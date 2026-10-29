"""Project workspace services: archives, snapshots, Git, diffs and grading.

Design rules enforced here:

* Uploaded paths are normalised and validated before they are written.
* Archives are rebuilt server-side from the uploaded file list, so a client
  cannot smuggle a different archive than the manifest describes.
* Archive entries are never extracted into the web root; only into a
  server-owned Git workspace (when Git integration is enabled).
* Submission snapshots are immutable at the model level.
* Applying an assessment creates an *unpublished* grade for instructor review.
"""

from __future__ import annotations

import difflib
import fnmatch
import hashlib
import io
import logging
import os
import posixpath
import re
import shutil
import subprocess
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.courses.models import (
    CriterionScore,
    Grade,
    RubricVersion,
    Submission,
)

from .models import (
    Assessment,
    CriterionAssessment,
    Notification,
    Project,
    ProjectSnapshot,
    PullRequest,
    Repository,
    RevisionRequest,
)

logger = logging.getLogger(__name__)

TEXT_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.php', '.rb', '.go',
    '.cs', '.c', '.cpp', '.h', '.hpp', '.rs', '.kt', '.swift', '.sql',
    '.html', '.css', '.scss', '.vue', '.dart', '.sh', '.ps1', '.md',
    '.txt', '.rst', '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg',
    '.env', '.xml', '.svg', '.drawio', '.mmd', '.mermaid', '.csv',
}
DOC_EXTENSIONS = {'.md', '.txt', '.rst', '.pdf', '.doc', '.docx'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.drawio'}
SQL_EXTENSIONS = {'.sql'}
DB_EXTENSIONS = {'.sqlite', '.sqlite3', '.db'}
TEST_NAME_RE = re.compile(r'(^test_.*\.py$|.*_test\.py$|.*\.test\.(js|ts|tsx|jsx)$|.*\.spec\.(js|ts|tsx|jsx)$)')
SNAKE_CASE_RE = re.compile(r'^[a-z0-9_]+$')

# These are security exclusions; user/assignment patterns may add to them but
# can never remove them.
SERVER_EXCLUSIONS = [
    '.git/', '.git/**', '.hg/**', '.svn/**',
    'node_modules/**', '.venv/**', 'venv/**', 'env/**',
    '__pycache__/**', '*.pyc', '*.pyo', '.pytest_cache/**',
    '.mypy_cache/**', '.ruff_cache/**', '.tox/**',
    '.DS_Store', 'Thumbs.db',
    '.env', '.env.local', '.env.development', '.env.production',
    '.env.test', '.env.staging',
    '*.pem', '*.key', '*.p12', '*.pfx', 'id_rsa', 'id_rsa.*',
    '.npmrc', '.netrc', '.pgpass',
]

DEFAULT_EXCLUSIONS = [
    '.classforgeignore',
    'media/**',
    'staticfiles/**',
    '*.log',
]


# ---------------------------------------------------------------------------
# Path handling
# ---------------------------------------------------------------------------

def normalise_path(raw):
    """Return a safe POSIX relative path or raise ``ValidationError``."""
    if raw is None:
        raise ValidationError('An uploaded file is missing its path.')
    path = str(raw).replace('\\', '/').strip()
    if not path:
        raise ValidationError('An uploaded file has an empty path.')
    if '\x00' in path or any(ord(ch) < 32 for ch in path):
        raise ValidationError(f'Invalid control character in path: {path!r}.')
    if re.match(r'^[A-Za-z]:', path):
        raise ValidationError(f'Absolute paths are not allowed: {path!r}.')
    path = path.lstrip('/')
    parts = [part for part in path.split('/') if part not in ('', '.')]
    if not parts:
        raise ValidationError(f'Invalid path: {path!r}.')
    if any(part == '..' for part in parts):
        raise ValidationError(f'Path traversal is not allowed: {path!r}.')
    if len(parts) > 32:
        raise ValidationError(f'Path is nested too deeply: {path!r}.')
    clean = '/'.join(parts)
    if len(clean) > 400:
        raise ValidationError('Path is too long.')
    return clean


def pattern_matches(path, pattern):
    pattern = (pattern or '').strip()
    if not pattern or pattern.startswith('#'):
        return False
    path = path.replace('\\', '/')
    pattern = pattern.replace('\\', '/')
    if pattern.endswith('/'):
        pattern += '**'
    if pattern in ('.git', '.git/'):
        return path == '.git' or path.startswith('.git/')
    if fnmatch.fnmatchcase(path, pattern):
        return True
    if fnmatch.fnmatchcase(posixpath.basename(path), pattern):
        return True
    return False


def should_exclude(path, patterns):
    """Apply user patterns (with ``!`` negation) then hard server exclusions."""
    excluded = False
    for pattern in patterns or []:
        pattern = (pattern or '').strip()
        if not pattern or pattern.startswith('#'):
            continue
        if pattern.startswith('!'):
            if pattern_matches(path, pattern[1:]):
                excluded = False
            continue
        if pattern_matches(path, pattern):
            excluded = True
    if excluded:
        # Never allow a negation to re-include a known secret/security path.
        for pattern in SERVER_EXCLUSIONS:
            if pattern_matches(path, pattern):
                return True
        return True
    return any(pattern_matches(path, pattern) for pattern in SERVER_EXCLUSIONS)


def effective_exclusions(assignment, extra_patterns=None):
    patterns = list(DEFAULT_EXCLUSIONS) + list(SERVER_EXCLUSIONS)
    if assignment is not None:
        patterns.extend(assignment.default_exclusions_list)
    patterns.extend(extra_patterns or [])
    return patterns


def _extension(path):
    return posixpath.splitext(path)[1].lower()


def _is_text_path(path):
    return _extension(path) in TEXT_EXTENSIONS


# ---------------------------------------------------------------------------
# Canonical zip creation
# ---------------------------------------------------------------------------

def _zip_info(path):
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def build_archive(assignment, files, paths=None, extra_exclusions=None):
    """Build a deterministic zip from ``(name, bytes)`` pairs.

    Returns ``(archive_bytes, included, excluded)``.  ``excluded`` is a list of
    ``{'path', 'reason'}`` records, never silently discarded.
    """
    files = list(files or [])
    if paths is not None and len(paths) != len(files):
        raise ValidationError('The file list and path list must have the same length.')
    patterns = effective_exclusions(assignment, extra_exclusions)

    max_files = int(getattr(settings, 'CLASSFORGE_MAX_SNAPSHOT_FILES', 500))
    max_bytes = int(getattr(settings, 'CLASSFORGE_MAX_SNAPSHOT_BYTES', 50 * 1024 * 1024))
    if assignment is not None:
        max_bytes = min(
            max_bytes,
            int(assignment.max_upload_mb or 25) * 1024 * 1024,
        )

    entries = {}
    excluded = []
    total = 0
    for index, handle in enumerate(files):
        raw_path = paths[index] if paths is not None else getattr(handle, 'name', '')
        try:
            path = normalise_path(raw_path)
        except ValidationError as exc:
            excluded.append({'path': str(raw_path)[:300], 'reason': exc.messages[0]})
            continue
        if should_exclude(path, patterns):
            excluded.append({'path': path, 'reason': 'excluded by policy'})
            continue
        if path in entries:
            excluded.append({'path': path, 'reason': 'duplicate path'})
            continue
        try:
            data = handle.read() if hasattr(handle, 'read') else bytes(handle)
        except Exception as exc:  # pragma: no cover - upload stream errors
            excluded.append({'path': path, 'reason': f'unreadable: {exc.__class__.__name__}'})
            continue
        if not isinstance(data, bytes):
            data = bytes(data)
        total += len(data)
        if len(entries) + 1 > max_files:
            raise ValidationError(
                f'The upload exceeds the {max_files} file limit.'
            )
        if total > max_bytes:
            raise ValidationError(
                'The upload exceeds the configured size limit '
                f'({max_bytes // (1024 * 1024)} MB).'
            )
        entries[path] = data

    if not entries:
        raise ValidationError(
            'No files remain after applying exclusion rules. '
            'Check .classforgeignore and the assignment exclusions.'
        )

    buffer = io.BytesIO()
    included = []
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(entries):
            data = entries[path]
            archive.writestr(_zip_info(path), data)
            included.append(
                {
                    'path': path,
                    'size': len(data),
                    'sha256': hashlib.sha256(data).hexdigest(),
                    'extension': _extension(path),
                }
            )
    return buffer.getvalue(), included, excluded


# ---------------------------------------------------------------------------
# Archive inspection
# ---------------------------------------------------------------------------

def inspect_archive(archive_bytes):
    """Validate an archive and return ``(manifest, summary, issues)``.

    Nothing is extracted.  Encrypted files, traversal entries and oversized
    archives are reported rather than trusted.
    """
    max_files = int(getattr(settings, 'CLASSFORGE_MAX_SNAPSHOT_FILES', 500))
    max_bytes = int(getattr(settings, 'CLASSFORGE_MAX_SNAPSHOT_BYTES', 50 * 1024 * 1024))
    issues = []
    manifest = []
    total = 0
    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValidationError(
            f'The uploaded archive could not be opened: {exc.__class__.__name__}.'
        )

    with archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) > max_files:
            raise ValidationError(f'The archive contains more than {max_files} files.')
        for info in infos:
            try:
                path = normalise_path(info.filename)
            except ValidationError as exc:
                issues.append({'severity': 'critical', 'message': exc.messages[0]})
                continue
            if info.flag_bits & 0x1:
                issues.append(
                    {
                        'severity': 'critical',
                        'message': f'Encrypted archive entry cannot be inspected: {path}',
                    }
                )
                continue
            size = max(int(info.file_size or 0), 0)
            total += size
            if total > max_bytes:
                raise ValidationError(
                    f'The archive expands beyond the {max_bytes // (1024 * 1024)} MB limit.'
                )
            try:
                data = archive.read(info)
            except (RuntimeError, OSError, zipfile.BadZipFile) as exc:
                issues.append(
                    {
                        'severity': 'warning',
                        'message': f'Could not read {path}: {exc.__class__.__name__}',
                    }
                )
                continue
            manifest.append(
                {
                    'path': path,
                    'size': len(data),
                    'sha256': hashlib.sha256(data).hexdigest(),
                    'extension': _extension(path),
                    'is_text': _is_text_path(path),
                }
            )

    manifest.sort(key=lambda item: item['path'])
    summary = {
        'file_count': len(manifest),
        'total_bytes': sum(item['size'] for item in manifest),
        'source_count': sum(
            1
            for item in manifest
            if item['extension'] in TEXT_EXTENSIONS
            and item['extension'] not in DOC_EXTENSIONS
        ),
        'doc_count': sum(1 for item in manifest if item['extension'] in DOC_EXTENSIONS),
    }
    return manifest, summary, issues


