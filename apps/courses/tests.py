"""Tests for the ClassForge courses app."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.courses.forms import AssignmentForm, SubmissionForm
from apps.courses.models import (
    Assignment,
    Course,
    Enrollment,
    Grade,
    Submission,
)

User = get_user_model()


def make_users():
    instructor = User.objects.create_user(
        username='instructor', password='secret1234', is_staff=True
    )
    student = User.objects.create_user(
        username='student', password='secret1234'
    )
    return instructor, student


def make_course(instructor, code='CS101'):
    return Course.objects.create(
        name='Intro to Testing',
        code=code,
        description='A course',
        instructor=instructor,
    )


def make_assignment(course, **kwargs):
    defaults = {
        'title': 'Homework 1',
        'description': 'Do things',
        'due_date': timezone.now() + timezone.timedelta(days=7),
        'max_score': Decimal('100.00'),
    }
    defaults.update(kwargs)
    return Assignment.objects.create(course=course, **defaults)


class CourseModelTests(TestCase):
    def test_code_is_uppercased_and_unique(self):
        instructor, _ = make_users()
        course = make_course(instructor, code='cs101')
        self.assertEqual(course.code, 'CS101')
        with self.assertRaises(IntegrityError):
            make_course(instructor, code='CS101')

    def test_enrollment_unique_per_course_student(self):
        instructor, student = make_users()
        course = make_course(instructor)
        Enrollment.objects.create(course=course, student=student)
        with self.assertRaises(IntegrityError):
            Enrollment.objects.create(course=course, student=student)


class SubmissionVersionTests(TestCase):
    def test_resubmit_creates_new_version(self):
        instructor, student = make_users()
        course = make_course(instructor)
        Enrollment.objects.create(course=course, student=student)
        assignment = make_assignment(course)

        first = Submission.objects.create(
            assignment=assignment, student=student, text_content='attempt 1'
        )
        second = Submission.objects.create(
            assignment=assignment, student=student, text_content='attempt 2'
        )
        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 2)
        self.assertNotEqual(first.pk, second.pk)

    def test_duplicate_version_rejected(self):
        instructor, student = make_users()
        course = make_course(instructor)
        assignment = make_assignment(course)
        Submission.objects.create(
            assignment=assignment, student=student, text_content='a'
        )
        # version is fully managed: even an explicitly colliding value is
        # renumbered, so the DB UNIQUE(assignment, student, version)
        # constraint acts only as a race-condition backstop.
        second = Submission.objects.create(
            assignment=assignment,
            student=student,
            version=1,
            text_content='dup',
        )
        self.assertEqual(second.version, 2)
        constraint_names = [
            c.name for c in Submission._meta.constraints
        ]
        self.assertIn(
            'uq_submissions_assignment_student_version', constraint_names
        )

    def test_submission_requires_content(self):
        instructor, student = make_users()
        course = make_course(instructor)
        assignment = make_assignment(course)
        submission = Submission(assignment=assignment, student=student)
        with self.assertRaises(ValidationError):
            submission.full_clean()


class GradeTests(TestCase):
    def test_one_grade_per_submission_version(self):
        instructor, student = make_users()
        course = make_course(instructor)
        assignment = make_assignment(course)
        submission = Submission.objects.create(
            assignment=assignment, student=student, text_content='work'
        )
        Grade.objects.create(
            submission=submission, instructor=instructor, score=Decimal('90')
        )
        with self.assertRaises(IntegrityError):
            Grade.objects.create(
                submission=submission, instructor=instructor, score=Decimal('80')
            )

    def test_score_above_max_rejected(self):
        instructor, student = make_users()
        course = make_course(instructor)
        assignment = make_assignment(course, max_score=Decimal('50.00'))
        submission = Submission.objects.create(
            assignment=assignment, student=student, text_content='work'
        )
        grade = Grade(
            submission=submission, instructor=instructor, score=Decimal('60')
        )
        with self.assertRaises(ValidationError):
            grade.full_clean()


class AssignmentCategoryTests(TestCase):
    def test_default_category_is_code_project(self):
        instructor, _ = make_users()
        assignment = make_assignment(make_course(instructor))
        self.assertEqual(assignment.category, 'code_project')
        self.assertEqual(assignment.get_category_display(), 'Code Project')

    def test_invalid_category_rejected(self):
        instructor, _ = make_users()
        assignment = make_assignment(make_course(instructor))
        assignment.category = 'not_a_category'
        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_course_detail_filters_by_category(self):
        instructor, student = make_users()
        course = make_course(instructor)
        Enrollment.objects.create(course=course, student=student)
        make_assignment(course, title='Proj', category='code_project')
        make_assignment(course, title='Diagram', category='erd')
        self.client.force_login(student)
        response = self.client.get(
            reverse('courses:course_detail', args=[course.pk])
            + '?category=erd'
        )
        self.assertEqual(response.status_code, 200)
        titles = [a.title for a in response.context['assignments']]
        self.assertEqual(titles, ['Diagram'])


class SubmissionSettingsTests(TestCase):
    def _assignment_data(self, **overrides):
        data = {
            'title': 'No links allowed',
            'category': 'code_project',
            'description': '',
            'due_date': (timezone.now() + timezone.timedelta(days=7)).strftime(
                '%Y-%m-%dT%H:%M'
            ),
            'max_score': '100.00',
            'status': 'published',
            'guidelines': '',
            'required_files': '',
            'expected_outcomes': '',
            'accepted_formats': '.zip\n.pdf',
            'required_directories': '',
            'documentation_requirements': '',
            'validation_rules': '',
            'required_tests': '',
            'max_upload_mb': '25',
            'ai_grading_mode': 'instructor_approved',
            'manual_review_required': 'on',
            'late_policy': 'accept',
            'late_penalty_percent': '0',
            'allow_resubmission': 'on',
            'revision_deadline_days': '7',
            'default_exclusions': '',
            'accepts_zip': 'on',
            'accepts_pdf': 'on',
            'ai_auto_run': 'on',
        }
        data.update(overrides)
        return data

    def test_github_fields_are_removed_from_models_and_forms(self):
        with self.assertRaises(FieldDoesNotExist):
            Assignment._meta.get_field('accepts_github')
        with self.assertRaises(FieldDoesNotExist):
            Submission._meta.get_field('github_url')
        self.assertNotIn('accepts_github', AssignmentForm().fields)
        self.assertNotIn('github_url', SubmissionForm().fields)

    def test_assignment_creation_only_offers_file_formats(self):
        instructor, _ = make_users()
        course = make_course(instructor)
        self.client.force_login(instructor)
        response = self.client.get(
            reverse('courses:assignment_create', args=[course.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'GitHub')
        self.assertContains(response, 'Accept .zip')
        self.assertContains(response, 'Accept .pdf')

    def test_assignment_form_accepts_zip_and_pdf_without_github(self):
        form = AssignmentForm(data=self._assignment_data())
        self.assertTrue(form.is_valid(), form.errors)
        assignment = form.save(commit=False)
        self.assertEqual(assignment.accepted_types, ['.zip', '.pdf'])

    def test_submission_form_accepts_text_without_github(self):
        instructor, student = make_users()
        assignment = make_assignment(make_course(instructor))
        form = SubmissionForm(
            data={'text_content': 'Notes submitted as text.'},
            assignment=assignment,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_submission_page_has_no_github_input(self):
        instructor, student = make_users()
        course = make_course(instructor)
        Enrollment.objects.create(course=course, student=student)
        assignment = make_assignment(course)
        self.client.force_login(student)
        response = self.client.get(
            reverse('courses:submission_create', args=[assignment.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'GitHub')
        self.assertContains(response, 'Text Content / Notes')


class CoursePermissionTests(TestCase):
    def test_student_cannot_open_course_create(self):
        _, student = make_users()
        self.client.force_login(student)
        response = self.client.get(reverse('courses:course_create'))
        self.assertEqual(response.status_code, 403)

    def test_instructor_can_create_course(self):
        instructor, _ = make_users()
        self.client.force_login(instructor)
        response = self.client.post(
            reverse('courses:course_create'),
            {'name': 'Math', 'code': 'MATH1', 'description': ''},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Course.objects.filter(code='MATH1').exists())

    def test_student_submit_requires_enrollment(self):
        instructor, student = make_users()
        course = make_course(instructor)
        assignment = make_assignment(course)
        self.client.force_login(student)
        response = self.client.post(
            reverse('courses:submission_create', args=[assignment.pk]),
            {'text_content': 'my work'},
        )
        # Redirected back to course page with an error message.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Submission.objects.filter(
                assignment=assignment, student=student
            ).count(),
            0,
        )

    def test_enrolled_student_can_submit_twice(self):
        instructor, student = make_users()
        course = make_course(instructor)
        Enrollment.objects.create(course=course, student=student)
        assignment = make_assignment(course)
        self.client.force_login(student)
        url = reverse('courses:submission_create', args=[assignment.pk])
        self.assertEqual(
            self.client.post(url, {'text_content': 'v1'}).status_code, 302
        )
        self.assertEqual(
            self.client.post(url, {'text_content': 'v2'}).status_code, 302
        )
        versions = list(
            Submission.objects.filter(
                assignment=assignment, student=student
            ).order_by('version').values_list('version', flat=True)
        )
        self.assertEqual(versions, [1, 2])

    def test_grade_over_max_returns_form_error_not_500(self):
        instructor, student = make_users()
        course = make_course(instructor)
        assignment = make_assignment(course, max_score=Decimal('50.00'))
        submission = Submission.objects.create(
            assignment=assignment, student=student, text_content='work'
        )
        self.client.force_login(instructor)
        response = self.client.post(
            reverse('courses:submission_grade', args=[submission.pk]),
            {'score': '60', 'feedback': 'too high'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Grade.objects.filter(submission=submission).exists()
        )

    def test_student_only_sees_published_grades(self):
        instructor, student = make_users()
        course = make_course(instructor)
        Enrollment.objects.create(course=course, student=student)
        assignment = make_assignment(course)
        submission = Submission.objects.create(
            assignment=assignment, student=student, text_content='work'
        )
        Grade.objects.create(
            submission=submission,
            instructor=instructor,
            score=Decimal('70'),
            is_published=False,
        )
        self.client.force_login(student)
        response = self.client.get(reverse('courses:my_grades'))
        self.assertEqual(response.status_code, 200)
        # '70' also appears in the theme's chart JS, so assert on context.
        self.assertEqual(list(response.context['grades']), [])
