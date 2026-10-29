"""Tests for the ClassForge project platform.

Covers path safety, canonical archives, immutable snapshots, artifact
inspection, the staged assessment pipeline (deterministic and AI paths),
rubric publication, grade application, the JSON API, and the web review UI.

Git integration is disabled and all file storage is redirected to a temporary
directory so the suite never touches the developer's media folder.
"""

import io
import json
import sqlite3
import tempfile
import zipfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import ActivityLog
from apps.courses.models import (
    Assignment,
    Course,
    CourseAssistant,
    Enrollment,
    Grade,
    Rubric,
    RubricCriterion,
    Submission,
)
from apps.projects import assessment as assessment_module
from apps.projects import parsers, services
from apps.projects.models import (
    ApiToken,
    Assessment,
    Notification,
    Project,
    ProjectSnapshot,
    PullRequest,
    RevisionRequest,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def file_pairs(files):
    """Return ``(handles, paths)`` suitable for ``services.build_archive``."""
    handles = [
        io.BytesIO(content.encode('utf-8') if isinstance(content, str) else content)
        for content in files.values()
    ]
    return handles, list(files)


PROJECT_FILES = {
    'README.md': '# Capstone\n\nA small library system.',
    'src/app.py': 'def main():\n    return "hello"\n',
    'schema.sql': (
        'CREATE TABLE authors (\n'
        '  id INTEGER PRIMARY KEY,\n'
        '  name TEXT NOT NULL\n'
        ');\n'
        'CREATE TABLE books (\n'
        '  id INTEGER PRIMARY KEY,\n'
        '  author_id INTEGER,\n'
        '  title TEXT,\n'
        '  FOREIGN KEY (author_id) REFERENCES authors(id)\n'
        ');\n'
    ),
    'tests/test_app.py': 'def test_main():\n    assert True\n',
    'docs/erd.md': '```mermaid\nerDiagram\n  AUTHORS ||--o{ BOOKS : writes\n```\n',
}


class WorkspaceTestCase(TestCase):
    """Shared fixture with temporary storage and Git disabled."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._tmp = tempfile.TemporaryDirectory(prefix='classforge-tests-')
        cls._settings = override_settings(
            MEDIA_ROOT=Path(cls._tmp.name) / 'media',
            CLASSFORGE_SNAPSHOT_ROOT=Path(cls._tmp.name) / 'snapshots',
            CLASSFORGE_GIT_ENABLED=False,
            ASSESSMENT_DISPATCH_MODE='inline',
            CLASSFORGE_TEST_RUNNER='disabled',
            AI_API_KEY='',
            ALLOWED_HOSTS=['testserver', 'localhost'],
        )
        cls._settings.enable()

    @classmethod
    def tearDownClass(cls):
        cls._settings.disable()
        cls._tmp.cleanup()
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.instructor = User.objects.create_user(
            username='instructor', password='secret1234', is_staff=True
        )
        self.student = User.objects.create_user(
            username='student', password='secret1234'
        )
        self.other_student = User.objects.create_user(
            username='other', password='secret1234'
        )
        self.course = Course.objects.create(
            name='Capstone', code='CAP101', instructor=self.instructor
        )
        Enrollment.objects.create(course=self.course, student=self.student)
        Enrollment.objects.create(course=self.course, student=self.other_student)
        self.assignment = Assignment.objects.create(
            course=self.course,
            title='Capstone Project',
            description='Build a library system.',
            due_date=timezone.now() + timezone.timedelta(days=14),
            max_score=Decimal('100.00'),
            status=Assignment.STATUS_PUBLISHED,
            guidelines='Document the schema and include tests.',
            required_files='README.md',
            required_directories='src',
            accepted_formats='.py\n.sql',
            documentation_requirements='A README describing the project.',
            validation_rules=(
                'require_sql\nrequire_primary_keys\nrequire_foreign_keys\n'
                'require_readme\nrequire_erd\nrequire_tests'
            ),
            required_tests='pytest -q',
            ai_grading_mode=Assignment.AI_MODE_INSTRUCTOR_APPROVED,
            manual_review_required=True,
        )
        self.rubric = Rubric.objects.create(
            assignment=self.assignment, title='Capstone rubric'
        )
        self.criterion_code = RubricCriterion.objects.create(
            rubric=self.rubric,
            name='Implementation',
            description='Working code and database schema.',
            max_points=Decimal('60.00'),
            expected_evidence='src/ and schema.sql',
            position=0,
        )
        self.criterion_docs = RubricCriterion.objects.create(
            rubric=self.rubric,
            name='Documentation',
            description='README and ERD.',
            max_points=Decimal('40.00'),
            expected_evidence='README.md and an ERD',
            position=1,
        )
        self.project = services.create_project(self.assignment, self.student)

    # -- helpers ---------------------------------------------------------
    def make_snapshot(self, files=None, project=None, **kwargs):
        handles, paths = file_pairs(files or PROJECT_FILES)
        return services.create_snapshot(
            project or self.project,
            files=handles,
            paths=paths,
            source=kwargs.pop('source', ProjectSnapshot.SOURCE_API),
            created_by=kwargs.pop('created_by', self.student),
            commit_to_git=False,
            **kwargs,
        )

    def make_token(self, user=None, scopes='read write'):
        return ApiToken.issue(user or self.student, scopes=scopes)[1]

    def api(self, method, url, *, token=None, data=None, **extra):
        kwargs = {'HTTP_AUTHORIZATION': f'Bearer {token or self.make_token()}'}
        kwargs.update(extra)
        if method == 'get':
            return self.client.get(url, **kwargs)
        if data is not None and not isinstance(data, dict) or (
            data is not None and not any(hasattr(v, 'read') for v in _iter_values(data))
        ):
            return self.client.post(
                url, data=json.dumps(data or {}), content_type='application/json', **kwargs
            )
        return self.client.post(url, data=data or {}, **kwargs)


def _iter_values(data):
    for value in data.values():
        if isinstance(value, list):
            yield from value
        else:
            yield value


# ---------------------------------------------------------------------------
# Path and archive safety
# ---------------------------------------------------------------------------

class PathSafetyTests(SimpleTestCase):
    def test_normalise_path_accepts_relative_paths(self):
        self.assertEqual(services.normalise_path('src\\app.py'), 'src/app.py')
        self.assertEqual(services.normalise_path('/src/app.py'), 'src/app.py')
        self.assertEqual(services.normalise_path('a/./b.txt'), 'a/b.txt')

    def test_normalise_path_rejects_unsafe_paths(self):
        for raw in ('../secret.txt', 'src/../../secret.txt', 'C:\\Windows\\x', '', '\x00bad'):
            with self.subTest(raw=raw), self.assertRaises(ValidationError):
                services.normalise_path(raw)

    def test_server_exclusions_cannot_be_negated(self):
        self.assertTrue(services.should_exclude('.env', []))
        self.assertTrue(services.should_exclude('.env', ['!.env']))
        self.assertTrue(services.should_exclude('node_modules/pkg/index.js', []))
        self.assertTrue(services.should_exclude('config/server.pem', []))
        self.assertFalse(services.should_exclude('src/app.py', []))

    def test_build_archive_excludes_ignored_and_secret_files(self):
        files = {
            'src/app.py': 'print("ok")',
            '.env': 'SECRET=1',
            'node_modules/pkg/index.js': 'x',
            'debug.log': 'noise',
            'README.md': '# Hi',
        }
        handles, paths = file_pairs(files)
        archive_bytes, included, excluded = services.build_archive(
            None, handles, paths
        )
        names = {item['path'] for item in included}
        self.assertEqual(names, {'src/app.py', 'README.md'})
        reasons = {item['path'] for item in excluded}
        self.assertIn('.env', reasons)
        self.assertIn('node_modules/pkg/index.js', reasons)
        self.assertIn('debug.log', reasons)

        handles, paths = file_pairs(files)
        again, _, _ = services.build_archive(None, handles, paths)
        self.assertEqual(archive_bytes, again, 'Archives must be deterministic.')

        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            self.assertEqual(archive.namelist(), ['README.md', 'src/app.py'])

    def test_build_archive_rejects_empty_result(self):
        handles, paths = file_pairs({'.env': 'SECRET=1'})
        with self.assertRaises(ValidationError):
            services.build_archive(None, handles, paths)

    def test_inspect_archive_reports_traversal_entries(self):
        archive_bytes = make_zip({'../evil.py': 'print(1)', 'ok.py': 'print(2)'})
        manifest, summary, issues = services.inspect_archive(archive_bytes)
        self.assertEqual([item['path'] for item in manifest], ['ok.py'])
        self.assertEqual(summary['file_count'], 1)
        self.assertTrue(any(issue['severity'] == 'critical' for issue in issues))

    def test_inspect_archive_rejects_non_zip(self):
        with self.assertRaises(ValidationError):
            services.inspect_archive(b'not a zip file')


# ---------------------------------------------------------------------------
# Snapshots, submissions, diffs and rubric publication
# ---------------------------------------------------------------------------

class SnapshotTests(WorkspaceTestCase):
    def test_create_snapshot_is_versioned_and_immutable(self):
        first = self.make_snapshot()
        second = self.make_snapshot({'README.md': '# v2', 'src/app.py': 'print(2)'})

        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 2)
        self.assertEqual(first.file_count, len(first.manifest))
        self.assertEqual(len(first.checksum), 64)
        self.assertTrue(first.archive.name.endswith('.zip'))
        self.assertEqual(self.project.latest_snapshot.pk, second.pk)

        first.note = 'tampered'
        with self.assertRaises(ValidationError):
            first.save()
        first.refresh_from_db()
        self.assertNotEqual(first.note, 'tampered')

    def test_project_creation_is_idempotent(self):
        again = services.create_project(self.assignment, self.student)
        self.assertEqual(again.pk, self.project.pk)
        self.assertEqual(Project.objects.count(), 1)

    def test_create_submission_for_snapshot_links_and_versions(self):
        snapshot = self.make_snapshot()
        submission = services.create_submission_for_snapshot(
            snapshot, self.student, note='first upload'
        )
        self.assertEqual(submission.version, 1)
        self.assertTrue(submission.file_attachment.name.endswith('.zip'))
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.submission_id, submission.pk)

        # Calling again returns the linked submission instead of creating one.
        same = services.create_submission_for_snapshot(snapshot, self.student)
        self.assertEqual(same.pk, submission.pk)
        self.assertEqual(Submission.objects.count(), 1)

    def test_diff_snapshots_reports_changes_and_text(self):
        base = self.make_snapshot()
        target = self.make_snapshot(
            {
                'README.md': '# Capstone changed',
                'src/app.py': 'def main():\n    return "hello"\n',
                'schema.sql': PROJECT_FILES['schema.sql'],
                'tests/test_app.py': PROJECT_FILES['tests/test_app.py'],
                'docs/erd.md': PROJECT_FILES['docs/erd.md'],
                'src/new.py': 'print("new")',
            }
        )
        diff = services.diff_snapshots(base, target)
        self.assertEqual(diff['summary']['added'], 1)
        self.assertEqual(diff['summary']['modified'], 1)
        self.assertEqual(diff['summary']['removed'], 0)
        self.assertEqual([item['path'] for item in diff['added']], ['src/new.py'])
        self.assertEqual([item['path'] for item in diff['modified']], ['README.md'])
        self.assertTrue(diff['text_diffs'])
        self.assertIn('Capstone changed', diff['text_diffs'][0]['diff'])

    def test_publish_rubric_creates_immutable_versions(self):
        version = services.publish_rubric(self.rubric, self.instructor, notes='v1')
        self.assertEqual(version.version, 1)
        self.assertEqual(version.total_points, Decimal('100.00'))
        self.assertEqual(len(version.criteria_snapshot), 2)
        self.assertEqual(version.published_by_id, self.instructor.pk)

        version2 = services.publish_rubric(self.rubric, self.instructor)
        self.assertEqual(version2.version, 2)

        empty_rubric = Rubric.objects.create(
            assignment=Assignment.objects.create(
                course=self.course,
                title='No criteria',
                due_date=timezone.now() + timezone.timedelta(days=1),
            )
        )
        with self.assertRaises(ValidationError):
            services.publish_rubric(empty_rubric)


# ---------------------------------------------------------------------------
# Artifact inspection
# ---------------------------------------------------------------------------

class ParserTests(SimpleTestCase):
    def test_parse_sql_detects_keys(self):
        parsed = parsers.parse_sql(PROJECT_FILES['schema.sql'])
        self.assertEqual(parsed['table_count'], 2)
        self.assertTrue(parsed['has_primary_key'])
        self.assertTrue(parsed['has_foreign_key'])
        self.assertFalse(parsed['syntax_issues'])

    def test_inspect_sqlite_is_read_only_and_extracts_schema(self):
        database = sqlite3.connect(':memory:')
        database.executescript(
            'CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT);'
            'CREATE TABLE books (id INTEGER PRIMARY KEY, author_id INTEGER '
            'REFERENCES authors(id), title TEXT);'
        )
        database.commit()
        data = database.serialize()
        database.close()

        info = parsers.inspect_sqlite_bytes(data, 'db.sqlite')
        self.assertEqual(info['table_count'], 2)
        self.assertTrue(info['has_primary_key'])
        self.assertTrue(info['has_foreign_key'])
        self.assertEqual(info['error'], '')

        invalid = parsers.inspect_sqlite_bytes(b'not a database')
        self.assertIn('error', invalid)

    def test_extract_artifacts_finds_docs_sql_tests_erd_and_secrets(self):
        files = dict(PROJECT_FILES)
        files['src/secret.py'] = 'API_KEY = "super-secret-value"\n'
        files['src/risky.py'] = 'import os\nos.system("echo hi")\n'
        archive_bytes = make_zip(files)
        manifest, _, _ = services.inspect_archive(archive_bytes)
        artifacts = parsers.extract_artifacts(archive_bytes, manifest, None)

        self.assertEqual(artifacts['readme']['path'], 'README.md')
        self.assertEqual(artifacts['sql']['table_count'], 2)
        self.assertTrue(artifacts['erd']['has_erd'])
        self.assertEqual(artifacts['tests'], ['tests/test_app.py'])
        self.assertTrue(any(item['kind'] == 'generic_secret' for item in artifacts['secrets']))
        self.assertTrue(any(item['kind'] == 'shell_execution' for item in artifacts['suspicious']))
        overview = parsers.artifact_overview(artifacts)
        self.assertTrue(overview['has_readme'])
        self.assertTrue(overview['has_erd'])
        self.assertEqual(overview['tests'], 1)


# ---------------------------------------------------------------------------
# Assessment pipeline
# ---------------------------------------------------------------------------

class AssessmentPipelineTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.rubric_version = services.publish_rubric(self.rubric, self.instructor)
        self.snapshot = self.make_snapshot()

    def test_deterministic_assessment_completes_and_requires_review(self):
        assessment = assessment_module.request_assessment(self.snapshot, self.instructor)

        self.assertEqual(assessment.status, Assessment.STATUS_COMPLETED)
        self.assertEqual(assessment.engine, Assessment.ENGINE_LOCAL)
        self.assertEqual(assessment.model_name, assessment_module.LOCAL_MODEL)
        self.assertIsNotNone(assessment.overall_score)
        self.assertLessEqual(assessment.overall_score, assessment.max_score)
        self.assertTrue(assessment.requires_review)
        self.assertEqual(assessment.review_status, Assessment.REVIEW_PENDING)
        self.assertEqual(assessment.rubric_version_id, self.rubric_version.pk)
        self.assertEqual(assessment.criteria.count(), 2)
        for criterion in assessment.criteria.all():
            self.assertTrue(criterion.comment)
            self.assertGreaterEqual(criterion.ai_points, 0)
            self.assertLessEqual(criterion.ai_points, criterion.max_points)

        checks = {item['key']: item for item in assessment.checks}
        self.assertEqual(checks['required_file:README.md']['status'], 'pass')
        self.assertEqual(checks['required_directory:src']['status'], 'pass')
        self.assertEqual(checks['require_sql']['status'], 'pass')
        self.assertEqual(checks['require_primary_keys']['status'], 'pass')
        self.assertEqual(checks['require_foreign_keys']['status'], 'pass')
        self.assertEqual(checks['require_tests']['status'], 'pass')
        self.assertEqual(checks['required_tests']['status'], 'skipped')

        self.assertTrue(
            Notification.objects.filter(
                user=self.student, kind=Notification.KIND_ASSESSMENT
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.instructor, kind=Notification.KIND_ASSESSMENT
            ).exists()
        )
        self.assertTrue(
            ActivityLog.objects.filter(action='assessment.completed').exists()
        )

    def test_running_assessment_twice_returns_the_completed_record(self):
        first = assessment_module.request_assessment(self.snapshot, self.instructor)
        second = assessment_module.request_assessment(self.snapshot, self.instructor)
        # The first call completed inline, so a new assessment may be created;
        # an in-flight request must be reused instead.
        self.assertEqual(second.status, Assessment.STATUS_COMPLETED)
        self.assertNotEqual(first.pk, second.pk)

        queued = Assessment.objects.create(
            snapshot=self.snapshot, status=Assessment.STATUS_QUEUED
        )
        reused = assessment_module.request_assessment(self.snapshot, self.instructor)
        self.assertEqual(reused.pk, queued.pk)
        # Clean up the in-flight record so later assertions stay isolated.
        queued.delete()

    def test_missing_requirements_fail_checks(self):
        bare = self.make_snapshot({'src/app.py': 'print(1)'})
        assessment = assessment_module.request_assessment(bare, self.instructor)
        checks = {item['key']: item for item in assessment.checks}
        self.assertEqual(checks['required_file:README.md']['status'], 'fail')
        self.assertEqual(checks['require_readme']['status'], 'fail')
        self.assertEqual(checks['require_sql']['status'], 'fail')
        self.assertLess(assessment.overall_score, Decimal('100.00'))

    def test_secret_check_flags_snapshot(self):
        snapshot = self.make_snapshot(
            {'README.md': '# x', 'src/app.py': 'password = "hunter2-secret"\n'}
        )
        assessment = assessment_module.request_assessment(snapshot, self.instructor)
        checks = {item['key']: item for item in assessment.checks}
        self.assertEqual(checks['secrets']['status'], 'fail')

    def test_failed_assessment_can_be_retried(self):
        assessment = Assessment.objects.create(
            snapshot=self.snapshot, status=Assessment.STATUS_FAILED, error='boom'
        )
        assessment_module.retry_assessment(assessment, self.instructor)
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, Assessment.STATUS_COMPLETED)
        self.assertEqual(assessment.error, '')
        self.assertEqual(assessment.attempts, 1)

        with self.assertRaises(ValidationError):
            assessment_module.retry_assessment(assessment, self.instructor)

    @override_settings(AI_API_KEY='test-key', AI_MODEL='fake-model')
    def test_ai_payload_is_used_when_valid(self):
        valid = {
            'summary': 'Solid implementation.',
            'feedback': 'Good work; add more tests.',
            'score': 75,
            'criteria': [
                {
                    'criterion_id': self.criterion_code.pk,
                    'points': 45,
                    'comment': 'The schema is complete.',
                    'evidence': 'schema.sql',
                    'confidence': 0.8,
                },
                {
                    'criterion_id': self.criterion_docs.pk,
                    'points': 30,
                    'comment': 'README is present.',
                    'evidence': 'README.md',
                    'confidence': 0.7,
                },
            ],
            'flags': [
                {'severity': 'warning', 'message': 'Tests are minimal.', 'evidence': 'tests/'}
            ],
        }
        with patch(
            'apps.projects.assessment.call_ai',
            return_value=('{}', valid),
        ):
            assessment = assessment_module.request_assessment(
                self.snapshot, self.instructor
            )

        self.assertEqual(assessment.engine, Assessment.ENGINE_AI)
        self.assertIn('fake-model', assessment.model_name)
        self.assertEqual(assessment.overall_score, Decimal('75'))
        self.assertEqual(assessment.summary, 'Solid implementation.')
        self.assertTrue(any(item['type'] == 'ai_flag' for item in assessment.evidence))

    @override_settings(AI_API_KEY='test-key')
    def test_invalid_ai_payload_falls_back_to_deterministic_draft(self):
        invalid = {'summary': '', 'feedback': '', 'score': 10, 'criteria': []}
        with patch(
            'apps.projects.assessment.call_ai',
            return_value=('{}', invalid),
        ):
            assessment = assessment_module.request_assessment(
                self.snapshot, self.instructor
            )

        self.assertEqual(assessment.engine, Assessment.ENGINE_LOCAL)
        self.assertIn('AI output rejected', assessment.model_name)
        self.assertIsNotNone(assessment.overall_score)

    def test_ai_exception_falls_back_to_deterministic_draft(self):
        with override_settings(AI_API_KEY='test-key'), patch(
            'apps.projects.assessment.call_ai',
            side_effect=RuntimeError('provider unavailable'),
        ):
            assessment = assessment_module.request_assessment(
                self.snapshot, self.instructor
            )
        self.assertEqual(assessment.engine, Assessment.ENGINE_LOCAL)
        self.assertIn('AI error', assessment.model_name)

    def test_automatic_mode_applies_unpublished_grade(self):
        self.assignment.ai_grading_mode = Assignment.AI_MODE_AUTOMATIC
        self.assignment.manual_review_required = False
        self.assignment.save(update_fields=['ai_grading_mode', 'manual_review_required'])

        assessment = assessment_module.request_assessment(self.snapshot, self.instructor)
        self.assertFalse(assessment.requires_review)
        assessment.refresh_from_db()
        self.assertIsNotNone(assessment.applied_grade_id)
        grade = assessment.applied_grade
        self.assertFalse(grade.is_published, 'Automated grades must remain unpublished.')

    def test_review_and_apply_create_unpublished_grade(self):
        assessment = assessment_module.request_assessment(self.snapshot, self.instructor)
        scores = {
            str(item.pk): str(item.max_points) for item in assessment.criteria.all()
        }
        services.review_assessment(
            assessment,
            self.instructor,
            'override',
            instructor_feedback='Well done.',
            criterion_scores=scores,
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.review_status, Assessment.REVIEW_OVERRIDDEN)
        self.assertEqual(assessment.reviewer_id, self.instructor.pk)

        grade, created = services.apply_assessment(assessment, self.instructor)
        self.assertTrue(created)
        self.assertEqual(grade.score, Decimal('100.00'))
        self.assertFalse(grade.is_published)
        self.assertIsNone(grade.published_at)
        self.assertEqual(grade.feedback, 'Well done.')
        self.assertEqual(grade.criterion_scores.count(), 2)
        self.assertEqual(assessment.applied_grade_id, grade.pk)

    def test_apply_requires_completed_assessment(self):
        assessment = Assessment.objects.create(
            snapshot=self.snapshot, status=Assessment.STATUS_QUEUED
        )
        with self.assertRaises(ValidationError):
            services.apply_assessment(assessment, self.instructor)


class AiValidationTests(SimpleTestCase):
    def setUp(self):
        self.criteria = [
            {
                'criterion_id': 1,
                'name': 'Code',
                'max_points': Decimal('10'),
            },
            {
                'criterion_id': 2,
                'name': 'Docs',
                'max_points': Decimal('5'),
            },
        ]

    def test_accepts_and_clamps_valid_payload(self):
        payload = assessment_module.validate_ai_payload(
            {
                'summary': 'Summary',
                'feedback': 'Feedback',
                'score': 1000,
                'criteria': [
                    {'criterion_id': 1, 'points': 99, 'comment': 'Great'},
                    {
                        'criterion_id': 2,
                        'points': -3,
                        'comment': 'Missing',
                        'confidence': 4,
                    },
                ],
                'flags': [
                    {'severity': 'bogus', 'message': 'ignored'},
                    {'severity': 'info', 'message': 'noted'},
                ],
            },
            self.criteria,
            Decimal('15'),
        )
        self.assertIsNotNone(payload)
        self.assertEqual(payload['criteria'][0]['points'], Decimal('10.00'))
        self.assertEqual(payload['criteria'][1]['points'], Decimal('0.00'))
        self.assertEqual(payload['criteria'][1]['confidence'], Decimal('1'))
        self.assertEqual(payload['score'], Decimal('10.00'))
        self.assertEqual(len(payload['evidence']), 1)

    def test_rejects_incomplete_or_unknown_criteria(self):
        base = {
            'summary': 'Summary',
            'feedback': 'Feedback',
            'score': 1,
            'criteria': [
                {'criterion_id': 1, 'points': 1, 'comment': 'ok'},
            ],
        }
        # Missing one criterion.
        self.assertIsNone(
            assessment_module.validate_ai_payload(base, self.criteria, Decimal('15'))
        )

        base['criteria'].append(
            {'criterion_id': 1, 'points': 2, 'comment': 'duplicate id'}
        )
        # Still only one unique criterion, so the count does not match.
        self.assertIsNone(
            assessment_module.validate_ai_payload(base, self.criteria, Decimal('15'))
        )

    def test_rejects_missing_comments_and_non_dicts(self):
        for payload in (
            None,
            [],
            {'summary': 'x', 'feedback': 'y', 'criteria': []},
            {
                'summary': 'x',
                'feedback': 'y',
                'criteria': [{'criterion_id': 1, 'points': 1, 'comment': ' '}],
            },
        ):
            with self.subTest(payload=payload):
                self.assertIsNone(
                    assessment_module.validate_ai_payload(
                        payload, self.criteria, Decimal('15')
                    )
                )


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

class ApiTokenTests(WorkspaceTestCase):
    def test_token_endpoint_authenticates_and_returns_raw_token_once(self):
        response = self.client.post(
            reverse('projects_api:token_create'),
            data=json.dumps(
                {'username': 'student', 'password': 'secret1234', 'name': 'VS Code'}
            ),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['token'].startswith('cf_'))
        token = ApiToken.objects.get(user=self.student)
        self.assertNotEqual(token.token_hash, data['token'])
        self.assertEqual(token.token_hash, ApiToken.hash_token(data['token']))

        me = self.client.get(
            reverse('projects_api:me'),
            HTTP_AUTHORIZATION=f'Bearer {data["token"]}',
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['user']['username'], 'student')

    def test_invalid_credentials_create_no_token(self):
        response = self.client.post(
            reverse('projects_api:token_create'),
            data=json.dumps({'username': 'student', 'password': 'wrong'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(ApiToken.objects.exists())

    def test_requests_require_a_token(self):
        response = self.client.get(reverse('projects_api:me'))
        self.assertEqual(response.status_code, 401)

    def test_revoked_and_expired_tokens_are_rejected(self):
        raw = self.make_token()
        token = ApiToken.objects.get(user=self.student)
        token.revoked_at = timezone.now()
        token.save(update_fields=['revoked_at'])
        response = self.client.get(
            reverse('projects_api:me'), HTTP_AUTHORIZATION=f'Bearer {raw}'
        )
        self.assertEqual(response.status_code, 401)

        raw = self.make_token()
        ApiToken.objects.filter(user=self.student).update(
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )
        response = self.client.get(
            reverse('projects_api:me'), HTTP_AUTHORIZATION=f'Bearer {raw}'
        )
        self.assertEqual(response.status_code, 401)

    def test_token_scopes_are_enforced(self):
        raw = self.make_token(scopes='read')
        response = self.client.post(
            reverse('projects_api:snapshot_assess', args=[999]),
            HTTP_AUTHORIZATION=f'Bearer {raw}',
        )
        self.assertEqual(response.status_code, 403)

    def test_revoke_via_web_session(self):
        raw = self.make_token()
        token = ApiToken.objects.get(user=self.student)
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('projects_api:token_revoke', args=[token.pk])
        )
        self.assertEqual(response.status_code, 200)
        token.refresh_from_db()
        self.assertIsNotNone(token.revoked_at)
        response = self.client.get(
            reverse('projects_api:me'), HTTP_AUTHORIZATION=f'Bearer {raw}'
        )
        self.assertEqual(response.status_code, 401)

    @override_settings(CLASSFORGE_API_RATE_LIMIT=1, CLASSFORGE_API_RATE_WINDOW=60)
    def test_rate_limit_returns_429(self):
        raw = self.make_token()
        url = reverse('projects_api:me')
        self.assertEqual(
            self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {raw}').status_code,
            200,
        )
        self.assertEqual(
            self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {raw}').status_code,
            429,
        )

    def test_health_endpoint_is_public(self):
        response = self.client.get(reverse('projects_api:health'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['test_runner'], 'disabled')
        self.assertFalse(data['ai_configured'])


class ApiUploadTests(WorkspaceTestCase):
    def test_student_uploads_multipart_files(self):
        files = [
            SimpleUploadedFile('README.md', PROJECT_FILES['README.md'].encode()),
            SimpleUploadedFile('app.py', PROJECT_FILES['src/app.py'].encode()),
            SimpleUploadedFile('.env', b'SECRET=1'),
        ]
        response = self.api(
            'post',
            reverse('projects_api:assignment_submit', args=[self.assignment.pk]),
            data={
                'files[]': files,
                'paths': json.dumps(['README.md', 'src/app.py', '.env']),
                'note': 'first upload',
                'source': 'vscode',
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data['snapshot']['source'], ProjectSnapshot.SOURCE_VSCODE)
        self.assertEqual(data['snapshot']['file_count'], 2)
        self.assertEqual(
            {item['path'] for item in data['snapshot']['manifest']},
            {'README.md', 'src/app.py'},
        )
        self.assertEqual(data['submission']['version'], 1)

        project = Project.objects.get(pk=data['project']['id'])
        self.assertEqual(project.student_id, self.student.pk)
        snapshot = ProjectSnapshot.objects.get(pk=data['snapshot']['id'])
        self.assertEqual(snapshot.submission_id, data['submission']['id'])
        self.assertTrue(
            Notification.objects.filter(user=self.instructor).exists()
        )

    def test_archive_upload_is_accepted(self):
        archive = SimpleUploadedFile(
            'project.zip', make_zip(PROJECT_FILES), content_type='application/zip'
        )
        response = self.api(
            'post',
            reverse('projects_api:assignment_submit', args=[self.assignment.pk]),
            data={'archive': archive},
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['snapshot']['file_count'], len(PROJECT_FILES))

    def test_path_traversal_upload_is_rejected(self):
        files = [SimpleUploadedFile('evil.py', b'print(1)')]
        response = self.api(
            'post',
            reverse('projects_api:assignment_submit', args=[self.assignment.pk]),
            data={'files[]': files, 'paths': json.dumps(['../evil.py'])},
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(ProjectSnapshot.objects.exists())

    def test_upload_ignores_classforgeignore_patterns(self):
        ignore = SimpleUploadedFile('.classforgeignore', b'docs/**\n')
        files = [
            SimpleUploadedFile('README.md', b'# hi'),
            SimpleUploadedFile('erd.md', b'```mermaid\nerDiagram\n```'),
        ]
        response = self.api(
            'post',
            reverse('projects_api:assignment_submit', args=[self.assignment.pk]),
            data={
                'files[]': files,
                'paths': json.dumps(['README.md', 'docs/erd.md']),
                'classforgeignore': ignore,
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            {item['path'] for item in response.json()['snapshot']['manifest']},
            {'README.md'},
        )

    def test_unpublished_assignment_rejects_students(self):
        self.assignment.status = Assignment.STATUS_DRAFT
        self.assignment.save(update_fields=['status'])
        response = self.api(
            'post',
            reverse('projects_api:assignment_submit', args=[self.assignment.pk]),
            data={
                'files[]': [SimpleUploadedFile('README.md', b'# hi')],
                'paths': json.dumps(['README.md']),
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_unenrolled_student_cannot_upload(self):
        outsider = User.objects.create_user(username='outsider', password='secret1234')
        token = self.make_token(outsider)
        response = self.api(
            'post',
            reverse('projects_api:assignment_submit', args=[self.assignment.pk]),
            data={
                'files[]': [SimpleUploadedFile('README.md', b'# hi')],
                'paths': json.dumps(['README.md']),
            },
            token=token,
        )
        self.assertEqual(response.status_code, 403)


class ApiProjectAndAssessmentTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        services.publish_rubric(self.rubric, self.instructor)
        self.snapshot = self.make_snapshot()
        self.student_token = self.make_token(self.student)
        self.instructor_token = self.make_token(self.instructor)

    def test_student_only_sees_own_projects(self):
        response = self.api(
            'get', reverse('projects_api:project_list'), token=self.student_token
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item['id'] for item in response.json()['projects']], [self.project.pk]
        )

        other = services.create_project(self.assignment, self.other_student)
        response = self.api(
            'get', reverse('projects_api:project_detail', args=[other.pk]),
            token=self.student_token,
        )
        self.assertEqual(response.status_code, 403)

        response = self.api(
            'get', reverse('projects_api:project_detail', args=[other.pk]),
            token=self.instructor_token,
        )
        self.assertEqual(response.status_code, 200)

    def test_snapshot_diff_and_status_endpoints(self):
        second = self.make_snapshot({'README.md': '# changed'})
        status = self.api(
            'get', reverse('projects_api:snapshot_status', args=[second.pk]),
            token=self.student_token,
        )
        self.assertEqual(status.status_code, 200)
        self.assertIsNone(status.json()['assessment'])

        diff = self.api(
            'get', reverse('projects_api:snapshot_diff', args=[second.pk]),
            token=self.student_token,
        )
        self.assertEqual(diff.status_code, 200)
        self.assertEqual(diff.json()['base']['id'], self.snapshot.pk)
        self.assertEqual(diff.json()['diff']['summary']['modified'], 1)

    def test_assess_and_feedback_endpoints(self):
        response = self.api(
            'post', reverse('projects_api:snapshot_assess', args=[self.snapshot.pk]),
            token=self.student_token, data={},
        )
        self.assertEqual(response.status_code, 202, response.content)
        assessment = response.json()['assessment']
        self.assertEqual(assessment['status'], Assessment.STATUS_COMPLETED)
        self.assertTrue(assessment['requires_review'])

        feedback = self.api(
            'get', reverse('projects_api:snapshot_feedback', args=[self.snapshot.pk]),
            token=self.student_token,
        )
        self.assertEqual(feedback.status_code, 200)
        self.assertEqual(feedback.json()['assessment']['id'], assessment['id'])
        self.assertFalse(feedback.json()['assessment']['requires_review'] is False)

    def test_assignments_endpoint_hides_unpublished_from_students(self):
        Assignment.objects.create(
            course=self.course,
            title='Draft work',
            due_date=timezone.now() + timezone.timedelta(days=3),
            status=Assignment.STATUS_DRAFT,
        )
        response = self.api(
            'get', reverse('projects_api:assignments'), token=self.student_token
        )
        self.assertEqual(response.status_code, 200)
        titles = [item['title'] for item in response.json()['assignments']]
        self.assertEqual(titles, ['Capstone Project'])

    def test_revision_and_pull_request_lifecycle(self):
        # Instructor requests a revision.
        response = self.api(
            'post',
            reverse('projects_api:revision_create', args=[self.project.pk]),
            token=self.instructor_token,
            data={
                'title': 'Add tests',
                'description': 'Please add integration tests.',
                'snapshot_id': self.snapshot.pk,
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        revision_id = response.json()['revision_request']['id']
        self.assertTrue(
            Notification.objects.filter(
                user=self.student, kind=Notification.KIND_REVISION
            ).exists()
        )

        # A student may not request a revision.
        response = self.api(
            'post',
            reverse('projects_api:revision_create', args=[self.project.pk]),
            token=self.student_token,
            data={'title': 'Nope'},
        )
        self.assertEqual(response.status_code, 403)

        # Student opens a pull request against the revision.
        response = self.api(
            'post',
            reverse('projects_api:pull_request_create', args=[self.project.pk]),
            token=self.student_token,
            data={
                'title': 'Add tests',
                'description': 'Added the tests.',
                'source_snapshot_id': self.snapshot.pk,
                'revision_request_id': revision_id,
                'source_branch': 'revision/1',
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        pull_request_id = response.json()['pull_request']['id']

        # A student may not merge.
        response = self.api(
            'post',
            reverse('projects_api:pull_request_action', args=[pull_request_id]),
            token=self.student_token,
            data={'action': 'merge'},
        )
        self.assertEqual(response.status_code, 403)

        # Comments are allowed for the owner and graders.
        response = self.api(
            'post',
            reverse('projects_api:pull_request_action', args=[pull_request_id]),
            token=self.student_token,
            data={'action': 'comment', 'body': 'Ready for review.'},
        )
        self.assertEqual(response.status_code, 200)

        response = self.api(
            'post',
            reverse('projects_api:pull_request_action', args=[pull_request_id]),
            token=self.instructor_token,
            data={'action': 'merge'},
        )
        self.assertEqual(response.status_code, 200, response.content)
        pull_request = PullRequest.objects.get(pk=pull_request_id)
        self.assertEqual(pull_request.status, PullRequest.STATUS_MERGED)
        self.assertEqual(pull_request.reviewed_by_id, self.instructor.pk)
        revision = RevisionRequest.objects.get(pk=revision_id)
        self.assertEqual(revision.status, RevisionRequest.STATUS_ADDRESSED)
        self.assertTrue(
            Notification.objects.filter(
                user=self.student, kind=Notification.KIND_PULL_REQUEST
            ).exists()
        )

    def test_pull_request_requires_a_snapshot(self):
        empty = services.create_project(self.assignment, self.other_student)
        empty.snapshots.all().delete()
        response = self.api(
            'post',
            reverse('projects_api:pull_request_create', args=[empty.pk]),
            token=self.make_token(self.other_student),
            data={'title': 'Nothing yet'},
        )
        self.assertEqual(response.status_code, 400)

    def test_notification_list_and_mark_read(self):
        services.notify(
            self.student, title='Hello', kind=Notification.KIND_INFO
        )
        response = self.api(
            'get', reverse('projects_api:notification_list'),
            token=self.student_token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()['unread'], 1)
        notification = response.json()['notifications'][0]

        response = self.api(
            'post',
            reverse('projects_api:notification_read', args=[notification['id']]),
            token=self.student_token,
            data={},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(
            Notification.objects.get(pk=notification['id']).read_at
        )


# ---------------------------------------------------------------------------
# Web UI
# ---------------------------------------------------------------------------

class ProjectWebTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.snapshot = self.make_snapshot()

    def test_project_list_requires_login(self):
        response = self.client.get(reverse('projects:project_list'))
        self.assertEqual(response.status_code, 302)

    def test_students_see_only_their_projects(self):
        services.create_project(self.assignment, self.other_student)
        self.client.force_login(self.student)
        response = self.client.get(reverse('projects:project_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [project.pk for project in response.context['projects']], [self.project.pk]
        )

        self.client.force_login(self.instructor)
        response = self.client.get(reverse('projects:project_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['projects'].paginator.count, 2)

    def test_snapshot_pages_enforce_ownership(self):
        self.client.force_login(self.student)
        response = self.client.get(
            reverse('projects:snapshot_detail', args=[self.snapshot.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'README.md')

        self.client.force_login(self.other_student)
        response = self.client.get(
            reverse('projects:snapshot_detail', args=[self.snapshot.pk])
        )
        self.assertEqual(response.status_code, 403)

        compare = self.client.get(
            reverse('projects:snapshot_compare', args=[self.snapshot.pk])
        )
        self.assertEqual(compare.status_code, 403)

    def test_assessment_review_is_restricted_to_graders(self):
        services.publish_rubric(self.rubric, self.instructor)
        assessment = assessment_module.request_assessment(self.snapshot, self.instructor)
        url = reverse('projects:assessment_review', args=[assessment.pk])

        self.client.force_login(self.student)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.instructor)
        self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.post(
            url,
            {
                'action': 'approve',
                'instructor_score': '88',
                'instructor_feedback': 'Good work.',
                f'criterion_{assessment.criteria.first().pk}': '50',
            },
        )
        self.assertEqual(response.status_code, 302)
        assessment.refresh_from_db()
        self.assertEqual(assessment.review_status, Assessment.REVIEW_APPROVED)
        self.assertIsNotNone(assessment.applied_grade_id)
        self.assertFalse(assessment.applied_grade.is_published)

    def test_student_can_request_assessment_from_snapshot_page(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('projects:snapshot_assess', args=[self.snapshot.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Assessment.objects.filter(
                snapshot=self.snapshot, status=Assessment.STATUS_COMPLETED
            ).exists()
        )

    def test_student_can_open_snapshot_with_completed_assessment(self):
        services.publish_rubric(self.rubric, self.instructor)
        assessment = assessment_module.request_assessment(self.snapshot, self.instructor)
        self.assertEqual(assessment.status, Assessment.STATUS_COMPLETED)
        self.assertTrue(assessment.evidence)

        self.client.force_login(self.student)
        response = self.client.get(
            reverse('projects:snapshot_detail', args=[self.snapshot.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'schema.sql')

    def test_token_management_page_shows_token_once(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('projects:token_manage'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['raw_token'])

        response = self.client.post(
            reverse('projects:token_manage'), {'name': 'Laptop', 'action': 'create'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['raw_token'].startswith('cf_'))
        self.assertTrue(ApiToken.objects.filter(user=self.student, name='Laptop').exists())

    def test_notifications_can_be_marked_read(self):
        services.notify(self.student, title='You have news')
        self.client.force_login(self.student)
        response = self.client.post(reverse('projects:notification_list'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Notification.objects.filter(user=self.student, read_at__isnull=True).exists()
        )

    def test_pull_request_detail_renders_and_only_graders_merge(self):
        pull_request = PullRequest.objects.create(
            project=self.project,
            title='Add tests',
            description='Ready for review.',
            source_snapshot=self.snapshot,
            created_by=self.student,
            source_branch='feature',
            target_branch='main',
        )
        url = reverse('projects:pull_request_detail', args=[pull_request.pk])

        self.client.force_login(self.student)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add tests')
        response = self.client.post(url, {'action': 'merge'})
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.instructor)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {'action': 'merge'})
        self.assertEqual(response.status_code, 302)
        pull_request.refresh_from_db()
        self.assertEqual(pull_request.status, PullRequest.STATUS_MERGED)
        self.assertEqual(pull_request.reviewed_by_id, self.instructor.pk)

    def test_snapshot_compare_page_renders_diff(self):
        second = self.make_snapshot({'README.md': '# Updated', 'src/app.py': 'print(2)'})
        self.client.force_login(self.student)
        response = self.client.get(
            reverse('projects:snapshot_compare', args=[second.pk])
            + f'?base={self.snapshot.pk}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'README.md')

    def test_instructor_creates_revision_and_student_cannot(self):
        self.client.force_login(self.student)
        response = self.client.get(
            reverse('projects:revision_create', args=[self.project.pk])
        )
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.instructor)
        response = self.client.post(
            reverse('projects:revision_create', args=[self.project.pk]),
            {
                'title': 'Improve docs',
                'description': 'Add an ERD.',
                'snapshot': self.snapshot.pk,
                'branch_name': 'revision/1',
            },
        )
        self.assertEqual(response.status_code, 302)
        revision = RevisionRequest.objects.get(project=self.project)
        self.assertEqual(revision.branch_name, 'revision/1')
        self.assertTrue(
            Notification.objects.filter(
                user=self.student, kind=Notification.KIND_REVISION
            ).exists()
        )


class CourseIntegrationTests(WorkspaceTestCase):
    def test_web_submission_zip_is_mirrored_into_a_snapshot(self):
        """The existing submission flow still creates a project snapshot."""
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('courses:submission_create', args=[self.assignment.pk]),
            {
                'file_attachment': SimpleUploadedFile(
                    'project.zip', make_zip(PROJECT_FILES), content_type='application/zip'
                ),
                'text_content': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        submission = Submission.objects.get(
            assignment=self.assignment, student=self.student
        )
        snapshot = ProjectSnapshot.objects.get(submission=submission)
        self.assertEqual(snapshot.source, ProjectSnapshot.SOURCE_WEB)
        self.assertEqual(snapshot.project.student_id, self.student.pk)
        self.assertEqual(snapshot.file_count, len(PROJECT_FILES))