def read_entry(archive_bytes, path):
    path = normalise_path(path)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        try:
            return archive.read(path)
        except KeyError:
            raise ValidationError(f'File not found in snapshot: {path}')


def read_archive_bytes(snapshot):
    try:
        with snapshot.archive.open('rb') as handle:
            return handle.read()
    except (OSError, ValueError) as exc:
        raise ValidationError(
            f'The snapshot archive is unavailable: {exc.__class__.__name__}.'
        )


# ---------------------------------------------------------------------------
# Git workspace (server-owned, student code never executed)
# ---------------------------------------------------------------------------

def git_enabled():
    return bool(getattr(settings, 'CLASSFORGE_GIT_ENABLED', True)) and bool(
        shutil.which('git')
    )


def git_workspace_path(project):
    root = Path(getattr(settings, 'CLASSFORGE_SNAPSHOT_ROOT', ''))
    return root / 'git' / f'project_{project.pk}'


def _git(args, cwd, timeout=90):
    env = os.environ.copy()
    env.setdefault('GIT_AUTHOR_NAME', getattr(settings, 'CLASSFORGE_GIT_AUTHOR', 'ClassForge'))
    env.setdefault(
        'GIT_AUTHOR_EMAIL',
        getattr(settings, 'CLASSFORGE_GIT_EMAIL', 'classforge@localhost'),
    )
    env.setdefault('GIT_COMMITTER_NAME', env['GIT_AUTHOR_NAME'])
    env.setdefault('GIT_COMMITTER_EMAIL', env['GIT_AUTHOR_EMAIL'])
    return subprocess.run(
        ['git', *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        check=False,
    )


def ensure_git_repository(project, branch='main'):
    path = git_workspace_path(project)
    repository, _ = Repository.objects.get_or_create(
        project=project, defaults={'default_branch': branch, 'current_branch': branch}
    )
    if not git_enabled():
        return repository
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not (path / '.git').exists():
            result = _git(['init', '-b', branch], path)
            if result.returncode != 0:
                _git(['init'], path)
            _git(['config', 'user.name', getattr(settings, 'CLASSFORGE_GIT_AUTHOR', 'ClassForge')], path)
            _git(['config', 'user.email', getattr(settings, 'CLASSFORGE_GIT_EMAIL', 'classforge@localhost')], path)
        repository.git_initialised = (path / '.git').exists()
        repository.save(update_fields=['git_initialised', 'updated_at'])
    except Exception:
        logger.warning('Could not initialise Git repository for project %s', project.pk, exc_info=True)
    return repository


def _clear_worktree(path):
    for entry in path.iterdir():
        if entry.name == '.git':
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            try:
                entry.unlink()
            except OSError:
                pass


def _extract_for_git(archive_bytes, destination):
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            path = normalise_path(info.filename)
            target = destination / Path(*path.split('/'))
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, open(target, 'wb') as handle:
                shutil.copyfileobj(source, handle)


def commit_snapshot(snapshot, branch=None):
    """Commit a snapshot archive to the project's Git workspace.

    Returns ``(commit_sha, base_commit_sha)``.  Failures are logged and do not
    block the snapshot from being stored.
    """
    project = snapshot.project
    repository = ensure_git_repository(project, snapshot.branch or 'main')
    if not git_enabled():
        return '', ''
    path = git_workspace_path(project)
    branch = branch or snapshot.branch or repository.current_branch or 'main'
    try:
        archive_bytes = read_archive_bytes(snapshot)
        _clear_worktree(path)
        _extract_for_git(archive_bytes, path)
        _git(['checkout', '-B', branch], path)
        _git(['add', '-A'], path)
        base = _git(['rev-parse', 'HEAD'], path)
        base_sha = base.stdout.strip() if base.returncode == 0 else ''
        message = f'ClassForge snapshot v{snapshot.version}'
        result = _git(['commit', '-m', message, '--allow-empty'], path)
        if result.returncode != 0:
            logger.warning('Git commit failed for snapshot %s: %s', snapshot.pk, result.stderr[:500])
            return '', base_sha
        head = _git(['rev-parse', 'HEAD'], path)
        commit_sha = head.stdout.strip() if head.returncode == 0 else ''
        repository.current_branch = branch
        repository.last_commit_sha = commit_sha
        repository.git_initialised = True
        repository.save(
            update_fields=['current_branch', 'last_commit_sha', 'git_initialised', 'updated_at']
        )
        return commit_sha, base_sha
    except Exception:
        logger.warning('Git snapshot commit failed for project %s', project.pk, exc_info=True)
        return '', ''


def git_merge(project, source_branch, target_branch):
    if not git_enabled():
        return ''
    path = git_workspace_path(project)
    try:
        _git(['checkout', target_branch], path)
        result = _git(['merge', '--no-ff', source_branch, '-m', f'Merge {source_branch} into {target_branch}'], path)
        if result.returncode != 0:
            return ''
        head = _git(['rev-parse', 'HEAD'], path)
        return head.stdout.strip() if head.returncode == 0 else ''
    except Exception:
        logger.warning('Git merge failed for project %s', project.pk, exc_info=True)
        return ''


# ---------------------------------------------------------------------------
# Project / snapshot lifecycle
# ---------------------------------------------------------------------------

def create_project(assignment, student, title='', description=''):
    project, _ = Project.objects.get_or_create(
        assignment=assignment,
        student=student,
        defaults={
            'title': (title or '').strip()[:255] or assignment.title[:255],
            'description': (description or '').strip(),
        },
    )
    ensure_git_repository(project)
    return project


def create_snapshot(
    project,
    *,
    archive_bytes=None,
    files=None,
    paths=None,
    source=ProjectSnapshot.SOURCE_API,
    note='',
    branch=None,
    created_by=None,
    submission=None,
    extra_exclusions=None,
    commit_to_git=True,
):
    if archive_bytes is None:
        archive_bytes, _, _ = build_archive(
            project.assignment, files or [], paths, extra_exclusions
        )
    if not archive_bytes:
        raise ValidationError('The snapshot archive is empty.')

    manifest, summary, issues = inspect_archive(archive_bytes)
    if not manifest:
        raise ValidationError('The snapshot contains no files.')

    version = (
        ProjectSnapshot.objects.filter(project=project).aggregate(
            max_version=models_max('version')
        )['max_version']
        or 0
    ) + 1

    checksum = hashlib.sha256(archive_bytes).hexdigest()
    branch = (branch or '').strip() or (
        project.repository.current_branch if hasattr(project, 'repository') else 'main'
    )
    snapshot = ProjectSnapshot(
        project=project,
        submission=submission,
        version=version,
        source=source,
        branch=branch,
        archive=None,
        checksum=checksum,
        file_count=summary['file_count'],
        total_bytes=summary['total_bytes'],
        manifest=manifest,
        validation={
            'issues': issues,
            'file_count': summary['file_count'],
            'total_bytes': summary['total_bytes'],
            'source_count': summary['source_count'],
            'doc_count': summary['doc_count'],
        },
        metadata={'exclusions': extra_exclusions or []},
        note=(note or '')[:500],
        created_by=created_by,
    )
    filename = f'project-{project.pk}-v{version}.zip'
    snapshot.archive.save(filename, ContentFile(archive_bytes), save=False)
    snapshot.save()

    if commit_to_git:
        commit_sha, base_sha = commit_snapshot(snapshot, branch)
        if commit_sha or base_sha:
            ProjectSnapshot.objects.filter(pk=snapshot.pk).update(
                commit_sha=commit_sha, base_commit_sha=base_sha
            )
            snapshot.commit_sha = commit_sha
            snapshot.base_commit_sha = base_sha
    return snapshot


def models_max(field):
    from django.db.models import Max

    return Max(field)


def create_submission_for_snapshot(snapshot, student, note=''):
    """Create an append-only ``courses.Submission`` that points at a snapshot."""
    if snapshot.submission_id:
        return snapshot.submission
    archive_bytes = read_archive_bytes(snapshot)
    submission = Submission(
        assignment=snapshot.project.assignment,
        student=student,
        text_content=(
            note
            or f'Project snapshot v{snapshot.version} '
            f'({snapshot.file_count} files, {snapshot.total_bytes} bytes).'
        ),
    )
    filename = f'project-{snapshot.project_id}-v{snapshot.version}.zip'
    submission.file_attachment.save(filename, ContentFile(archive_bytes), save=False)
    submission.save()
    ProjectSnapshot.objects.filter(pk=snapshot.pk).update(submission=submission)
    snapshot.submission = submission
    return submission


def save_web_submission_snapshot(submission, uploaded_file):
    """Best-effort snapshot creation for a web .zip upload.

    Returns the snapshot or ``None``.  Errors are swallowed because the
    submission itself must not fail if the workspace mirror cannot be built.
    """
    try:
        name = (uploaded_file.name or '').lower()
        if not name.endswith('.zip'):
            return None
        uploaded_file.seek(0)
        archive_bytes = uploaded_file.read()
        project = create_project(submission.assignment, submission.student)
        snapshot = create_snapshot(
            project,
            archive_bytes=archive_bytes,
            source=ProjectSnapshot.SOURCE_WEB,
            note=f'Imported with submission v{submission.version}',
            created_by=submission.student,
            submission=submission,
        )
        notify_course_staff(
            submission.assignment,
            kind=Notification.KIND_INFO,
            title=f'New project snapshot from {submission.student}',
            body=f'{submission.assignment.title} · v{snapshot.version}',
            url=f'/projects/snapshots/{snapshot.pk}/',
            project=project,
            snapshot=snapshot,
        )
        return snapshot
    except Exception:
        logger.warning('Could not mirror web submission %s into a project snapshot', submission.pk, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Diffing
# ---------------------------------------------------------------------------

def diff_manifests(base_manifest, target_manifest):
    base = {item['path']: item for item in base_manifest or []}
    target = {item['path']: item for item in target_manifest or []}
    added = sorted(set(target) - set(base))
    removed = sorted(set(base) - set(target))
    modified = sorted(
        path
        for path in set(base) & set(target)
        if base[path].get('sha256') != target[path].get('sha256')
    )
    unchanged = sorted(
        path
        for path in set(base) & set(target)
        if base[path].get('sha256') == target[path].get('sha256')
    )
    return {
        'added': [target[path] for path in added],
        'removed': [base[path] for path in removed],
        'modified': [target[path] for path in modified],
        'unchanged_count': len(unchanged),
        'summary': {
            'added': len(added),
            'removed': len(removed),
            'modified': len(modified),
            'unchanged': len(unchanged),
        },
    }


def diff_snapshots(base, target, max_text_bytes=60_000, max_diff_lines=200):
    result = diff_manifests(base.manifest, target.manifest)
    result['text_diffs'] = []
    if not base or not target:
        return result
    try:
        base_bytes = read_archive_bytes(base)
        target_bytes = read_archive_bytes(target)
    except ValidationError:
        return result

    for item in result['modified'][:12]:
        path = item['path']
        if not _is_text_path(path) or item.get('size', 0) > max_text_bytes:
            continue
        try:
            before = read_entry(base_bytes, path).decode('utf-8', errors='replace')
            after = read_entry(target_bytes, path).decode('utf-8', errors='replace')
        except (ValidationError, KeyError):
            continue
        lines = list(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile=f'v{base.version}/{path}',
                tofile=f'v{target.version}/{path}',
                lineterm='',
            )
        )
        if lines:
            result['text_diffs'].append(
                {
                    'path': path,
                    'diff': '\n'.join(lines[:max_diff_lines]),
                    'truncated': len(lines) > max_diff_lines,
                }
            )
    return result


# ---------------------------------------------------------------------------
# Rubric publication
# ---------------------------------------------------------------------------

def publish_rubric(rubric, user=None, notes=''):
    rubric = rubric.__class__.objects.select_related('assignment').get(pk=rubric.pk)
    criteria = [
        {
            'id': criterion.id,
            'name': criterion.name,
            'description': criterion.description,
            'max_points': str(criterion.max_points),
            'weight': str(criterion.weight),
            'position': criterion.position,
            'expected_evidence': criterion.expected_evidence,
            'scoring_guidance': criterion.scoring_guidance,
            'validation_rule': criterion.validation_rule,
            'ai_instructions': criterion.ai_instructions,
            'feedback_requirements': criterion.feedback_requirements,
        }
        for criterion in rubric.criteria.all()
    ]
    if not criteria:
        raise ValidationError('Add at least one criterion before publishing the rubric.')
    latest = rubric.versions.aggregate(max_version=models_max('version'))['max_version'] or 0
    total = sum((Decimal(item['max_points']) for item in criteria), Decimal('0'))
    version = RubricVersion.objects.create(
        rubric=rubric,
        assignment=rubric.assignment,
        version=latest + 1,
        snapshot={
            'title': rubric.title,
            'instructions': rubric.instructions,
            'criteria': criteria,
            'total_points': str(total),
        },
        total_points=total,
        notes=notes or '',
        published_by=user if getattr(user, 'pk', None) else None,
    )
    return version


# ---------------------------------------------------------------------------
# Assessment application
# ---------------------------------------------------------------------------

def apply_assessment(assessment, user):
    """Create/update an **unpublished** grade from a completed assessment."""
    if assessment.status != Assessment.STATUS_COMPLETED:
        raise ValidationError('Only completed assessments can be applied.')
    snapshot = assessment.snapshot
    submission = snapshot.submission
    if submission is None:
        submission = create_submission_for_snapshot(snapshot, snapshot.project.student)
    assignment = snapshot.project.assignment
    rubric = getattr(assignment, 'rubric', None)
    max_score = assignment.effective_max_score

    with transaction.atomic():
        grade, created = Grade.objects.get_or_create(
            submission=submission,
            defaults={'instructor': user, 'score': Decimal('0'), 'is_published': False},
        )
        if not created:
            grade.instructor = user

        score = assessment.instructor_score
        if score is None:
            score = assessment.overall_score
        score = max(Decimal('0'), min(score or Decimal('0'), max_score))

        criteria_by_id = {}
        for criterion in (rubric.criteria.all() if rubric else []):
            criteria_by_id[criterion.id] = criterion
        for item in assessment.criteria.all():
            criterion = criteria_by_id.get(item.criterion_id)
            if criterion is None:
                continue
            points = item.instructor_points
            if points is None:
                points = item.ai_points
            points = max(Decimal('0'), min(points, criterion.max_points))
            CriterionScore.objects.update_or_create(
                grade=grade,
                criterion=criterion,
                defaults={
                    'points_awarded': points,
                    'comment': item.comment[:4000],
                },
            )

        if assessment.criteria.exists():
            total = sum(
                (row.points_awarded for row in grade.criterion_scores.all()),
                Decimal('0'),
            )
            score = min(total, max_score)
        grade.score = score
        feedback = (assessment.instructor_feedback or assessment.feedback or '').strip()
        if feedback:
            if (grade.feedback or '').strip():
                grade.feedback = (
                    grade.feedback.rstrip()
                    + '\n\n--- Project assessment (reviewed by instructor) ---\n'
                    + feedback
                )
            else:
                grade.feedback = feedback
        grade.is_published = False
        grade.published_at = None
        grade.published_by = None
        grade.save()

        assessment.applied_grade = grade
        assessment.applied_at = timezone.now()
        assessment.save(update_fields=['applied_grade', 'applied_at'])

    return grade, created


def review_assessment(assessment, user, action, *, instructor_score=None,
                      instructor_feedback='', criterion_scores=None):
    action = (action or '').strip().lower()
    mapping = {
        'approve': Assessment.REVIEW_APPROVED,
        'override': Assessment.REVIEW_OVERRIDDEN,
        'reject': Assessment.REVIEW_REJECTED,
    }
    if action not in mapping:
        raise ValidationError('Unknown review action.')
    if assessment.status != Assessment.STATUS_COMPLETED:
        raise ValidationError('Only completed assessments can be reviewed.')

    if instructor_score is not None:
        assessment.instructor_score = max(
            Decimal('0'), min(Decimal(str(instructor_score)), assessment.max_score or Decimal('0'))
        )
    assessment.instructor_feedback = (instructor_feedback or '').strip()[:20_000]
    assessment.review_status = mapping[action]
    assessment.reviewer = user
    assessment.reviewed_at = timezone.now()

    if criterion_scores:
        for criterion in assessment.criteria.all():
            if str(criterion.pk) not in criterion_scores:
                continue
            value = criterion_scores[str(criterion.pk)]
            if value in (None, ''):
                criterion.instructor_points = None
            else:
                criterion.instructor_points = max(
                    Decimal('0'), min(Decimal(str(value)), criterion.max_points)
                )
            criterion.save(update_fields=['instructor_points'])

    assessment.save(
        update_fields=[
            'instructor_score',
            'instructor_feedback',
            'review_status',
            'reviewer',
            'reviewed_at',
        ]
    )
    return assessment


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def notify(user, *, kind=Notification.KIND_INFO, title, body='', url='', project=None, snapshot=None):
    if user is None or not getattr(user, 'pk', None):
        return None
    return Notification.objects.create(
        user=user,
        kind=kind,
        title=title[:255],
        body=body or '',
        url=url[:500],
        project=project,
        snapshot=snapshot,
    )


def notify_course_staff(assignment, **kwargs):
    course = assignment.course
    recipients = [course.instructor]
    recipients.extend(
        assistant.user for assistant in course.assistants.select_related('user')
    )
    seen = set()
    created = []
    for user in recipients:
        if user is None or user.pk in seen:
            continue
        seen.add(user.pk)
        created.append(notify(user, **kwargs))
    return created


def unread_notification_count(user):
    if user is None or not getattr(user, 'is_authenticated', False):
        return 0
    return Notification.objects.filter(user=user, read_at__isnull=True).count()
