from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Q

from apps.scoping import scoped_info, scoped_infos
from apps.courses.models import Course, Enrollment, Submission
from apps.users.roles import role_label
from django.contrib.auth import get_user_model

from .models import Info

User = get_user_model()

MIN_AGE = 1
MAX_AGE = 150


def _grader_courses(user):
    """Courses whose students the given instructor/TA may inspect."""
    if user.is_superuser:
        return Course.objects.all().order_by('code')
    return (
        Course.objects.filter(Q(instructor=user) | Q(assistants__user=user))
        .distinct()
        .order_by('code')
    )


def _parse_age(raw_age):
    """Convert an age value to an integer, returning None when it is invalid."""
    try:
        return int(raw_age)
    except (TypeError, ValueError):
        return None


@login_required(login_url='login')
def info_list_page(request):
    """Show students enrolled in courses taught by the signed-in instructor."""
    user = request.user
    query = request.GET.get('q', '').strip()

    # For instructors/staff/superusers, show enrolled students from their courses
    if user.is_superuser or user.is_staff or getattr(user, 'classforge_profile', None):
        from apps.users.roles import is_instructor, can_grade

        if user.is_superuser or is_instructor(user) or can_grade(user):
            courses = Course.objects.filter(
                Q(instructor=user) | Q(assistants__user=user)
            ).distinct().order_by('code')
            course_filter = request.GET.get('course', '').strip()
            if course_filter:
                try:
                    course_filter_id = int(course_filter)
                    if course_filter_id in list(courses.values_list('id', flat=True)):
                        courses_qs = courses.filter(id=course_filter_id)
                    else:
                        courses_qs = courses
                except ValueError:
                    courses_qs = courses
            else:
                courses_qs = courses

            enrollments = (
                Enrollment.objects.filter(course__in=courses_qs)
                .select_related('course', 'student', 'student__classforge_profile')
                .prefetch_related('student__infos')
                .order_by('course__code', 'student__first_name', 'student__last_name', 'student__username')
            )

            if query:
                enrollments = enrollments.filter(
                    Q(student__username__icontains=query)
                    | Q(student__first_name__icontains=query)
                    | Q(student__last_name__icontains=query)
                    | Q(student__email__icontains=query)
                    | Q(student__infos__name__icontains=query)
                    | Q(student__infos__id_number__icontains=query)
                ).distinct()

            paginator = Paginator(enrollments, 30)
            page_number = request.GET.get('page', 1)
            enrollments_page = paginator.get_page(page_number)

            return render(
                request,
                'info.html',
                {
                    'enrollments': enrollments_page,
                    'courses': courses,
                    'course_filter': course_filter,
                    'query': query,
                    'is_student_view': False,
                },
            )

    # Fallback for students - show their own info (legacy behavior)
    infos_list = scoped_infos(request.user).order_by('name')

    if query:
        infos_list = infos_list.filter(
            Q(name__icontains=query)
            | Q(address__icontains=query)
            | Q(email__icontains=query)
        )

    paginator = Paginator(infos_list, 10)
    page_number = request.GET.get('page', 1)
    infos = paginator.get_page(page_number)

    return render(
        request,
        'info.html',
        {
            'infos': infos,
            'query': query,
            'is_student_view': True,
        },
    )


@login_required(login_url='login')
def student_detail(request, pk):
    """Show a student's profile to an instructor or TA who teaches them."""
    student = get_object_or_404(User, pk=pk)
    courses = _grader_courses(request.user)
    enrollments = (
        Enrollment.objects.filter(student=student, course__in=courses)
        .select_related('course')
        .order_by('course__code')
    )
    if not enrollments.exists():
        raise PermissionDenied(
            'You can only view students enrolled in your courses.'
        )

    # Imported lazily so the info app does not depend on project models at
    # application-load time.
    from apps.projects.models import Project

    submissions = (
        Submission.objects.filter(
            student=student, assignment__course__in=courses
        )
        .select_related('assignment', 'assignment__course')
        .prefetch_related('grade')
        .order_by('-submitted_at')
    )
    projects = (
        Project.objects.filter(student=student, assignment__course__in=courses)
        .select_related('assignment', 'assignment__course')
        .order_by('-updated_at')
    )

    return render(
        request,
        'info_student.html',
        {
            'student': student,
            'student_role': role_label(student),
            'infos': student.infos.all(),
            'enrollments': enrollments,
            'submissions': submissions,
            'projects': projects,
        },
    )


