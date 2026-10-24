"""Single source of truth for ClassForge role checks.

The legacy project used ``is_superuser`` / ``is_staff`` to represent
administrators and instructors.  Those flags remain a supported fallback so
existing databases and tests keep working.
"""

from .models import UserProfile


def get_user_role(user):
    """Return ``admin``, ``instructor``, ``ta``, ``student`` or ``None``."""
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return UserProfile.ROLE_ADMIN

    try:
        profile = user.classforge_profile
    except UserProfile.DoesNotExist:
        profile = None

    if profile and profile.role:
        # Never let a non-superuser elevate themselves in the database.
        if profile.role == UserProfile.ROLE_ADMIN:
            return (
                UserProfile.ROLE_INSTRUCTOR
                if user.is_staff
                else UserProfile.ROLE_STUDENT
            )
        return profile.role

    if user.is_staff:
        return UserProfile.ROLE_INSTRUCTOR
    return UserProfile.ROLE_STUDENT


def is_admin(user):
    return bool(user and user.is_authenticated and user.is_superuser)


def is_instructor(user):
    return get_user_role(user) in (
        UserProfile.ROLE_ADMIN,
        UserProfile.ROLE_INSTRUCTOR,
    )


def is_teaching_assistant(user):
    return get_user_role(user) == UserProfile.ROLE_TA


def is_student(user):
    return get_user_role(user) == UserProfile.ROLE_STUDENT


def can_grade(user):
    return get_user_role(user) in (
        UserProfile.ROLE_ADMIN,
        UserProfile.ROLE_INSTRUCTOR,
        UserProfile.ROLE_TA,
    )


def can_manage_course(user, course):
    """Only the owning instructor (or an administrator) manages a course."""
    if not user or not user.is_authenticated or course is None:
        return False
    if user.is_superuser:
        return True
    return (
        is_instructor(user)
        and course.instructor_id == user.id
    )


def can_grade_course(user, course):
    """Instructors and assigned TAs may grade a course."""
    if can_manage_course(user, course):
        return True
    if not user or not user.is_authenticated or course is None:
        return False
    if is_teaching_assistant(user) or is_instructor(user):
        return course.assistants.filter(user=user).exists()
    return False


def course_role(user, course):
    if can_manage_course(user, course):
        return 'instructor'
    if can_grade_course(user, course):
        return 'ta'
    return 'student'


def role_label(user):
    labels = {
        UserProfile.ROLE_ADMIN: 'Administrator',
        UserProfile.ROLE_INSTRUCTOR: 'Instructor',
        UserProfile.ROLE_TA: 'Teaching Assistant',
        UserProfile.ROLE_STUDENT: 'Student',
    }
    return labels.get(get_user_role(user), 'Student')
