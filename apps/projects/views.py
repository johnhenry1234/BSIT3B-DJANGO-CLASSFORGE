"""Server-rendered project, assessment and review pages."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.audit import log_activity
from apps.courses.models import Assignment, Course, Grade
from apps.users.roles import (
    can_grade_course,
    can_manage_course,
    is_instructor,
    is_teaching_assistant,
)

from . import assessment as assessment_module
from . import services
from .forms import (
    AssessmentReviewForm,
    CommentForm,
    ProjectForm,
    PullRequestForm,
    RevisionRequestForm,
)
from .models import (
    Assessment,
    Notification,
    Project,
    ProjectSnapshot,
    PullRequest,
    PullRequestComment,
    RevisionRequest,
)

logger = logging.getLogger(__name__)


def _courses_for(user):
    if user.is_superuser:
        return Course.objects.all()
    return Course.objects.filter(
        Q(instructor=user) | Q(assistants__user=user)
    ).distinct()


def _visible_projects(user):
    queryset = Project.objects.select_related(
        'assignment__course', 'assignment__course__instructor', 'student'
    )
    if user.is_superuser:
        return queryset
    if is_instructor(user) or is_teaching_assistant(user):
        return (
            queryset.filter(assignment__course__in=_courses_for(user))
            | queryset.filter(student=user)
        ).distinct()
    return queryset.filter(student=user)


def _project_or_403(user, pk):
    project = get_object_or_404(
        _visible_projects(user), pk=pk
    )
    return project


def _require_grader(user, project):
    if not can_grade_course(user, project.assignment.course):
        raise PermissionDenied('Only the instructor or a TA can do that.')


@login_required(login_url='login')
def project_list(request):
    projects = _visible_projects(request.user).order_by('-updated_at')
    status = request.GET.get('status', '').strip()
    if status in dict(Project.STATUS_CHOICES):
        projects = projects.filter(status=status)
    assignment_id = request.GET.get('assignment', '').strip()
    if assignment_id.isdigit():
        projects = projects.filter(assignment_id=int(assignment_id))
    query = request.GET.get('q', '').strip()
    if query:
        projects = projects.filter(
            Q(title__icontains=query)
            | Q(assignment__title__icontains=query)
            | Q(student__username__icontains=query)
        )
    paginator = Paginator(projects, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(
        request,
        'projects/project_list.html',
        {
            'projects': page,
            'status': status,
            'status_choices': Project.STATUS_CHOICES,
            'query': query,
            'assignment_id': assignment_id,
        },
    )


@login_required(login_url='login')
def project_detail(request, pk):
    project = _project_or_403(request.user, pk)
    snapshots = list(project.snapshots.select_related('created_by').order_by('-version'))
    latest = snapshots[0] if snapshots else None
    assessments = (
        Assessment.objects.filter(snapshot__project=project)
        .select_related('snapshot', 'reviewer')
        .order_by('-created_at')[:10]
    )
    revisions = project.revision_requests.select_related(
        'requested_by', 'snapshot'
    ).order_by('-created_at')
    pull_requests = project.pull_requests.select_related(
        'created_by', 'source_snapshot'
    ).order_by('-created_at')
    grade = None
    if latest and latest.submission_id:
        try:
            grade = latest.submission.grade
        except Grade.DoesNotExist:
            grade = None
    return render(
        request,
        'projects/project_detail.html',
        {
            'project': project,
            'course': project.assignment.course,
            'assignment': project.assignment,
            'snapshots': snapshots,
            'latest_snapshot': latest,
            'assessments': assessments,
            'revisions': revisions,
            'pull_requests': pull_requests,
            'can_grade': can_grade_course(request.user, project.assignment.course),
            'can_manage': can_manage_course(request.user, project.assignment.course),
            'is_owner': project.student_id == request.user.id,
            'grade': grade,
            'repository': getattr(project, 'repository', None),
        },
    )


@login_required(login_url='login')
@require_POST
def project_create(request, assignment_pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related('course'), pk=assignment_pk
    )
    if not (
        can_grade_course(request.user, assignment.course)
        or assignment.course.enrollments.filter(student=request.user).exists()
    ):
        raise PermissionDenied('Enroll in the course before creating a project.')
    project = services.create_project(
        assignment,
        request.user,
        title=request.POST.get('title', ''),
        description=request.POST.get('description', ''),
    )
    messages.success(request, 'Project workspace is ready.')
    log_activity(
        request,
        action='project.created',
        entity=project,
        description=f'Created project for {assignment.title}',
        metadata={'course_id': assignment.course_id, 'assignment_id': assignment.id},
    )
    return redirect('projects:project_detail', pk=project.pk)


@login_required(login_url='login')
def snapshot_detail(request, pk):
    snapshot = get_object_or_404(
        ProjectSnapshot.objects.select_related(
            'project__assignment__course', 'project__student', 'created_by'
        ),
        pk=pk,
    )
    project = snapshot.project
    if not (
        project.student_id == request.user.id
        or can_grade_course(request.user, project.assignment.course)
    ):
        raise PermissionDenied('You do not have access to this snapshot.')

    previous = (
        ProjectSnapshot.objects.filter(
            project=project, version__lt=snapshot.version
        )
        .order_by('-version')
        .first()
    )
    assessments = snapshot.assessments.select_related('reviewer').order_by('-created_at')
    latest = assessments.first()
    manifest = snapshot.manifest or []
    grouped = {}
    for item in manifest:
        top = item['path'].split('/')[0] if '/' in item['path'] else '(root)'
        grouped.setdefault(top, []).append(item)
    return render(
        request,
        'projects/snapshot_detail.html',
        {
            'snapshot': snapshot,
            'project': project,
            'previous': previous,
            'assessments': assessments,
            'assessment': latest,
            'manifest': manifest,
            'grouped': grouped,
            'can_grade': can_grade_course(request.user, project.assignment.course),
            'is_owner': project.student_id == request.user.id,
        },
    )


@login_required(login_url='login')
@require_POST
def snapshot_assess(request, pk):
    snapshot = get_object_or_404(
        ProjectSnapshot.objects.select_related(
            'project__assignment__course', 'project__student'
        ),
        pk=pk,
    )
    project = snapshot.project
    if not (
        project.student_id == request.user.id
        or can_grade_course(request.user, project.assignment.course)
    ):
        raise PermissionDenied('You do not have access to this snapshot.')
    try:
        assessment = assessment_module.request_assessment(snapshot, request.user)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    except Exception:
        logger.exception('Could not queue assessment for snapshot %s', snapshot.pk)
        messages.error(request, 'The assessment could not be queued. Please try again.')
    else:
        if assessment.status == Assessment.STATUS_COMPLETED:
            messages.success(request, 'Assessment completed and ready for review.')
        else:
            messages.info(request, 'Assessment queued.')
        log_activity(
            request,
            action='assessment.requested',
            entity=assessment,
            description=f'Assessment requested from the web UI for {snapshot}',
            metadata={
                'course_id': project.assignment.course_id,
                'project_id': project.pk,
                'snapshot_id': snapshot.pk,
            },
        )
    return redirect('projects:snapshot_detail', pk=snapshot.pk)


@login_required(login_url='login')
def snapshot_compare(request, pk):
    target = get_object_or_404(
        ProjectSnapshot.objects.select_related('project__assignment__course'),
        pk=pk,
    )
    project = target.project
    if not (
        project.student_id == request.user.id
        or can_grade_course(request.user, project.assignment.course)
    ):
        raise PermissionDenied('You do not have access to this snapshot.')
    base_id = request.GET.get('base')
    if base_id:
        base = get_object_or_404(ProjectSnapshot, pk=base_id, project=project)
    else:
        base = (
            ProjectSnapshot.objects.filter(
                project=project, version__lt=target.version
            )
            .order_by('-version')
            .first()
        )
    diff = services.diff_snapshots(base, target) if base else None
    return render(
        request,
        'projects/snapshot_compare.html',
        {
            'project': project,
            'base': base,
            'target': target,
            'diff': diff,
            'snapshots': project.snapshots.order_by('-version')[:50],
        },
    )


@login_required(login_url='login')
def assessment_queue(request):
    if is_instructor(request.user) or is_teaching_assistant(request.user) or request.user.is_superuser:
        assessments = (
            Assessment.objects.filter(
                snapshot__project__assignment__course__in=_courses_for(request.user)
            )
            .select_related(
                'snapshot__project__assignment',
                'snapshot__project__student',
                'reviewer',
            )
            .order_by('-created_at')
        )
        queue_filter = request.GET.get('filter', 'pending').strip()
        if queue_filter == 'pending':
            assessments = assessments.filter(
                status=Assessment.STATUS_COMPLETED,
                requires_review=True,
                review_status=Assessment.REVIEW_PENDING,
            )
        elif queue_filter == 'failed':
            assessments = assessments.filter(status=Assessment.STATUS_FAILED)
        elif queue_filter == 'reviewed':
            assessments = assessments.exclude(review_status=Assessment.REVIEW_PENDING)
        else:
            queue_filter = 'all'
        paginator = Paginator(assessments, 25)
        page = paginator.get_page(request.GET.get('page', 1))
        return render(
            request,
            'projects/assessment_queue.html',
            {
                'assessments': page,
                'queue_filter': queue_filter,
                'is_grader': True,
            },
        )

    assessments = (
        Assessment.objects.filter(snapshot__project__student=request.user)
        .select_related('snapshot__project__assignment')
        .order_by('-created_at')
    )
    paginator = Paginator(assessments, 25)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(
        request,
        'projects/assessment_queue.html',
        {'assessments': page, 'queue_filter': 'all', 'is_grader': False},
    )


@login_required(login_url='login')
def assessment_review(request, pk):
    assessment = get_object_or_404(
        Assessment.objects.select_related(
            'snapshot__project__assignment__course',
            'snapshot__project__student',
            'reviewer',
            'applied_grade',
        ),
        pk=pk,
    )
    project = assessment.snapshot.project
    _require_grader(request.user, project)

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'retry':
            try:
                assessment_module.retry_assessment(assessment, request.user)
            except ValidationError as exc:
                messages.error(request, exc.messages[0])
            else:
                messages.success(request, 'Assessment re-queued for processing.')
            return redirect('projects:assessment_review', pk=assessment.pk)
        if action == 'apply':
            try:
                grade, created = services.apply_assessment(assessment, request.user)
            except ValidationError as exc:
                messages.error(request, exc.messages[0])
            else:
                messages.success(
                    request,
                    f'Assessment applied as an unpublished grade '
                    f'({grade.score}/{assessment.max_score}). '
                    'Publish it from the grading page when ready.',
                )
                log_activity(
                    request,
                    action='assessment.applied',
                    entity=assessment,
                    description=f'Assessment applied to a draft grade for {project.student}',
                    metadata={
                        'course_id': project.assignment.course_id,
                        'assessment_id': assessment.pk,
                        'grade_id': grade.pk,
                    },
                )
            return redirect('projects:assessment_review', pk=assessment.pk)

        form = AssessmentReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            score = form.cleaned_data.get('instructor_score')
            criteria_values = {}
            for item in assessment.criteria.all():
                key = f'criterion_{item.pk}'
                if key in request.POST:
                    criteria_values[str(item.pk)] = request.POST.get(key)
            try:
                services.review_assessment(
                    assessment,
                    request.user,
                    action,
                    instructor_score=score,
                    instructor_feedback=form.cleaned_data.get(
                        'instructor_feedback', ''
                    ),
                    criterion_scores=criteria_values,
                )
            except (ValidationError, InvalidOperation) as exc:
                messages.error(request, getattr(exc, 'messages', [str(exc)])[0])
            else:
                messages.success(request, 'Assessment review saved.')
                if action in ('approve', 'override'):
                    try:
                        grade, _ = services.apply_assessment(assessment, request.user)
                    except ValidationError as exc:
                        messages.warning(
                            request,
                            f'Review saved, but the grade was not applied: {exc.messages[0]}',
                        )
                    else:
                        messages.info(
                            request,
                            f'Draft grade created ({grade.score}/{assessment.max_score}); '
                            'it is not published until you publish it.',
                        )
                log_activity(
                    request,
                    action=f'assessment.reviewed.{action}',
                    entity=assessment,
                    description=f'Assessment {action} by {request.user.username}',
                    metadata={
                        'course_id': project.assignment.course_id,
                        'assessment_id': assessment.pk,
                        'score': str(assessment.instructor_score or assessment.overall_score),
                    },
                )
            return redirect('projects:assessment_review', pk=assessment.pk)
    else:
        form = AssessmentReviewForm(
            initial={
                'action': 'approve',
                'instructor_score': assessment.instructor_score,
                'instructor_feedback': assessment.instructor_feedback,
            }
        )
    return render(
        request,
        'projects/assessment_review.html',
        {
            'assessment': assessment,
            'project': project,
            'form': form,
            'criteria': assessment.criteria.all(),
            'can_publish_grade': assessment.applied_grade_id is not None,
        },
    )


@login_required(login_url='login')
@require_POST
def assessment_retry(request, pk):
    assessment = get_object_or_404(
        Assessment.objects.select_related('snapshot__project__assignment__course'), pk=pk
    )
    _require_grader(request.user, assessment.snapshot.project)
    try:
        assessment_module.retry_assessment(assessment, request.user)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    else:
        messages.success(request, 'Assessment re-queued.')
    return redirect('projects:assessment_review', pk=assessment.pk)


@login_required(login_url='login')
def revision_create(request, project_pk):
    project = _project_or_403(request.user, project_pk)
    _require_grader(request.user, project)
    if request.method == 'POST':
        form = RevisionRequestForm(request.POST, project=project)
        if form.is_valid():
            revision = form.save(commit=False)
            revision.project = project
            revision.requested_by = request.user
            if not revision.branch_name:
                revision.branch_name = f'revision/{project.pk}-{RevisionRequest.objects.filter(project=project).count() + 1}'
            revision.save()
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
                metadata={'course_id': project.assignment.course_id},
            )
            messages.success(request, 'Revision request sent to the student.')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        initial = {
            'snapshot': project.latest_snapshot,
            'branch_name': f'revision/{project.pk}-{project.revision_requests.count() + 1}',
        }
        form = RevisionRequestForm(project=project, initial=initial)
    return render(
        request,
        'projects/revision_form.html',
        {'project': project, 'form': form},
    )


@login_required(login_url='login')
@require_POST
def revision_update(request, pk):
    revision = get_object_or_404(
        RevisionRequest.objects.select_related(
            'project__assignment__course', 'project__student'
        ),
        pk=pk,
    )
    _require_grader(request.user, revision.project)
    status = request.POST.get('status', '')
    if status not in dict(RevisionRequest.STATUS_CHOICES):
        messages.error(request, 'Invalid revision status.')
    else:
        revision.status = status
        if status in (RevisionRequest.STATUS_ADDRESSED, RevisionRequest.STATUS_CLOSED):
            revision.resolved_by = request.user
            revision.resolved_at = timezone.now()
        revision.save()
        messages.success(request, 'Revision request updated.')
        log_activity(
            request,
            action=f'project.revision.{status}',
            entity=revision,
            description=f'Revision {status} for {revision.project}',
            metadata={'course_id': revision.project.assignment.course_id},
        )
    return redirect('projects:project_detail', pk=revision.project_id)


@login_required(login_url='login')
def pull_request_create(request, project_pk):
    project = _project_or_403(request.user, project_pk)
    if not (
        project.student_id == request.user.id
        or can_grade_course(request.user, project.assignment.course)
    ):
        raise PermissionDenied('Only the project owner or a grader can open a pull request.')
    if request.method == 'POST':
        form = PullRequestForm(request.POST, project=project)
        if form.is_valid():
            pull_request = form.save(commit=False)
            pull_request.project = project
            pull_request.created_by = request.user
            pull_request.save()
            services.notify_course_staff(
                project.assignment,
                kind=Notification.KIND_PULL_REQUEST,
                title=f'Pull request #{pull_request.pk}: {pull_request.title}',
                body=f'{project.student} requested a review.',
                url=f'/projects/pull-requests/{pull_request.pk}/',
                project=project,
                snapshot=pull_request.source_snapshot,
            )
            log_activity(
                request,
                action='project.pull_request.created',
                entity=pull_request,
                description=f'Pull request created for {project}',
                metadata={'course_id': project.assignment.course_id},
            )
            messages.success(request, 'Pull request created.')
            return redirect('projects:pull_request_detail', pk=pull_request.pk)
    else:
        latest = project.latest_snapshot
        initial = {
            'source_snapshot': latest,
            'source_branch': latest.branch if latest else 'main',
            'target_branch': 'main',
        }
        form = PullRequestForm(project=project, initial=initial)
    return render(
        request,
        'projects/pull_request_form.html',
        {'project': project, 'form': form},
    )


@login_required(login_url='login')
def pull_request_detail(request, pk):
    pull_request = get_object_or_404(
        PullRequest.objects.select_related(
            'project__assignment__course',
            'project__student',
            'source_snapshot',
            'created_by',
            'reviewed_by',
        ).prefetch_related('comments__author'),
        pk=pk,
    )
    project = pull_request.project
    is_grader = can_grade_course(request.user, project.assignment.course)
    if not (is_grader or project.student_id == request.user.id):
        raise PermissionDenied('You do not have access to this pull request.')
    comment_form = CommentForm()
    if request.method == 'POST':
        action = request.POST.get('action', 'comment')
        if action == 'comment':
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                PullRequestComment.objects.create(
                    pull_request=pull_request,
                    author=request.user,
                    body=comment_form.cleaned_data['body'],
                )
                messages.success(request, 'Comment added.')
                return redirect('projects:pull_request_detail', pk=pull_request.pk)
        elif not is_grader:
            raise PermissionDenied('Only a grader can review a pull request.')
        elif action == 'merge':
            if pull_request.status != PullRequest.STATUS_OPEN:
                messages.error(request, 'This pull request is not open.')
            else:
                merge_sha = services.git_merge(
                    project,
                    pull_request.source_branch,
                    pull_request.target_branch,
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
                    revision.save(
                        update_fields=['status', 'resolved_by', 'resolved_at', 'updated_at']
                    )
                services.notify(
                    project.student,
                    kind=Notification.KIND_PULL_REQUEST,
                    title=f'Pull request merged: {pull_request.title}',
                    body='Your changes were merged by the instructor.',
                    url=f'/projects/pull-requests/{pull_request.pk}/',
                    project=project,
                )
                messages.success(request, 'Pull request merged.')
            return redirect('projects:pull_request_detail', pk=pull_request.pk)
        elif action == 'close':
            pull_request.status = PullRequest.STATUS_CLOSED
            pull_request.reviewed_by = request.user
            pull_request.save(update_fields=['status', 'reviewed_by', 'updated_at'])
            messages.info(request, 'Pull request closed.')
            return redirect('projects:pull_request_detail', pk=pull_request.pk)
    return render(
        request,
        'projects/pull_request_detail.html',
        {
            'pull_request': pull_request,
            'project': project,
            'comment_form': comment_form,
            'is_grader': is_grader,
            'is_owner': project.student_id == request.user.id,
        },
    )


@login_required(login_url='login')
def notification_list(request):
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        if notification_id:
            Notification.objects.filter(
                pk=notification_id, user=request.user
            ).update(read_at=timezone.now())
        else:
            Notification.objects.filter(
                user=request.user, read_at__isnull=True
            ).update(read_at=timezone.now())
            messages.success(request, 'All notifications marked as read.')
        return redirect('projects:notification_list')
    notifications = Notification.objects.filter(user=request.user).select_related(
        'project', 'snapshot'
    )
    paginator = Paginator(notifications, 30)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(
        request,
        'projects/notifications.html',
        {'notifications': page},
    )


@login_required(login_url='login')
def token_manage(request):
    from .models import ApiToken

    raw_token = None
    if request.method == 'POST':
        action = request.POST.get('action', 'create')
        if action == 'revoke':
            token = get_object_or_404(
                ApiToken, pk=request.POST.get('token_id'), user=request.user
            )
            token.revoked_at = timezone.now()
            token.save(update_fields=['revoked_at'])
            messages.success(request, 'Token revoked.')
            log_activity(
                request,
                action='api.token.revoked',
                entity=token,
                description='API token revoked from the web UI',
            )
            return redirect('projects:token_manage')
        token, raw_token = ApiToken.issue(
            request.user,
            name=request.POST.get('name') or 'VS Code extension',
        )
        log_activity(
            request,
            action='api.token.created',
            entity=token,
            description='API token created from the web UI',
        )
        messages.warning(
            request,
            'Copy the token now — it is shown once and stored only as a hash.',
        )
    tokens = ApiToken.objects.filter(user=request.user).order_by('-created_at')[:50]
    return render(
        request,
        'projects/tokens.html',
        {'tokens': tokens, 'raw_token': raw_token},
    )