@login_required(login_url='login')
def info_list_ajax(request):
    """Return the signed-in user's filtered info records as paginated JSON."""
    query = request.GET.get('q', '').strip()

    infos_list = scoped_infos(request.user).order_by('name')

    if query:
        infos_list = infos_list.filter(
            Q(name__icontains=query) |
            Q(address__icontains=query) |
            Q(email__icontains=query)
        )

    paginator = Paginator(infos_list, 10)
    page_number = request.GET.get('page', 1)
    infos = paginator.get_page(page_number)
    data = list(infos.object_list.values(
        'id', 'name', 'id_number', 'age', 'address', 'email'
    ))
    return JsonResponse({
        'data': data,
        'has_next': infos.has_next(),
        'has_prev': infos.has_previous(),
        'page': infos.number,
        'pages': infos.paginator.num_pages,
        'total': infos.paginator.count,
    })


@login_required(login_url='login')
def info_get_ajax(request, pk):
    """Return one of the signed-in user's info records as JSON."""
    info = scoped_info(request.user, pk)
    return JsonResponse({
        'id': info.id,
        'name': info.name,
        'id_number': info.id_number,
        'age': info.age,
        'address': info.address,
        'email': info.email,
    })


@login_required(login_url='login')
@require_POST
def info_save_ajax(request):
    """Validate and create or update an info record, returning its data as JSON."""
    info_id = request.POST.get('id')

    if info_id:
        info = scoped_info(request.user, info_id)
        is_update = True
    else:
        info = Info()
        is_update = False

    name = request.POST.get('name', '').strip()
    id_number = request.POST.get('id_number', '').strip()
    age = request.POST.get('age', '').strip()
    address = request.POST.get('address', '').strip()
    email = request.POST.get('email', '').strip()

    if not name:
        return JsonResponse({'error': 'Name is required.'}, status=400)

    if not id_number:
        return JsonResponse({'error': 'ID number is required.'}, status=400)

    dup = Info.objects.filter(id_number=id_number)
    if info.pk:
        dup = dup.exclude(pk=info.pk)
    if dup.exists():
        return JsonResponse({'error': 'ID number already registered.'}, status=400)

    if not age:
        return JsonResponse({'error': 'Age is required.'}, status=400)

    age_value = _parse_age(age)

    if age_value is None or age_value < MIN_AGE or age_value > MAX_AGE:
        return JsonResponse(
            {'error': f'Age must be a number between {MIN_AGE} and {MAX_AGE}.'},
            status=400
        )

    if not address:
        return JsonResponse({'error': 'Address is required.'}, status=400)

    if email:
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'error': 'Enter a valid email address.'}, status=400)

    info.name = name
    info.id_number = id_number
    info.age = age_value
    info.address = address
    info.email = email

    if not info.pk:
        info.user = request.user

    try:
        info.save()
    except IntegrityError:
        return JsonResponse(
            {'error': 'Could not save record due to a conflict.'},
            status=400
        )

    messages.success(
        request,
        f'Record "{info.name}" has been {"updated" if is_update else "saved"} successfully.'
    )

    return JsonResponse({
        'status': 'success',
        'id': info.id,
        'name': info.name,
        'id_number': info.id_number,
        'age': info.age,
        'address': info.address,
        'email': info.email,
    })


@login_required(login_url='login')
@require_POST
def info_delete_ajax(request, pk):
    """Delete the specified signed-in user's info record and confirm as JSON."""
    info = scoped_info(request.user, pk)
    info_name = info.name
    info.delete()
    messages.success(request, f'Record "{info_name}" has been deleted successfully.')
    return JsonResponse({'status': 'deleted'})
