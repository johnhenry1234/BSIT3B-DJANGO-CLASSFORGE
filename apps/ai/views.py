"""Views for requesting and applying AI draft evaluations."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.core.audit import log_activity
from apps.courses.models import Assignment, Submission
from apps.users.roles import can_grade_course

from .models import AIEvaluation
from .services import apply_suggestions, request_evaluation


def _require_grader(user, course):
    if not can_grade_course(user, course):
        raise PermissionDenied('Only instructors and assigned TAs can evaluate this course.')


@login_required(login_url='login')
@require_POST
def run_evaluation_view(request, submission_pk):
    submission = get_object_or_404(
        Submission.objects.select_related('assignment__course'), pk=submission_pk
    )
    _require_grader(request.user, submission.assignment.course)
    evaluation = request_evaluation(submission, request.user)
    if evaluation.status == AIEvaluation.STATUS_COMPLETED:
        messages.success(
            request,
            f'AI draft ready: suggested {evaluation.suggested_score} / '
            f'{submission.assignment.max_score} with '
            f'{evaluation.flags.count()} finding(s). Review it before saving.',
        )
    elif evaluation.status == AIEvaluation.STATUS_FAILED:
        messages.error(request, f'AI draft failed: {evaluation.error}')
    else:
        messages.info(request, 'AI draft queued for background processing.')
    return redirect('courses:submission_grade', pk=submission.pk)


@login_required(login_url='login')
@require_POST
def run_assignment_view(request, assignment_pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related('course'), pk=assignment_pk
    )
    _require_grader(request.user, assignment.course)

    latest_ids = (
        Submission.objects.filter(assignment=assignment)
        .values('student_id')
        .annotate(latest_id=Max('id'))
        .values_list('latest_id', flat=True)
    )
    submissions = Submission.objects.filter(id__in=list(latest_ids))[:25]
    queued = 0
    for submission in submissions:
        has_completed = submission.ai_evaluations.filter(
            status=AIEvaluation.STATUS_COMPLETED
        ).exists()
        if not has_completed:
            request_evaluation(submission, request.user)
            queued += 1
    messages.success(
        request,
        f'Queued AI drafts for {queued} latest submission(s). Existing drafts were left untouched.',
    )
    return redirect('courses:assignment_detail', pk=assignment.pk)


@login_required(login_url='login')
@require_POST
def apply_evaluation_view(request, pk):
    evaluation = get_object_or_404(
        AIEvaluation.objects.select_related(
            'submission__assignment__course'
        ),
        pk=pk,
    )
    _require_grader(request.user, evaluation.submission.assignment.course)
    try:
        grade, created = apply_suggestions(evaluation, request.user)
    except ValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
    else:
        state = 'created' if created else 'updated'
        messages.success(
            request,
            f'AI draft applied to the {state} draft grade. '
            'The grade remains unpublished until you review and publish it.',
        )
        log_activity(
            request,
            actor=request.user,
            action='ai.evaluation.reviewed',
            entity=evaluation,
            description=f'Instructor opened AI-assisted grading for {evaluation.submission}',
            metadata={
                'course_id': evaluation.submission.assignment.course_id,
                'grade_id': grade.id,
            },
        )
    return redirect('courses:submission_grade', pk=evaluation.submission_id)
