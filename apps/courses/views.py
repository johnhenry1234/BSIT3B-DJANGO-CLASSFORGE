"""ClassForge views: courses, enrollments, assignments, submissions, grades."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Max, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.ai.models import AIEvaluation
from apps.core.audit import log_activity
from apps.core.models import ActivityLog
from apps.users.models import UserProfile
from apps.users.roles import (
    can_grade,
    can_grade_course,
    can_manage_course,
    get_user_role,
    is_admin,
    is_instructor,
    is_student,
    is_teaching_assistant,
)

from .forms import (
    AnnotationForm,
    AssignmentForm,
    CourseForm,
    GradeForm,
    RubricCriterionForm,
    RubricForm,
    RubricGradeForm,
    SubmissionForm,
)
from .models import (
    Assignment,
    Course,
    CourseAssistant,
    CriterionScore,
    Enrollment,
    Grade,
    Rubric,
    RubricCriterion,
    Submission,
)


def _is_instructor(user):
    return is_instructor(user)


def _can_manage_course(user, course):
    return can_manage_course(user, course)


def _require_manage_course(user, course):
    if not can_manage_course(user, course):
        raise PermissionDenied('Only the course instructor can do that.')


def _require_grader(user, course):
    if not can_grade_course(user, course):
        raise PermissionDenied(
            'Only instructors, teaching assistants, or administrators can grade this course.'
        )


def _require_instructor(user):
    if not is_instructor(user):
        raise PermissionDenied('Only instructors can do that.')


@login_required(login_url='login')
def course_list(request):
    query = request.GET.get('q', '').strip()
    if request.user.is_superuser:
        courses = Course.objects.all()
    elif is_instructor(request.user):
        courses = Course.objects.filter(instructor=request.user)
    elif is_teaching_assistant(request.user):
        courses = Course.objects.filter(assistants__user=request.user)
    else:
        courses = Course.objects.all()

    if query:
        courses = courses.filter(
            Q(name__icontains=query)
            | Q(code__icontains=query)
            | Q(description__icontains=query)
        )
    courses = courses.select_related('instructor').distinct().order_by('code')

    enrolled_ids = set(
        Enrollment.objects.filter(student=request.user).values_list(
            'course_id', flat=True
        )
    )

    paginator = Paginator(courses, 10)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(
        request,
        'courses/list.html',
        {'courses': page, 'query': query, 'enrolled_ids': enrolled_ids},
    )


@login_required(login_url='login')
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    category_filter = request.GET.get('category', '').strip()
    assignments = course.assignments.all().order_by('due_date')
    if category_filter in dict(Assignment.CATEGORY_CHOICES):
        assignments = assignments.filter(category=category_filter)
    else:
        category_filter = ''
    enrollments = course.enrollments.select_related('student')
    is_enrolled = course.enrollments.filter(student=request.user).exists()
    can_manage = can_manage_course(request.user, course)
    can_grade_this = can_grade_course(request.user, course)

    my_submissions = {}
    my_grades = {}
    if not can_grade_this:
        subs = (
            Submission.objects.filter(
                assignment__course=course, student=request.user
            )
            .select_related('grade')
            .order_by('assignment_id', '-version')
        )
        for sub in subs:
            my_submissions.setdefault(sub.assignment_id, []).append(sub)
            if hasattr(sub, 'grade') and sub.grade.is_published:
                my_grades.setdefault(sub.assignment_id, sub.grade)

    # For instructors and TAs: latest submission per (assignment, student).
    latest_by_student = {}
    pending_by_assignment = {}
    pending_count = 0
    if can_grade_this:
        for assignment in assignments:
            latest_ids = (
                Submission.objects.filter(assignment=assignment)
                .values('student_id')
                .annotate(latest_id=Max('id'))
                .values_list('latest_id', flat=True)
            )
            latest = (
                Submission.objects.filter(id__in=list(latest_ids))
                .select_related('student', 'assignment')
                .prefetch_related('grade')
                .order_by('-submitted_at')
            )
            latest = list(latest)
            latest_by_student[assignment.id] = latest
            pending = sum(1 for s in latest if not hasattr(s, 'grade'))
            pending_by_assignment[assignment.id] = pending
            pending_count += pending

    return render(
        request,
        'courses/detail.html',
        {
            'course': course,
            'assignments': assignments,
            'enrollments': enrollments,
            'is_enrolled': is_enrolled,
            'can_manage': can_manage,
            'can_grade': can_grade_this,
            'my_submissions': my_submissions,
            'my_grades': my_grades,
            'latest_by_student': latest_by_student,
            'pending_by_assignment': pending_by_assignment,
            'pending_count': pending_count,
            'category_filter': category_filter,
            'category_choices': Assignment.CATEGORY_CHOICES,
            'now': timezone.now(),
        },
    )


@login_required(login_url='login')
def course_create(request):
    _require_instructor(request.user)
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            try:
                course.save()
            except IntegrityError:
                form.add_error('code', 'That course code is already taken.')
            else:
                messages.success(
                    request, f'Course "{course.code}" created successfully.'
                )
                log_activity(
                    request,
                    action='course.created',
                    entity=course,
                    description=f'Created course {course.code}',
                )
                return redirect('courses:course_detail', pk=course.pk)
    else:
        form = CourseForm()
    return render(
        request, 'courses/course_form.html', {'form': form, 'mode': 'create'}
    )


@login_required(login_url='login')
def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)
    _require_manage_course(request.user, course)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully.')
            return redirect('courses:course_detail', pk=course.pk)
    else:
        form = CourseForm(instance=course)
    return render(
        request,
        'courses/course_form.html',
        {'form': form, 'mode': 'edit', 'course': course},
    )


@login_required(login_url='login')
@require_POST
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    _require_manage_course(request.user, course)
    code = course.code
    course.delete()
    messages.success(request, f'Course "{code}" deleted successfully.')
    return redirect('courses:course_list')


@login_required(login_url='login')
@require_POST
def course_enroll(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if is_instructor(request.user) or is_teaching_assistant(request.user):
        messages.error(request, 'Instructors and TAs cannot enroll as students.')
        return redirect('courses:course_detail', pk=pk)
    _, created = Enrollment.objects.get_or_create(
        course=course, student=request.user
    )
    if created:
        messages.success(request, f'Enrolled in {course.code} successfully.')
        log_activity(
            request,
            action='course.enrolled',
            entity=course,
            description=f'Enrolled in {course.code}',
            metadata={'course_id': course.id},
        )
    else:
        messages.info(request, f'You are already enrolled in {course.code}.')
    return redirect('courses:course_detail', pk=pk)


@login_required(login_url='login')
@require_POST
def course_unenroll(request, pk):
    course = get_object_or_404(Course, pk=pk)
    Enrollment.objects.filter(course=course, student=request.user).delete()
    messages.success(request, f'Unenrolled from {course.code}.')
    return redirect('courses:course_detail', pk=pk)


@login_required(login_url='login')
def assignment_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    _require_manage_course(request.user, course)
    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.course = course
            assignment.save()
            messages.success(request, 'Assignment created successfully.')
            log_activity(
                request,
                action='assignment.created',
                entity=assignment,
                description=f'Created assignment "{assignment.title}" in {course.code}',
                metadata={'course_id': course.id},
            )
            return redirect('courses:assignment_detail', pk=assignment.pk)
    else:
        form = AssignmentForm()
    return render(
        request,
        'courses/assignment_form.html',
        {'form': form, 'mode': 'create', 'course': course},
    )


@login_required(login_url='login')
def assignment_detail(request, pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related('course'), pk=pk
    )
    course = assignment.course
    can_manage = can_manage_course(request.user, course)
    can_grade_this = can_grade_course(request.user, course)

    if is_instructor(request.user) and not can_grade_this:
        raise PermissionDenied('You do not teach this course.')

    context = {
        'assignment': assignment,
        'course': course,
        'can_manage': can_manage,
        'can_grade': can_grade_this,
        'rubric': getattr(assignment, 'rubric', None),
        'now': timezone.now(),
    }

    if can_grade_this:
        # All versions grouped by student, newest first; prefetch grades.
        submissions = (
            Submission.objects.filter(assignment=assignment)
            .select_related('student')
            .prefetch_related('grade')
            .order_by('student__username', '-version')
        )
        by_student = {}
        for sub in submissions:
            by_student.setdefault(sub.student, []).append(sub)
        context['by_student'] = by_student
    else:
        is_enrolled = course.enrollments.filter(student=request.user).exists()
        versions = (
            Submission.objects.filter(
                assignment=assignment, student=request.user
            )
            .prefetch_related('grade')
            .order_by('-version')
        )
        context['is_enrolled'] = is_enrolled
        context['versions'] = versions
        context['latest_grade'] = next(
            (
                v.grade
                for v in versions
                if hasattr(v, 'grade') and v.grade.is_published
            ),
            None,
        )

    return render(request, 'courses/assignment_detail.html', context)


@login_required(login_url='login')
def assignment_update(request, pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related('course'), pk=pk
    )
    _require_manage_course(request.user, assignment.course)
    if request.method == 'POST':
        form = AssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Assignment updated successfully.')
            return redirect('courses:assignment_detail', pk=assignment.pk)
    else:
        form = AssignmentForm(instance=assignment)
    return render(
        request,
        'courses/assignment_form.html',
        {
            'form': form,
            'mode': 'edit',
            'course': assignment.course,
            'assignment': assignment,
        },
    )


@login_required(login_url='login')
@require_POST
def assignment_delete(request, pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related('course'), pk=pk
    )
    _require_manage_course(request.user, assignment.course)
    course_pk = assignment.course_id
    title = assignment.title
    assignment.delete()
    messages.success(request, f'Assignment "{title}" deleted successfully.')
    return redirect('courses:course_detail', pk=course_pk)


@login_required(login_url='login')
def submission_create(request, pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related('course'), pk=pk
    )
    course = assignment.course
    if can_grade_course(request.user, course) or is_instructor(request.user):
        messages.error(request, 'Instructors and TAs cannot submit assignments.')
        return redirect('courses:assignment_detail', pk=pk)
    if not course.enrollments.filter(student=request.user).exists():
        messages.error(request, 'Enroll in the course before submitting.')
        return redirect('courses:course_detail', pk=course.pk)

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES, assignment=assignment)
        if form.is_valid():
            try:
                with transaction.atomic():
                    submission = form.save(commit=False)
                    submission.assignment = assignment
                    submission.student = request.user
                    # version is auto-assigned (max + 1) in model save().
                    submission.save()
            except IntegrityError:
                messages.error(
                    request, 'Could not save submission. Please try again.'
                )
            else:
                messages.success(
                    request,
                    f'Submission v{submission.version} uploaded successfully.'
                    + (
                        ' Note: it was submitted after the due date.'
                        if submission.is_late
                        else ''
                    ),
                )
                log_activity(
                    request,
                    action='submission.created',
                    entity=submission,
                    description=f'Uploaded v{submission.version} for "{assignment.title}"',
                    metadata={'course_id': course.id},
                )
                return redirect('courses:assignment_detail', pk=pk)
    else:
        form = SubmissionForm(assignment=assignment)
    return render(
        request,
        'courses/submit.html',
        {'form': form, 'assignment': assignment, 'course': course},
    )


@login_required(login_url='login')
@require_POST
def grade_publish_toggle(request, pk):
    grade = get_object_or_404(
        Grade.objects.select_related('submission__assignment__course'), pk=pk
    )
    _require_grader(request.user, grade.submission.assignment.course)
    grade.is_published = not grade.is_published
    grade.published_at = timezone.now() if grade.is_published else None
    grade.published_by = request.user if grade.is_published else None
    grade.save(
        update_fields=[
            'is_published',
            'published_at',
            'published_by',
            'graded_at',
        ]
    )
    state = 'published' if grade.is_published else 'unpublished'
    messages.success(request, f'Grade {state} successfully.')
    log_activity(
        request,
        action=f'grade.{state}',
        entity=grade,
        description=f'Grade {state} for {grade.submission}',
        metadata={'course_id': grade.submission.assignment.course_id},
    )
    return redirect(
        'courses:assignment_detail', pk=grade.submission.assignment_id
    )


@login_required(login_url='login')
def my_grades(request):
    if is_instructor(request.user) or is_teaching_assistant(request.user):
        return redirect('courses:course_list')
    latest_version = (
        Submission.objects.filter(
            assignment=OuterRef('submission__assignment'), student=request.user
        )
        .order_by('-version')
        .values('version')[:1]
    )
    grades = (
        Grade.objects.filter(
            submission__student=request.user,
            is_published=True,
            submission__version=Subquery(latest_version),
        )
        .select_related('submission__assignment__course')
        .order_by('-graded_at')
    )
    # Show only the latest-version grade per assignment.
    seen = set()
    published = []
    for grade in grades:
        aid = grade.submission.assignment_id
        if aid not in seen:
            seen.add(aid)
            published.append(grade)
    return render(request, 'courses/my_grades.html', {'grades': published})


@login_required(login_url='login')
def student_history(request):
    if is_instructor(request.user) or is_teaching_assistant(request.user):
        return redirect('courses:course_list')

    from django.core.paginator import Paginator
    from apps.core.models import ActivityLog

    enrolled_courses = Course.objects.filter(enrollments__student=request.user).distinct()
    course_ids = list(enrolled_courses.values_list('id', flat=True))
    instructor_ids = list(enrolled_courses.values_list('instructor_id', flat=True))

    logs = (
        ActivityLog.objects.select_related('actor')
        .filter(
            Q(actor=request.user)
            | (
                Q(actor_id__in=instructor_ids)
                & (
                    Q(metadata__course_id__in=course_ids)
                    | Q(entity_type='Course', entity_id__in=[str(c) for c in course_ids])
                    | Q(entity_type__in=['Assignment', 'Submission', 'Grade'], entity_id__isnull=False)
                )
            )
        )
        .order_by('-created_at')
    )
    # Further constrain to only events related to the student's courses where possible
    if course_ids:
        logs = logs.filter(
            Q(actor=request.user)
            | Q(metadata__course_id__in=course_ids)
            | Q(entity_type='Course', entity_id__in=[str(c) for c in course_ids])
        ).order_by('-created_at')

    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'courses/student_history.html',
        {
            'page_obj': page_obj,
            'logs': page_obj.object_list,
        },
    )


@login_required(login_url='login')
def grading_queue(request):
    if not can_grade(request.user):
        raise PermissionDenied('Only instructors and TAs can access the grading queue.')

    courses = []
    if request.user.is_superuser:
        courses = Course.objects.all()
    else:
        courses = Course.objects.filter(
            Q(instructor=request.user) | Q(assistants__user=request.user)
        ).distinct()

    queue = []
    for course in courses:
        latest_ids = (
            Submission.objects.filter(assignment__course=course)
            .values('assignment_id', 'student_id')
            .annotate(latest_id=Max('id'))
            .values_list('latest_id', flat=True)
        )
        latest = (
            Submission.objects.filter(id__in=list(latest_ids))
            .select_related('assignment', 'student', 'assignment__course')
            .prefetch_related('grade', 'ai_evaluations')
        )
        for submission in latest:
            if hasattr(submission, 'grade'):
                continue
            ai = submission.ai_evaluations.filter(
                status=AIEvaluation.STATUS_COMPLETED
            ).order_by('-created_at').first()
            queue.append(
                {
                    'submission': submission,
                    'course': course,
                    'ai': ai,
                    'is_late': submission.is_late,
                }
            )
    return render(request, 'courses/grading_queue.html', {'queue': queue})


@login_required(login_url='login')
def manage_assistants(request, pk):
    course = get_object_or_404(Course, pk=pk)
    _require_manage_course(request.user, course)

    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, f'User "{username}" not found.')
            return redirect('courses:manage_assistants', pk=course.pk)

        if user.is_superuser or user == course.instructor:
            messages.error(request, 'That user cannot be assigned as a TA.')
            return redirect('courses:manage_assistants', pk=course.pk)

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if profile.role != UserProfile.ROLE_TA and not user.is_staff:
            profile.role = UserProfile.ROLE_TA
            profile.save(update_fields=['role', 'updated_at'])

        try:
            CourseAssistant.objects.create(
                course=course, user=user, added_by=request.user
            )
            messages.success(request, f'{user.username} assigned as a Teaching Assistant.')
            log_activity(
                request,
                action='course.ta_assigned',
                entity=course,
                description=f'{user.username} assigned as TA to {course.code}',
                metadata={'ta_id': user.id},
            )
        except IntegrityError:
            messages.info(request, f'{user.username} is already assigned as a TA.')

        return redirect('courses:manage_assistants', pk=course.pk)

    assistants = course.assistants.select_related('user')
    return render(
        request,
        'courses/manage_assistants.html',
        {'course': course, 'assistants': assistants},
    )


@login_required(login_url='login')
@require_POST
def course_remove_assistant(request, pk):
    assistant = get_object_or_404(CourseAssistant, pk=pk)
    course = assistant.course
    _require_manage_course(request.user, course)
    username = assistant.user.username
    assistant.delete()
    messages.success(request, f'{username} removed as a Teaching Assistant.')
    log_activity(
        request,
        action='course.ta_removed',
        entity=course,
        description=f'{username} removed as TA from {course.code}',
        metadata={'ta_id': assistant.user_id},
    )
    return redirect('courses:manage_assistants', pk=course.pk)


@login_required(login_url='login')
def assignment_rubric(request, pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related('course'), pk=pk
    )
    _require_manage_course(request.user, assignment.course)
    rubric, _ = Rubric.objects.get_or_create(
        assignment=assignment,
        defaults={'title': f'{assignment.title} Rubric'},
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_rubric':
            form = RubricForm(request.POST, instance=rubric)
            if form.is_valid():
                form.save()
                messages.success(request, 'Rubric details saved.')
            else:
                messages.error(request, 'Please fix the errors in the rubric form.')
        elif action == 'add_criterion':
            form = RubricCriterionForm(request.POST)
            if form.is_valid():
                criterion = form.save(commit=False)
                criterion.rubric = rubric
                criterion.save()
                messages.success(request, 'Rubric criterion added.')
                log_activity(
                    request,
                    action='rubric.criterion_added',
                    entity=rubric,
                    description=f'Added "{criterion.name}" to rubric for {assignment.title}',
                    metadata={'course_id': assignment.course_id},
                )
            else:
                messages.error(request, 'Please fix the errors in the criterion form.')
        elif action == 'delete_criterion':
            criterion = get_object_or_404(
                RubricCriterion, pk=request.POST.get('criterion_id'), rubric=rubric
            )
            name = criterion.name
            criterion.delete()
            messages.success(request, f'"{name}" removed from the rubric.')
            log_activity(
                request,
                action='rubric.criterion_deleted',
                entity=rubric,
                description=f'Removed "{name}" from rubric for {assignment.title}',
                metadata={'course_id': assignment.course_id},
            )
        return redirect('courses:assignment_rubric', pk=assignment.pk)

    rubric_form = RubricForm(instance=rubric)
    criterion_form = RubricCriterionForm()
    return render(
        request,
        'courses/assignment_rubric.html',
        {
            'assignment': assignment,
            'course': assignment.course,
            'rubric': rubric,
            'rubric_form': rubric_form,
            'criterion_form': criterion_form,
        },
    )


@login_required(login_url='login')
@require_POST
def grade_publish(request, pk):
    grade = get_object_or_404(
        Grade.objects.select_related('submission__assignment__course'), pk=pk
    )
    _require_grader(request.user, grade.submission.assignment.course)
    if not grade.is_published:
        grade.is_published = True
        grade.published_at = timezone.now()
        grade.published_by = request.user
        grade.save(update_fields=['is_published', 'published_at', 'published_by', 'graded_at'])
        messages.success(request, 'Grade published successfully.')
        log_activity(
            request,
            action='grade.published',
            entity=grade,
            description=f'Published grade for {grade.submission}',
            metadata={'course_id': grade.submission.assignment.course_id},
        )
    else:
        messages.info(request, 'Grade is already published.')
    return redirect('courses:assignment_detail', pk=grade.submission.assignment_id)


@login_required(login_url='login')
@require_POST
def grade_unpublish(request, pk):
    grade = get_object_or_404(
        Grade.objects.select_related('submission__assignment__course'), pk=pk
    )
    _require_grader(request.user, grade.submission.assignment.course)
    if grade.is_published:
        grade.is_published = False
        grade.published_at = None
        grade.published_by = None
        grade.save(update_fields=['is_published', 'published_at', 'published_by', 'graded_at'])
        messages.success(request, 'Grade unpublished successfully.')
        log_activity(
            request,
            action='grade.unpublished',
            entity=grade,
            description=f'Unpublished grade for {grade.submission}',
            metadata={'course_id': grade.submission.assignment.course_id},
        )
    else:
        messages.info(request, 'Grade is already a draft.')
    return redirect('courses:assignment_detail', pk=grade.submission.assignment_id)


@login_required(login_url='login')
@require_POST
def grade_publish_batch(request):
    ids = request.POST.getlist('grade_ids')
    if not ids:
        messages.error(request, 'No grades were selected.')
        return redirect('courses:grading_queue')

    grades = Grade.objects.filter(
        id__in=ids, is_published=False
    ).select_related('submission__assignment__course')
    published = 0
    for grade in grades:
        if not can_grade_course(request.user, grade.submission.assignment.course):
            continue
        grade.is_published = True
        grade.published_at = timezone.now()
        grade.published_by = request.user
        grade.save(update_fields=['is_published', 'published_at', 'published_by', 'graded_at'])
        log_activity(
            request,
            action='grade.published',
            entity=grade,
            description=f'Batch-published grade for {grade.submission}',
            metadata={'course_id': grade.submission.assignment.course_id},
        )
        published += 1

    if published:
        messages.success(request, f'Published {published} grade(s) in batch.')
    else:
        messages.info(request, 'No eligible draft grades were published.')
    return redirect('courses:grading_queue')


@login_required(login_url='login')
def submission_grade(request, pk):
    submission = get_object_or_404(
        Submission.objects.select_related('assignment__course', 'student'), pk=pk
    )
    _require_grader(request.user, submission.assignment.course)
    try:
        existing = submission.grade
    except Grade.DoesNotExist:
        existing = None

    rubric = getattr(submission.assignment, 'rubric', None)
    ai_evaluations = submission.ai_evaluations.select_related(
        'requested_by', 'applied_by'
    ).prefetch_related('flags').all()[:10]
    annotations = []
    if existing:
        annotations = existing.annotations.select_related('author').all()

    if request.method == 'POST':
        if rubric and rubric.criteria.exists():
            form = RubricGradeForm(
                request.POST, rubric=rubric, grade=existing
            )
        else:
            stub = existing or Grade(submission=submission, instructor=request.user)
            form = GradeForm(request.POST, instance=stub)

        if form.is_valid():
            try:
                with transaction.atomic():
                    if rubric and rubric.criteria.exists():
                        if existing:
                            grade = existing
                            grade.instructor = request.user
                        else:
                            grade = Grade(
                                submission=submission,
                                instructor=request.user,
                                is_published=False,
                            )
                        total = Decimal('0')
                        for criterion, points, comment in form.criteria_values():
                            total += points
                            CriterionScore.objects.update_or_create(
                                grade=grade,
                                criterion=criterion,
                                defaults={'points_awarded': points, 'comment': comment},
                            )
                        grade.score = min(total, submission.assignment.max_score)
                        grade.feedback = (form.cleaned_data.get('feedback') or '').strip()
                        if form.cleaned_data.get('is_published'):
                            grade.is_published = True
                            grade.published_at = timezone.now()
                            grade.published_by = request.user
                        elif existing and existing.is_published and not form.cleaned_data.get('is_published'):
                            # preserve existing published state unless explicitly toggled below
                            pass
                        grade.save()
                    else:
                        grade = form.save(commit=False)
                        grade.submission = submission
                        grade.instructor = request.user
                        grade.save()

                    if form.cleaned_data.get('is_published') and not grade.is_published:
                        grade.is_published = True
                        grade.published_at = timezone.now()
                        grade.published_by = request.user
                        grade.save(update_fields=['is_published', 'published_at', 'published_by', 'graded_at'])
                    elif 'is_published' in form.cleaned_data and not form.cleaned_data.get('is_published') and grade.is_published and existing:
                        # allow unpublish via toggle is separate; keep simple
                        pass

            except IntegrityError:
                messages.error(request, 'Could not save grade. Try again.')
            else:
                messages.success(
                    request,
                    f'Graded v{submission.version} '
                    f'({grade.score}/{submission.assignment.max_score}). '
                    f'{"Published" if grade.is_published else "Saved as draft"}.',
                )
                log_activity(
                    request,
                    action='grade.saved',
                    entity=grade,
                    description=f'Graded submission {submission} by rubric' if rubric and rubric.criteria.exists() else f'Graded submission {submission}',
                    metadata={
                        'course_id': submission.assignment.course_id,
                        'assignment_id': submission.assignment_id,
                        'submission_id': submission.id,
                        'published': grade.is_published,
                    },
                )
                return redirect(
                    'courses:assignment_detail',
                    pk=submission.assignment_id,
                )
    else:
        if rubric and rubric.criteria.exists():
            form = RubricGradeForm(rubric=rubric, grade=existing)
            if existing:
                form.fields['feedback'].initial = existing.feedback
                form.fields['is_published'].initial = existing.is_published
        else:
            form = GradeForm(instance=existing)

    annotation_form = AnnotationForm()
    return render(
        request,
        'courses/grade_form.html',
        {
            'form': form,
            'submission': submission,
            'existing': existing,
            'rubric': rubric,
            'ai_evaluations': ai_evaluations,
            'annotations': annotations,
            'annotation_form': annotation_form,
        },
    )


@login_required(login_url='login')
@require_POST
def add_annotation(request, pk):
    grade = get_object_or_404(
        Grade.objects.select_related('submission__assignment__course'), pk=pk
    )
    _require_grader(request.user, grade.submission.assignment.course)
    form = AnnotationForm(request.POST, request.FILES)
    if form.is_valid():
        annotation = form.save(commit=False)
        annotation.grade = grade
        annotation.author = request.user
        annotation.save()
        messages.success(request, 'Feedback annotation added.')
        log_activity(
            request,
            action='feedback.annotation_added',
            entity=grade,
            description=f'Added annotation to grade for {grade.submission}',
            metadata={'course_id': grade.submission.assignment.course_id},
        )
    else:
        messages.error(request, 'Could not add annotation. Check the form.')
    return redirect('courses:submission_grade', pk=grade.submission_id)


@login_required(login_url='login')
@require_POST
def mark_assignment_seen(request, pk):
    from .models import Assignment, AssignmentSeen, Enrollment
    from django.http import JsonResponse

    assignment = get_object_or_404(Assignment, pk=pk)
    if not Enrollment.objects.filter(course=assignment.course, student=request.user).exists():
        return JsonResponse({'ok': False}, status=403)
    AssignmentSeen.objects.get_or_create(student=request.user, assignment=assignment)
    return JsonResponse({'ok': True})


@login_required(login_url='login')
@require_POST
def dashboard_submit(request, pk):
    from .models import Assignment, AssignmentSeen, Enrollment
    from .forms import SubmissionForm

    assignment = get_object_or_404(Assignment.objects.select_related('course'), pk=pk)
    course = assignment.course
    if can_grade_course(request.user, course) or is_instructor(request.user):
        messages.error(request, 'Instructors and TAs cannot submit assignments.')
        return redirect('dashboard')
    if not course.enrollments.filter(student=request.user).exists():
        messages.error(request, 'Enroll in the course before submitting.')
        return redirect('courses:course_detail', pk=course.pk)

    form = SubmissionForm(request.POST, request.FILES, assignment=assignment)
    if form.is_valid():
        try:
            with transaction.atomic():
                submission = form.save(commit=False)
                submission.assignment = assignment
                submission.student = request.user
                submission.save()
        except IntegrityError:
            messages.error(request, 'Could not save submission. Please try again.')
        else:
            messages.success(
                request,
                f'Submission v{submission.version} uploaded successfully.'
                + (' Note: it was submitted after the due date.' if submission.is_late else ''),
            )
            log_activity(
                request,
                action='submission.created',
                entity=submission,
                description=f'Uploaded v{submission.version} for "{assignment.title}"',
                metadata={'course_id': course.id},
            )
            AssignmentSeen.objects.get_or_create(student=request.user, assignment=assignment)
    else:
        messages.error(request, 'Could not submit. Please check the file/link/text.')
    return redirect('dashboard')


@login_required(login_url='login')
def audit_log(request):
    if request.user.is_superuser:
        logs = ActivityLog.objects.select_related('actor').all()
    else:
        # Instructors see their own courses, TAs see the courses they assist,
        # and everybody can always see the actions they performed themselves.
        courses = Course.objects.filter(
            Q(instructor=request.user) | Q(assistants__user=request.user)
        ).distinct()
        course_ids = list(courses.values_list('id', flat=True))
        # Instructors and TAs always see their own actions, even before they
        # own/assist a course.  Students have no access to the audit trail.
        if not course_ids and not can_grade(request.user):
            raise PermissionDenied(
                'You do not have access to an audit trail.'
            )
        logs = ActivityLog.objects.select_related('actor').filter(
            Q(actor=request.user)
            | Q(metadata__course_id__in=course_ids)
            | Q(entity_type='Course', entity_id__in=[str(c) for c in course_ids])
        )

    action_filter = request.GET.get('action', '').strip()
    if action_filter:
        logs = logs.filter(action__icontains=action_filter)

    paginator = Paginator(logs, 30)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(
        request, 'courses/audit_log.html', {'logs': page, 'action_filter': action_filter}
    )
