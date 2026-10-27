from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.info.models import Info

from .audit import log_activity

User = get_user_model()

INVALID_LOGIN_MESSAGE = 'Invalid username or password.'
ROLE_STUDENT = 'student'
ROLE_INSTRUCTOR = 'instructor'
ROLE_CHOICES = (ROLE_STUDENT, ROLE_INSTRUCTOR)
MIN_AGE = 1
MAX_AGE = 150


def _validate_registration_data(data):
    errors = {}

    username = data.get('username', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    role = data.get('role', ROLE_STUDENT).strip().lower()
    age = data.get('age', '').strip()
    address = data.get('address', '').strip()
    id_number = data.get('id_number', '').strip()

    if not username:
        errors['username'] = 'Username is required.'
    elif User.objects.filter(username=username).exists():
        errors['username'] = 'Username already taken.'

    if not first_name:
        errors['first_name'] = 'First name is required.'

    if not last_name:
        errors['last_name'] = 'Last name is required.'

    if not email:
        errors['email'] = 'Email is required.'
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = 'Enter a valid email address.'
        else:
            if User.objects.filter(email=email).exists():
                errors['email'] = 'Email already registered.'

    if not password:
        errors['password'] = 'Password is required.'
    elif len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters.'
    else:
        try:
            validate_password(password)
        except ValidationError as exc:
            errors['password'] = ' '.join(exc.messages)

    if password != confirm_password:
        errors['confirm_password'] = 'Passwords do not match.'

    if role not in ROLE_CHOICES:
        errors['role'] = 'Choose a valid role: student or instructor.'

    if not id_number:
        errors['id_number'] = 'ID number is required.'
    elif Info.objects.filter(id_number=id_number).exists():
        errors['id_number'] = 'ID number already registered.'

    if not age:
        errors['age'] = 'Age is required.'
    else:
        try:
            age_value = int(age)
        except (TypeError, ValueError):
            errors['age'] = f'Age must be a number between {MIN_AGE} and {MAX_AGE}.'
        else:
            if age_value < MIN_AGE or age_value > MAX_AGE:
                errors['age'] = f'Age must be a number between {MIN_AGE} and {MAX_AGE}.'

    if not address:
        errors['address'] = 'Address is required.'

    return errors


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'GET':
        return render(request, 'auth/login.html')

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        log_activity(
            request,
            actor=user,
            action='auth.login',
            entity=user,
            description=f'{user.username} signed in',
        )
        return redirect('dashboard')

    log_activity(
        request,
        action='auth.login_failed',
        entity_type='User',
        entity_id='',
        description=f'Failed sign-in for username "{username}"',
    )
    messages.error(request, INVALID_LOGIN_MESSAGE)
    return render(request, 'auth/login.html')


def logout_view(request):
    if request.user.is_authenticated:
        log_activity(
            request,
            actor=request.user,
            action='auth.logout',
            entity=request.user,
            description=f'{request.user.username} signed out',
        )
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def home(request):
    from apps.courses.models import (
        Assignment,
        AssignmentSeen,
        Course,
        Enrollment,
        Grade,
        Submission,
    )
    from apps.users.roles import is_instructor as user_is_instructor
    from django.db.models import Max, Q

    user = request.user
    stats = {}
    if user.is_superuser:
        stats = {
            'courses': Course.objects.count(),
            'assignments': Assignment.objects.count(),
            'submissions': Submission.objects.count(),
            'pending_grades': Submission.objects.filter(grade__isnull=True).count(),
        }
        role = 'admin'
    elif user.is_staff or user_is_instructor(user):
        own_courses = Course.objects.filter(
            Q(instructor=user) | Q(assistants__user=user)
        ).distinct()
        latest_ids = (
            Submission.objects.filter(assignment__course__in=own_courses)
            .values('assignment_id', 'student_id')
            .annotate(latest_id=Max('id'))
            .values_list('latest_id', flat=True)
        )
        pending_grades = (
            Submission.objects.filter(id__in=latest_ids)
            .exclude(grade__isnull=False)
            .count()
        )
        stats = {
            'courses': own_courses.count(),
            'assignments': Assignment.objects.filter(course__in=own_courses).count(),
            'students': Enrollment.objects.filter(course__in=own_courses)
            .values('student')
            .distinct()
            .count(),
            'pending_grades': pending_grades,
        }
        role = 'instructor'
        # Recent submissions for instructor dashboard
        recent_submissions = (
            Submission.objects.filter(id__in=latest_ids)
            .select_related('assignment', 'student', 'assignment__course')
            .order_by('-submitted_at')[:10]
        )
        # Class-level stats
        total_students = (
            Enrollment.objects.filter(course__in=own_courses)
            .values('student')
            .distinct()
            .count()
        )
        submitted_count = (
            Submission.objects.filter(id__in=latest_ids).values('student').distinct().count()
        )
        stats['submission_rate'] = round((submitted_count / total_students * 100) if total_students else 0, 1)
        stats['ungraded_count'] = pending_grades
        now = __import__('django.utils.timezone').utils.timezone.now()
        stats['upcoming_deadlines'] = Assignment.objects.filter(
            course__in=own_courses, due_date__gte=now
        ).count()
        return render(
            request,
            'home.html',
            {
                'stats': stats,
                'role': role,
                'recent_submissions': recent_submissions,
                'own_courses': own_courses,
                'upcoming_assignments': Assignment.objects.filter(
                    course__in=own_courses, due_date__gte=now
                )
                .select_related('course')
                .order_by('due_date')[:5],
            },
        )
    else:
        enrolled = Enrollment.objects.filter(student=user).values_list(
            'course_id', flat=True
        )
        submitted_assignment_ids = Submission.objects.filter(
            student=user
        ).values_list('assignment_id', flat=True)
        stats = {
            'courses': len(enrolled),
            'pending_submissions': Assignment.objects.filter(
                course_id__in=enrolled
            )
            .exclude(id__in=submitted_assignment_ids)
            .count(),
            'submissions': Submission.objects.filter(student=user).count(),
            'published_grades': Grade.objects.filter(
                submission__student=user, is_published=True
            ).count(),
        }
        role = 'student'
        # Feed of instructor posts
        assignments = (
            Assignment.objects.filter(course_id__in=enrolled)
            .select_related('course', 'course__instructor')
            .order_by('-created_at')
        )
        seen_ids = set(
            AssignmentSeen.objects.filter(student=user).values_list('assignment_id', flat=True)
        )
        posts = []
        for a in assignments:
            latest_sub = (
                Submission.objects.filter(assignment=a, student=user)
                .order_by('-version')
                .first()
            )
            if latest_sub and hasattr(latest_sub, 'grade'):
                status = 'Graded'
            elif latest_sub:
                status = 'Submitted'
            else:
                status = 'Not submitted'
            posts.append(
                {
                    'assignment': a,
                    'course': a.course,
                    'instructor': a.course.instructor,
                    'is_new': a.id not in seen_ids,
                    'status': status,
                    'latest_submission': latest_sub,
                }
            )
        unseen_count = sum(1 for p in posts if p['is_new'])
        return render(
            request,
            'home.html',
            {
                'stats': stats,
                'role': role,
                'posts': posts,
                'unseen_count': unseen_count,
            },
        )
    return render(request, 'home.html', {'stats': stats, 'role': role})


@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'GET':
        return render(request, 'auth/register.html')

    form_data = {
        'username': request.POST.get('username', ''),
        'first_name': request.POST.get('first_name', ''),
        'last_name': request.POST.get('last_name', ''),
        'email': request.POST.get('email', ''),
        'password': request.POST.get('password', ''),
        'confirm_password': request.POST.get('confirm_password', ''),
        'role': request.POST.get('role', ROLE_STUDENT),
        'id_number': request.POST.get('id_number', ''),
        'age': request.POST.get('age', ''),
        'address': request.POST.get('address', ''),
    }

    errors = _validate_registration_data(form_data)
    if errors:
        return render(request, 'auth/register.html', {'errors': errors, 'form_data': form_data})

    role = form_data['role'].strip().lower()
    with transaction.atomic():
        user = User.objects.create_user(
            username=form_data['username'].strip(),
            first_name=form_data['first_name'].strip(),
            last_name=form_data['last_name'].strip(),
            email=form_data['email'].strip(),
            password=form_data['password'],
        )
        if role == ROLE_INSTRUCTOR:
            user.is_staff = True
            user.save(update_fields=['is_staff'])
        Info.objects.create(
            user=user,
            name=f"{form_data['first_name'].strip()} {form_data['last_name'].strip()}".strip(),
            id_number=form_data['id_number'].strip(),
            age=int(form_data['age'].strip()),
            address=form_data['address'].strip(),
            email=form_data['email'].strip(),
        )
    login(request, user)
    log_activity(
        request,
        actor=user,
        action='auth.registered',
        entity=user,
        description=f'New {role} account "{user.username}" registered',
    )
    return redirect('dashboard')
