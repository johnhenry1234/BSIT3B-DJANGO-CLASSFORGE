"""JSON API v1 used by the ClassForge VS Code extension.

Authentication is a hashed bearer token (``Authorization: Bearer cf_...``).
Tokens are created from real credentials, are time-limited, can be revoked, and
are never stored in plaintext.  All endpoints are rate limited per token/IP.
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.core.audit import log_activity
from apps.courses.models import (
    Assignment,
    Course,
    Enrollment,
    Submission,
)
from apps.users.roles import can_grade_course, is_instructor, is_teaching_assistant

from . import assessment as assessment_module
from . import services
from .models import (
    ApiToken,
    Assessment,
    Notification,
    Project,
    ProjectSnapshot,
    PullRequest,
    PullRequestComment,
    RevisionRequest,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json(data, status=200):
    return JsonResponse(data, status=status, safe=False)


def _error(message, status=400, **extra):
    payload = {'ok': False, 'error': message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def _body(request):
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        raise ValidationError('Request body must be valid JSON.')
    if not isinstance(data, dict):
        raise ValidationError('Request body must be a JSON object.')
    return data


def _rate_limit(key):
    limit = int(getattr(settings, 'CLASSFORGE_API_RATE_LIMIT', 120))
    window = int(getattr(settings, 'CLASSFORGE_API_RATE_WINDOW', 60))
    if limit <= 0:
        return True
    cache_key = f'classforge-api-rate:{key}'
    try:
        added = cache.add(cache_key, 1, timeout=window)
        if added:
            return True
        return cache.incr(cache_key) <= limit
    except ValueError:
        return True


def _token_from_request(request):
    header = request.META.get('HTTP_AUTHORIZATION', '')
    if header.lower().startswith('bearer '):
        return ApiToken.authenticate(header[7:].strip())
    return None


def api_auth(scopes=('read',)):
    def decorator(view):
        @functools.wraps(view)
        @csrf_exempt
        def wrapper(request, *args, **kwargs):
            token = _token_from_request(request)
            if token is None:
                return _error('Authentication required. Send a bearer token.', 401)
            if any(scope not in token.scope_list for scope in scopes):
                return _error('This token does not have the required scope.', 403)
            request.api_token = token
            request.user = token.user
            if not _rate_limit(f'token:{token.pk}'):
                return _error('Rate limit exceeded. Try again shortly.', 429)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def _decorate(*decorators):
    def apply(view):
        for decorator in reversed(decorators):
            view = decorator(view)
        return view

    return apply


def _iso(value):
    return value.isoformat() if value else None


def _int_or_none(value):
    if value in (None, ''):
        return None
    try:
        return max(1, min(int(value), 3650))
    except (TypeError, ValueError):
        return None


def _decimal(value):
    if value is None:
        return None
    return str(Decimal(value).normalize())


def _assignment_payload(assignment):
    return {
        'id': assignment.id,
        'title': assignment.title,
        'course': {
            'id': assignment.course_id,
            'code': assignment.course.code,
            'name': assignment.course.name,
        },
        'category': assignment.category,
        'status': assignment.status,
        'due_date': _iso(assignment.due_date),
        'max_score': _decimal(assignment.effective_max_score),
        'guidelines': assignment.guidelines,
        'required_files': assignment.required_files_list,
        'required_directories': assignment.required_directories_list,
        'accepted_formats': assignment.accepted_formats_list,
        'documentation_requirements': assignment.documentation_requirements,
        'validation_rules': assignment.validation_rules_list,
        'required_tests': assignment.required_tests_list,
        'max_upload_mb': assignment.max_upload_mb,
        'ai_grading_mode': assignment.ai_grading_mode,
        'manual_review_required': assignment.manual_review_required,
        'allow_resubmission': assignment.allow_resubmission,
        'late_policy': assignment.late_policy,
        'default_exclusions': assignment.default_exclusions_list,
        'rubric_total_points': _decimal(assignment.rubric_total_points),
        'accepted_types': assignment.accepted_types,
    }


def _project_payload(project, user=None):
    repository = getattr(project, 'repository', None)
    latest = project.snapshots.order_by('-version').first()
    return {
        'id': project.id,
        'title': project.title,
        'status': project.status,
        'assignment': _assignment_payload(project.assignment),
        'student': {
            'id': project.student_id,
            'username': project.student.username,
            'name': project.student.get_full_name() or project.student.username,
        },
        'repository': (
            {
                'provider': repository.provider,
                'default_branch': repository.default_branch,
                'current_branch': repository.current_branch,
                'last_commit_sha': repository.last_commit_sha,
                'git_initialised': repository.git_initialised,
            }
            if repository
            else None
        ),
        'latest_snapshot': _snapshot_summary(latest) if latest else None,
        'open_revisions': project.revision_requests.filter(
            status=RevisionRequest.STATUS_OPEN
        ).count(),
        'open_pull_requests': project.pull_requests.filter(
            status=PullRequest.STATUS_OPEN
        ).count(),
        'created_at': _iso(project.created_at),
        'updated_at': _iso(project.updated_at),
    }


def _snapshot_summary(snapshot):
    return {
        'id': snapshot.id,
        'project_id': snapshot.project_id,
        'version': snapshot.version,
        'source': snapshot.source,
        'branch': snapshot.branch,
        'file_count': snapshot.file_count,
        'total_bytes': snapshot.total_bytes,
        'checksum': snapshot.checksum,
        'commit_sha': snapshot.commit_sha,
        'created_at': _iso(snapshot.created_at),
        'created_by': snapshot.created_by_id,
        'note': snapshot.note,
    }


def _snapshot_payload(snapshot, include_manifest=False):
    data = _snapshot_summary(snapshot)
    data['manifest'] = snapshot.manifest if include_manifest else []
    data['validation'] = snapshot.validation
    data['metadata'] = snapshot.metadata
    data['submission_id'] = snapshot.submission_id
    data['branch'] = snapshot.branch
    data['parent_id'] = snapshot.parent_id
    data['previous_id'] = (
        ProjectSnapshot.objects.filter(
            project_id=snapshot.project_id, version__lt=snapshot.version
        )
        .order_by('-version')
        .values_list('id', flat=True)
        .first()
    )
    if include_manifest:
        data['file_count'] = len(snapshot.manifest or [])
    return data


def _criteria_payload(assessment):
    return [
        {
            'id': item.id,
            'criterion_id': item.criterion_id,
            'name': item.criterion_name,
            'position': item.position,
            'max_points': _decimal(item.max_points),
            'ai_points': _decimal(item.ai_points),
            'instructor_points': _decimal(item.instructor_points),
            'points': _decimal(item.points),
            'comment': item.comment,
            'evidence': item.evidence,
            'confidence': _decimal(item.confidence),
        }
        for item in assessment.criteria.all()
    ]


def _assessment_payload(assessment, include_details=False):
    data = {
        'id': assessment.id,
        'snapshot_id': assessment.snapshot_id,
        'status': assessment.status,
        'engine': assessment.engine,
        'model_name': assessment.model_name,
        'mode': assessment.mode,
        'score': _decimal(assessment.overall_score),
        'max_score': _decimal(assessment.max_score),
        'instructor_score': _decimal(assessment.instructor_score),
        'summary': assessment.summary,
        'feedback': assessment.feedback,
        'requires_review': assessment.requires_review,
        'review_status': assessment.review_status,
        'applied_at': _iso(assessment.applied_at),
        'created_at': _iso(assessment.created_at),
        'completed_at': _iso(assessment.completed_at),
        'error': assessment.error,
        'attempts': assessment.attempts,
        'criteria': _criteria_payload(assessment),
    }
    if include_details:
        data['checks'] = assessment.checks
        data['evidence'] = assessment.evidence
        data['structure'] = assessment.structure
        data['artifacts'] = assessment.artifacts
        data['validation'] = assessment.validation
    return data


def _project_for_user(user, project_id):
    project = get_object_or_404(
        Project.objects.select_related(
            'assignment__course', 'assignment__course__instructor', 'student'
        ).prefetch_related('repository'),
        pk=project_id,
    )
    if project.student_id == user.id:
        return project
    if can_grade_course(user, project.assignment.course):
        return project
    raise PermissionDenied('You do not have access to this project.')


def _snapshot_for_user(user, snapshot_id):
    snapshot = get_object_or_404(
        ProjectSnapshot.objects.select_related(
            'project__assignment__course', 'project__student'
        ),
        pk=snapshot_id,
    )
    project = snapshot.project
    if project.student_id == user.id or can_grade_course(
        user, project.assignment.course
    ):
        return snapshot
    raise PermissionDenied('You do not have access to this snapshot.')


def _visible_projects(user):
    queryset = Project.objects.select_related(
        'assignment__course', 'student'
    ).prefetch_related('repository')
    if user.is_superuser:
        return queryset
    if is_instructor(user) or is_teaching_assistant(user):
        courses = Course.objects.filter(
            models_q_instructor_or_assistant(user)
        ).distinct()
        taught = queryset.filter(assignment__course__in=courses)
        own = queryset.filter(student=user)
        return (taught | own).distinct()
    return queryset.filter(student=user)


def models_q_instructor_or_assistant(user):
    from django.db.models import Q

    return Q(instructor=user) | Q(assistants__user=user)


def _assignment_visible(user, assignment):
    if can_grade_course(user, assignment.course):
        return True
    return assignment.course.enrollments.filter(student=user).exists()


# ---------------------------------------------------------------------------
# Token endpoints
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(['POST'])
def token_create(request):
    if not _rate_limit(f'ip:{_client_ip(request)}'):
        return _error('Too many login attempts. Try again shortly.', 429)
    try:
        data = _body(request)
    except ValidationError as exc:
        return _error(exc.messages[0])
    username = str(data.get('username') or '').strip()
    password = str(data.get('password') or '')
    if not username or not password:
        return _error('username and password are required.')
    user = authenticate(request, username=username, password=password)
    if user is None:
        log_activity(
            action='api.token.failed',
            description='Failed API token request',
            metadata={'username': username[:100]},
            request=request,
        )
        return _error('Invalid username or password.', 401)
    token, raw = ApiToken.issue(
        user,
        name=str(data.get('name') or 'VS Code extension')[:120],
        scopes=str(data.get('scopes') or 'read write'),
        days=_int_or_none(data.get('days')),
    )
    log_activity(
        actor=user,
        action='api.token.created',
        entity=token,
        description=f'API token created for {user.username}',
        request=request,
    )
    return _json(
        {
            'ok': True,
            'token': raw,
            'prefix': token.prefix,
            'expires_at': _iso(token.expires_at),
            'scopes': token.scope_list,
        },
        status=201,
    )


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def token_list(request):
    if request.method == 'POST':
        # Session-authenticated token creation from the web UI.
        if not request.user.is_authenticated:
            return _error('Authentication required.', 401)
        token, raw = ApiToken.issue(request.user, name=request.POST.get('name') or 'Web-created token')
        log_activity(
            actor=request.user,
            action='api.token.created',
            entity=token,
            description='API token created from the web UI',
            request=request,
        )
        return _json(
            {
                'ok': True,
                'token': raw,
                'prefix': token.prefix,
                'expires_at': _iso(token.expires_at),
            },
            status=201,
        )
    if not request.user.is_authenticated:
        return _error('Authentication required.', 401)
    return _json(
        {
            'ok': True,
            'tokens': [
                {
                    'id': token.id,
                    'name': token.name,
                    'prefix': token.prefix,
                    'scopes': token.scope_list,
                    'created_at': _iso(token.created_at),
                    'expires_at': _iso(token.expires_at),
                    'last_used_at': _iso(token.last_used_at),
                    'revoked_at': _iso(token.revoked_at),
                }
                for token in ApiToken.objects.filter(user=request.user)[:50]
            ],
        }
    )


@csrf_exempt
@require_http_methods(['POST'])
def token_revoke(request, pk):
    if not request.user.is_authenticated:
        return _error('Authentication required.', 401)
    token = get_object_or_404(ApiToken, pk=pk, user=request.user)
    token.revoked_at = timezone.now()
    token.save(update_fields=['revoked_at'])
    log_activity(
        actor=request.user,
        action='api.token.revoked',
        entity=token,
        description='API token revoked',
        request=request,
    )
    return _json({'ok': True})


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

@api_auth(('read',))
@require_http_methods(['GET'])
def me(request):
    user = request.user
    return _json(
        {
            'ok': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'name': user.get_full_name() or user.username,
                'email': user.email,
                'is_instructor': is_instructor(user),
                'is_teaching_assistant': is_teaching_assistant(user),
            },
            'scopes': request.api_token.scope_list,
            'token_expires_at': _iso(request.api_token.expires_at),
            'limits': {
                'max_upload_mb': getattr(settings, 'CLASSFORGE_MAX_UPLOAD_MB', 25),
                'max_files': getattr(settings, 'CLASSFORGE_MAX_SNAPSHOT_FILES', 500),
                'max_bytes': getattr(settings, 'CLASSFORGE_MAX_SNAPSHOT_BYTES', 50 * 1024 * 1024),
            },
        }
    )


@api_auth(('read',))
@require_http_methods(['GET'])
def courses(request):
    user = request.user
    if user.is_superuser:
        queryset = Course.objects.all()
    elif is_instructor(user):
        queryset = Course.objects.filter(
            models_q_instructor_or_assistant(user)
        ).distinct()
    elif is_teaching_assistant(user):
        queryset = Course.objects.filter(assistants__user=user).distinct()
    else:
        queryset = Course.objects.filter(enrollments__student=user).distinct()
    queryset = queryset.select_related('instructor').order_by('code')
    return _json(
        {
            'ok': True,
            'courses': [
                {
                    'id': course.id,
                    'code': course.code,
                    'name': course.name,
                    'instructor': course.instructor.get_full_name()
                    or course.instructor.username,
                    'assignment_count': course.assignments.count(),
                }
                for course in queryset
            ],
        }
    )


@api_auth(('read',))
@require_http_methods(['GET'])
def assignments(request):
    user = request.user
    course_id = request.GET.get('course')
    queryset = Assignment.objects.select_related('course').prefetch_related(
        'rubric__criteria'
    )
    if course_id:
        queryset = queryset.filter(course_id=course_id)
    if not (is_instructor(user) or is_teaching_assistant(user) or user.is_superuser):
        queryset = queryset.filter(
            course__enrollments__student=user,
            status=Assignment.STATUS_PUBLISHED,
        )
    elif not user.is_superuser:
        queryset = queryset.filter(
            models_q_course_instructor_or_assistant(user)
        ).distinct()
    queryset = queryset.order_by('due_date')
    return _json(
        {'ok': True, 'assignments': [_assignment_payload(item) for item in queryset]}
    )


def models_q_course_instructor_or_assistant(user):
    from django.db.models import Q

    return Q(course__instructor=user) | Q(course__assistants__user=user)


@api_auth(('read',))
@require_http_methods(['GET'])
def assignment_detail(request, pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related('course'), pk=pk
    )
    if not _assignment_visible(request.user, assignment):
        return _error('You do not have access to this assignment.', 403)
    payload = _assignment_payload(assignment)
    rubric = getattr(assignment, 'rubric', None)
    payload['rubric'] = (
        [
            {
                'id': criterion.id,
                'name': criterion.name,
                'description': criterion.description,
                'max_points': _decimal(criterion.max_points),
                'expected_evidence': criterion.expected_evidence,
                'validation_rule': criterion.validation_rule,
            }
            for criterion in rubric.criteria.all()
        ]
        if rubric
        else []
    )
    payload['published_rubric_version'] = (
        assignment.rubric_versions.order_by('-version')
        .values('id', 'version', 'total_points', 'published_at')
        .first()
    )

    if not (is_instructor(request.user) or is_teaching_assistant(request.user)):
        try:
            project = Project.objects.get(assignment=assignment, student=request.user)
        except Project.DoesNotExist:
            project = None
        payload['project'] = _project_payload(project, request.user) if project else None
    return _json({'ok': True, 'assignment': payload})


@api_auth(('read',))
@require_http_methods(['GET'])
def project_list(request):
    projects = _visible_projects(request.user).order_by('-updated_at')[:100]
    return _json(
        {'ok': True, 'projects': [_project_payload(project, request.user) for project in projects]}
    )


@api_auth(('read',))
@require_http_methods(['GET'])
def project_detail(request, pk):
    project = _project_for_user(request.user, pk)
    snapshots = project.snapshots.select_related('created_by').order_by('-version')[:50]
    return _json(
        {
            'ok': True,
            'project': _project_payload(project, request.user),
            'snapshots': [_snapshot_summary(item) for item in snapshots],
            'revision_requests': [
                _revision_payload(item)
                for item in project.revision_requests.select_related('requested_by')[:50]
            ],
            'pull_requests': [
                _pull_request_payload(item)
                for item in project.pull_requests.select_related('created_by')[:50]
            ],
        }
    )


@api_auth(('read',))
@require_http_methods(['GET'])
def snapshot_list(request, project_id):
    project = _project_for_user(request.user, project_id)
    snapshots = project.snapshots.select_related('created_by').order_by('-version')[:100]
    return _json(
        {
            'ok': True,
            'project_id': project.id,
            'snapshots': [_snapshot_summary(item) for item in snapshots],
        }
    )


@api_auth(('read',))
@require_http_methods(['GET'])
def snapshot_detail(request, pk):
    snapshot = _snapshot_for_user(request.user, pk)
    return _json(
        {
            'ok': True,
            'snapshot': _snapshot_payload(snapshot, include_manifest=True),
            'project': _project_payload(snapshot.project, request.user),
        }
    )


@api_auth(('read',))
@require_http_methods(['GET'])
def snapshot_status(request, pk):
    snapshot = _snapshot_for_user(request.user, pk)
    latest = snapshot.assessments.order_by('-created_at').first()
    return _json(
        {
            'ok': True,
            'snapshot': _snapshot_summary(snapshot),
            'assessment': _assessment_payload(latest) if latest else None,
        }
    )


@api_auth(('read',))
@require_http_methods(['GET'])
def snapshot_feedback(request, pk):
    snapshot = _snapshot_for_user(request.user, pk)
    latest = snapshot.assessments.order_by('-created_at').first()
    if latest is None:
        return _json({'ok': True, 'feedback': None, 'assessment': None})
    return _json(
        {
            'ok': True,
            'assessment': _assessment_payload(latest, include_details=True),
            'grade': _grade_payload(snapshot),
        }
    )


def _grade_payload(snapshot):
    if snapshot.submission_id is None:
        return None
    try:
        grade = snapshot.submission.grade
    except Exception:
        return None
    return {
        'id': grade.id,
        'score': _decimal(grade.score),
        'max_score': _decimal(grade.max_score),
        'feedback': grade.feedback,
        'is_published': grade.is_published,
        'graded_at': _iso(grade.graded_at),
    }


@api_auth(('read',))
@require_http_methods(['GET'])
def snapshot_diff(request, pk):
    target = _snapshot_for_user(request.user, pk)
    base_id = request.GET.get('base')
    if base_id:
        base = _snapshot_for_user(request.user, base_id)
        if base.project_id != target.project_id:
            return _error('Snapshots belong to different projects.')
    else:
        base = (
            ProjectSnapshot.objects.filter(
                project_id=target.project_id, version__lt=target.version
            )
            .order_by('-version')
            .first()
        )
    if base is None:
        return _json(
            {
                'ok': True,
                'base': None,
                'target': _snapshot_summary(target),
                'diff': None,
                'message': 'This is the first snapshot; there is nothing to compare.',
            }
        )
    diff = services.diff_snapshots(base, target)
    return _json(
        {
            'ok': True,
            'base': _snapshot_summary(base),
            'target': _snapshot_summary(target),
            'diff': diff,
        }
    )


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

@api_auth(('write',))
@require_http_methods(['POST'])
def assignment_submit(request, pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related('course'), pk=pk
    )
    user = request.user
    if not _assignment_visible(user, assignment):
        return _error('You are not enrolled in this course.', 403)
    if assignment.status != Assignment.STATUS_PUBLISHED and not can_grade_course(
        user, assignment.course
    ):
        return _error('This assignment is not published.', 403)

    upload = request.FILES.get('archive')
    files = request.FILES.getlist('files') or request.FILES.getlist('files[]')
    extra_exclusions = []
    ignore_file = request.FILES.get('classforgeignore')
    if ignore_file is not None:
        try:
            extra_exclusions.extend(
                line.strip()
                for line in ignore_file.read().decode('utf-8', errors='replace').splitlines()
                if line.strip() and not line.strip().startswith('#')
            )
        except Exception:
            return _error('Could not read .classforgeignore.')
    raw_paths = request.POST.get('paths') or request.POST.get('paths[]')
    paths = None
    if raw_paths:
        try:
            paths = json.loads(raw_paths)
        except ValueError:
            return _error('paths must be a JSON array of relative paths.')
        if not isinstance(paths, list):
            return _error('paths must be a JSON array.')
    elif files:
        paths = [getattr(handle, 'name', '') for handle in files]

    try:
        if upload is not None:
            archive_bytes = upload.read()
        elif files:
            archive_bytes, _, excluded = services.build_archive(
                assignment, files, paths, extra_exclusions
            )
        else:
            return _error('Upload at least one file (files[]) or an archive.')
    except ValidationError as exc:
        return _error(exc.messages[0] if exc.messages else 'Invalid upload.', 422)

    branch = (request.POST.get('branch') or 'main').strip() or 'main'
    note = request.POST.get('note') or ''
    source = (
        ProjectSnapshot.SOURCE_VSCODE
        if request.POST.get('source') == ProjectSnapshot.SOURCE_VSCODE or request.POST.get('client') == 'vscode'
        else ProjectSnapshot.SOURCE_API
    )
    create_submission = request.POST.get('create_submission', '1').lower() not in (
        '0', 'false', 'no'
    )

    try:
        project = services.create_project(assignment, user)
        snapshot = services.create_snapshot(
            project,
            archive_bytes=archive_bytes,
            source=source,
            note=note,
            branch=branch,
            created_by=user,
            extra_exclusions=extra_exclusions,
        )
        submission = None
        if create_submission:
            submission = services.create_submission_for_snapshot(
                snapshot, user, note=note
            )
    except ValidationError as exc:
        return _error(exc.messages[0] if exc.messages else 'Could not create snapshot.', 422)
    except Exception:
        logger.exception('API snapshot upload failed')
        return _error('Could not create the project snapshot.', 500)

    services.notify_course_staff(
        assignment,
        kind=Notification.KIND_INFO,
        title=f'New project snapshot from {user}',
        body=f'{assignment.title} · v{snapshot.version}',
        url=f'/projects/snapshots/{snapshot.pk}/',
        project=project,
        snapshot=snapshot,
    )
    log_activity(
        request,
        action='project.snapshot.created',
        entity=snapshot,
        description=f'Uploaded project snapshot v{snapshot.version} for {assignment.title}',
        metadata={
            'course_id': assignment.course_id,
            'assignment_id': assignment.id,
            'project_id': project.id,
            'file_count': snapshot.file_count,
        },
    )

    assessment = None
    if assignment.ai_auto_run:
        try:
            assessment = assessment_module.request_assessment(snapshot, user)
        except Exception:
            logger.warning('Could not queue assessment after API upload', exc_info=True)

    return _json(
        {
            'ok': True,
            'project': _project_payload(project, user),
            'snapshot': _snapshot_payload(snapshot, include_manifest=True),
            'submission': (
                {
                    'id': submission.id,
                    'version': submission.version,
                    'is_late': submission.is_late,
                }
                if submission
                else None
            ),
            'assessment': _assessment_payload(assessment) if assessment else None,
        },
        status=201,
    )


@api_auth(('write',))
@require_http_methods(['POST'])
def snapshot_assess(request, pk):
    snapshot = _snapshot_for_user(request.user, pk)
    try:
        assessment = assessment_module.request_assessment(snapshot, request.user)
    except ValidationError as exc:
        return _error(exc.messages[0] if exc.messages else 'Could not queue assessment.')
    return _json(
        {'ok': True, 'assessment': _assessment_payload(assessment)}, status=202
    )


# ---------------------------------------------------------------------------
# Revision requests and pull requests
# ---------------------------------------------------------------------------

def _revision_payload(revision):
    return {
        'id': revision.id,
        'project_id': revision.project_id,
        'snapshot_id': revision.snapshot_id,
        'title': revision.title,
        'description': revision.description,
        'branch_name': revision.branch_name,
        'due_date': _iso(revision.due_date),
        'status': revision.status,
        'requested_by': revision.requested_by_id,
        'created_at': _iso(revision.created_at),
        'resolved_at': _iso(revision.resolved_at),
    }


@api_auth(('read',))
@require_http_methods(['GET'])
def revision_list(request):
    queryset = RevisionRequest.objects.select_related('project', 'requested_by')
    user = request.user
    if not (user.is_superuser or is_instructor(user) or is_teaching_assistant(user)):
        queryset = queryset.filter(project__student=user)
    else:
        courses = Course.objects.filter(models_q_instructor_or_assistant(user)).distinct()
        queryset = queryset.filter(project__assignment__course__in=courses)
    return _json(
        {'ok': True, 'revision_requests': [_revision_payload(item) for item in queryset[:100]]}
    )


@api_auth(('read',))
@require_http_methods(['GET'])
def revision_list_by_project(request, project_id):
    project = _project_for_user(request.user, project_id)
    rows = project.revision_requests.select_related('requested_by')[:100]
    return _json(
        {
            'ok': True,
            'project_id': project.id,
            'revision_requests': [_revision_payload(item) for item in rows],
        }
    )


@api_auth(('write',))
@require_http_methods(['POST'])
def revision_create(request, project_id):
    project = _project_for_user(request.user, project_id)
    if not can_grade_course(request.user, project.assignment.course):
        return _error('Only the instructor or a TA can request revisions.', 403)
    try:
        data = _body(request)
    except ValidationError as exc:
        return _error(exc.messages[0])
    title = str(data.get('title') or '').strip()
    if not title:
        return _error('A revision request title is required.')
    revision = RevisionRequest.objects.create(
        project=project,
        snapshot_id=data.get('snapshot_id') or None,
        title=title[:255],
        description=str(data.get('description') or '')[:10_000],
        branch_name=str(data.get('branch_name') or '')[:128],
        requested_by=request.user,
    )
    services.notify(
        project.student,
        kind=Notification.KIND_REVISION,
        title=f'Revision requested: {revision.title}',
        body=revision.description[:1000],
        url=f'/projects/{project.pk}/',
        project=project,
        snapshot=revision.snapshot,
    )
    log_activity(
        request,
        action='project.revision.requested',
        entity=revision,
        description=f'Revision requested for {project}',
        metadata={
            'course_id': project.assignment.course_id,
            'project_id': project.pk,
        },
    )
    return _json({'ok': True, 'revision_request': _revision_payload(revision)}, status=201)


@api_auth(('write',))
@require_http_methods(['POST'])
def revision_update(request, pk):
    revision = get_object_or_404(
        RevisionRequest.objects.select_related(
            'project__assignment__course', 'project__student'
        ),
        pk=pk,
    )
    project = revision.project
    if not can_grade_course(request.user, project.assignment.course):
        return _error('Only the instructor or a TA can update revisions.', 403)
    try:
        data = _body(request)
    except ValidationError as exc:
        return _error(exc.messages[0])
    status = str(data.get('status') or '').strip()
    if status not in dict(RevisionRequest.STATUS_CHOICES):
        return _error('Invalid revision status.')
    revision.status = status
    if status in (RevisionRequest.STATUS_ADDRESSED, RevisionRequest.STATUS_CLOSED):
        revision.resolved_by = request.user
        revision.resolved_at = timezone.now()
    revision.save()
    if status == RevisionRequest.STATUS_ADDRESSED:
        services.notify(
            project.student,
            kind=Notification.KIND_REVISION,
            title=f'Revision addressed: {revision.title}',
            body='Your instructor marked this revision request as addressed.',
            url=f'/projects/{project.pk}/',
            project=project,
        )
    return _json({'ok': True, 'revision_request': _revision_payload(revision)})


def _pull_request_payload(pull_request):
    return {
        'id': pull_request.id,
        'project_id': pull_request.project_id,
        'title': pull_request.title,
        'description': pull_request.description,
        'source_snapshot_id': pull_request.source_snapshot_id,
        'merged_snapshot_id': pull_request.merged_snapshot_id,
        'revision_request_id': pull_request.revision_request_id,
        'source_branch': pull_request.source_branch,
        'target_branch': pull_request.target_branch,
        'status': pull_request.status,
        'created_by': pull_request.created_by_id,
        'reviewed_by': pull_request.reviewed_by_id,
        'merge_commit_sha': pull_request.merge_commit_sha,
        'created_at': _iso(pull_request.created_at),
        'merged_at': _iso(pull_request.merged_at),
        'comments': [
            {
                'id': comment.id,
                'author': comment.author.username,
                'body': comment.body,
                'created_at': _iso(comment.created_at),
            }
            for comment in pull_request.comments.select_related('author')
        ],
    }


@api_auth(('read',))
@require_http_methods(['GET'])
def pull_request_list(request, project_id):
    project = _project_for_user(request.user, project_id)
    rows = project.pull_requests.select_related('created_by').prefetch_related(
        'comments__author'
    )[:100]
    return _json(
        {'ok': True, 'pull_requests': [_pull_request_payload(item) for item in rows]}
    )


@api_auth(('read',))
@require_http_methods(['GET'])
def pull_request_global_list(request):
    user = request.user
    queryset = PullRequest.objects.select_related(
        'project', 'created_by'
    ).prefetch_related('comments__author')
    if not (user.is_superuser or is_instructor(user) or is_teaching_assistant(user)):
        queryset = queryset.filter(project__student=user)
    else:
        courses = Course.objects.filter(models_q_instructor_or_assistant(user)).distinct()
        queryset = queryset.filter(project__assignment__course__in=courses)
    return _json(
        {'ok': True, 'pull_requests': [_pull_request_payload(item) for item in queryset[:100]]}
    )


@api_auth(('write',))
@require_http_methods(['POST'])
def pull_request_create(request, project_id):
    project = _project_for_user(request.user, project_id)
    try:
        data = _body(request)
    except ValidationError as exc:
        return _error(exc.messages[0])
    latest = project.latest_snapshot
    snapshot_id = data.get('source_snapshot_id') or (latest.pk if latest else None)
    if snapshot_id is None:
        return _error('Upload a project snapshot before opening a pull request.')
    try:
        snapshot = project.snapshots.get(pk=snapshot_id)
    except ProjectSnapshot.DoesNotExist:
        return _error('Source snapshot not found.', 404)
    title = str(data.get('title') or '').strip()
    if not title:
        return _error('A pull-request title is required.')
    pull_request = PullRequest.objects.create(
        project=project,
        title=title[:255],
        description=str(data.get('description') or '')[:10_000],
        source_snapshot=snapshot,
        revision_request_id=data.get('revision_request_id') or None,
        source_branch=str(data.get('source_branch') or snapshot.branch or 'feature')[:128],
        target_branch=str(data.get('target_branch') or 'main')[:128],
        created_by=request.user,
    )
    services.notify_course_staff(
        project.assignment,
        kind=Notification.KIND_PULL_REQUEST,
        title=f'Pull request #{pull_request.pk}: {pull_request.title}',
        body=f'{project.student} requested a review.',
        url=f'/projects/pull-requests/{pull_request.pk}/',
        project=project,
        snapshot=snapshot,
    )
    log_activity(
        request,
        action='project.pull_request.created',
        entity=pull_request,
        description=f'Pull request created for {project}',
        metadata={
            'course_id': project.assignment.course_id,
            'project_id': project.pk,
            'snapshot_id': snapshot.pk,
        },
    )
    return _json(
        {'ok': True, 'pull_request': _pull_request_payload(pull_request)}, status=201
    )


@api_auth(('write',))
@require_http_methods(['POST'])
def pull_request_action(request, pk):
    pull_request = get_object_or_404(
        PullRequest.objects.select_related(
            'project__assignment__course', 'project__student', 'source_snapshot'
        ),
        pk=pk,
    )
    project = pull_request.project
    try:
        data = _body(request)
    except ValidationError as exc:
        return _error(exc.messages[0])
    action = str(data.get('action') or '').strip().lower()
    if action == 'comment':
        body = str(data.get('body') or '').strip()
        if not body:
            return _error('A comment body is required.')
        if not (
            project.student_id == request.user.id
            or can_grade_course(request.user, project.assignment.course)
        ):
            return _error('You cannot comment on this pull request.', 403)
        comment = PullRequestComment.objects.create(
            pull_request=pull_request, author=request.user, body=body[:10_000]
        )
        return _json(
            {'ok': True, 'comment': {'id': comment.id, 'body': comment.body}}
        )
    if not can_grade_course(request.user, project.assignment.course):
        return _error('Only the instructor or a TA can review pull requests.', 403)
    if action == 'merge':
        if pull_request.status != PullRequest.STATUS_OPEN:
            return _error('This pull request is not open.')
        merge_sha = services.git_merge(
            project, pull_request.source_branch, pull_request.target_branch
        )
        pull_request.status = PullRequest.STATUS_MERGED
        pull_request.reviewed_by = request.user
        pull_request.merged_snapshot = pull_request.source_snapshot
        pull_request.merged_at = timezone.now()
        pull_request.merge_commit_sha = merge_sha
        pull_request.save()
        repository = getattr(project, 'repository', None)
        if repository is not None:
            repository.current_branch = pull_request.target_branch
            repository.last_commit_sha = merge_sha or repository.last_commit_sha
            repository.save(
                update_fields=['current_branch', 'last_commit_sha', 'updated_at']
            )
        if pull_request.revision_request_id:
            revision = pull_request.revision_request
            revision.status = RevisionRequest.STATUS_ADDRESSED
            revision.resolved_by = request.user
            revision.resolved_at = timezone.now()
            revision.save(update_fields=['status', 'resolved_by', 'resolved_at', 'updated_at'])
        services.notify(
            project.student,
            kind=Notification.KIND_PULL_REQUEST,
            title=f'Pull request merged: {pull_request.title}',
            body='Your changes were merged by the instructor.',
            url=f'/projects/pull-requests/{pull_request.pk}/',
            project=project,
        )
        log_activity(
            request,
            action='project.pull_request.merged',
            entity=pull_request,
            description=f'Pull request merged for {project}',
            metadata={
                'course_id': project.assignment.course_id,
                'project_id': project.pk,
            },
        )
    elif action == 'close':
        pull_request.status = PullRequest.STATUS_CLOSED
        pull_request.reviewed_by = request.user
        pull_request.save(update_fields=['status', 'reviewed_by', 'updated_at'])
        services.notify(
            project.student,
            kind=Notification.KIND_PULL_REQUEST,
            title=f'Pull request closed: {pull_request.title}',
            body=str(data.get('reason') or 'The instructor closed this pull request.'),
            url=f'/projects/pull-requests/{pull_request.pk}/',
            project=project,
        )
    else:
        return _error('Unknown pull-request action.')
    return _json({'ok': True, 'pull_request': _pull_request_payload(pull_request)})


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@api_auth(('read',))
@require_http_methods(['GET'])
def notification_list(request):
    queryset = request.user.classforge_notifications.select_related(
        'project', 'snapshot'
    )[:100]
    return _json(
        {
            'ok': True,
            'unread': services.unread_notification_count(request.user),
            'notifications': [
                {
                    'id': item.id,
                    'kind': item.kind,
                    'title': item.title,
                    'body': item.body,
                    'url': item.url,
                    'project_id': item.project_id,
                    'snapshot_id': item.snapshot_id,
                    'read_at': _iso(item.read_at),
                    'created_at': _iso(item.created_at),
                }
                for item in queryset
            ],
        }
    )


@api_auth(('write',))
@require_http_methods(['POST'])
def notification_read(request, pk):
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
    except Notification.DoesNotExist:
        return _error('Notification not found.', 404)
    notification.mark_read()
    return _json({'ok': True})


@require_http_methods(['GET'])
def health(request):
    return _json(
        {
            'ok': True,
            'version': '1',
            'time': _iso(timezone.now()),
            'test_runner': getattr(settings, 'CLASSFORGE_TEST_RUNNER', 'disabled'),
            'ai_configured': bool(getattr(settings, 'AI_API_KEY', '')),
            'git_enabled': services.git_enabled(),
        }
    )
