"""ClassForge views: courses, enrollments, assignments, submissions, grades."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Max, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AssignmentForm, CourseForm, GradeForm, SubmissionForm
from .models import Assignment, Course, Enrollment, Grade, Submission


def _is_instructor(user):
    return user.is_staff or user.is_superuser


def _can_manage_course(user, course):
    return user.is_superuser or (
        user.is_staff and course.instructor_id == user.id
    )


def _require_manage_course(user, course):
    if not _can_manage_course(user, course):
        raise PermissionDenied('Only the course instructor can do that.')


def _require_instructor(user):
    if not _is_instructor(user):
        raise PermissionDenied('Only instructors can do that.')


@login_required(login_url='login')
def course_list(request):
    query = request.GET.get('q', '').strip()
    if request.user.is_superuser:
        courses = Course.objects.all()
    elif _is_instructor(request.user):
        courses = Course.objects.filter(instructor=request.user)
    else:
        courses = Course.objects.all()

    if query:
        courses = courses.filter(
            Q(name__icontains=query)
            | Q(code__icontains=query)
            | Q(description__icontains=query)
        )
    courses = courses.select_related('instructor').order_by('code')

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
    can_manage = _can_manage_course(request.user, course)

    my_submissions = {}
    my_grades = {}
    if not _is_instructor(request.user):
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

    # For instructors: latest submission per (assignment, student).
    latest_by_student = {}
    pending_by_assignment = {}
    pending_count = 0
    if can_manage:
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
    if _is_instructor(request.user):
        messages.error(request, 'Instructors cannot enroll as students.')
        return redirect('courses:course_detail', pk=pk)
    _, created = Enrollment.objects.get_or_create(
        course=course, student=request.user
    )
    if created:
        messages.success(request, f'Enrolled in {course.code} successfully.')
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
    can_manage = _can_manage_course(request.user, course)

    if _is_instructor(request.user) and not can_manage:
        raise PermissionDenied('You do not teach this course.')

    context = {
        'assignment': assignment,
        'course': course,
        'can_manage': can_manage,
        'now': timezone.now(),
    }

    if can_manage:
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
    if _is_instructor(request.user):
        messages.error(request, 'Instructors cannot submit assignments.')
        return redirect('courses:assignment_detail', pk=pk)
    if not course.enrollments.filter(student=request.user).exists():
        messages.error(request, 'Enroll in the course before submitting.')
        return redirect('courses:course_detail', pk=course.pk)

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
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
                return redirect('courses:assignment_detail', pk=pk)
    else:
        form = SubmissionForm()
    return render(
        request,
        'courses/submit.html',
        {'form': form, 'assignment': assignment, 'course': course},
    )


@login_required(login_url='login')
def submission_grade(request, pk):
    submission = get_object_or_404(
        Submission.objects.select_related('assignment__course'), pk=pk
    )
    _require_manage_course(request.user, submission.assignment.course)
    try:
        existing = submission.grade
    except Grade.DoesNotExist:
        existing = None

    if request.method == 'POST':
        # Bind submission/instructor before validation so Grade.clean() can
        # check score against the assignment's max_score on the first pass.
        stub = existing or Grade(submission=submission, instructor=request.user)
        form = GradeForm(request.POST, instance=stub)
        if form.is_valid():
            grade = form.save(commit=False)
            grade.submission = submission
            grade.instructor = request.user
            try:
                grade.save()
            except IntegrityError:
                messages.error(request, 'Could not save grade. Try again.')
            else:
                messages.success(
                    request,
                    f'Graded v{submission.version} '
                    f'({grade.score}/{submission.assignment.max_score}).',
                )
                return redirect(
                    'courses:assignment_detail',
                    pk=submission.assignment_id,
                )
    else:
        form = GradeForm(instance=existing)
    return render(
        request,
        'courses/grade_form.html',
        {'form': form, 'submission': submission, 'existing': existing},
    )


@login_required(login_url='login')
@require_POST
def grade_publish_toggle(request, pk):
    grade = get_object_or_404(
        Grade.objects.select_related('submission__assignment__course'), pk=pk
    )
    _require_manage_course(request.user, grade.submission.assignment.course)
    grade.is_published = not grade.is_published
    grade.save(update_fields=['is_published', 'graded_at'])
    state = 'published' if grade.is_published else 'unpublished'
    messages.success(request, f'Grade {state} successfully.')
    return redirect(
        'courses:assignment_detail', pk=grade.submission.assignment_id
    )


@login_required(login_url='login')
def my_grades(request):
    if _is_instructor(request.user):
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
