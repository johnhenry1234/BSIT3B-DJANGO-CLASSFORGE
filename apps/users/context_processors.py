"""Expose the current user's ClassForge role to every template."""

from .roles import get_user_role, can_grade, is_teaching_assistant


def role_context(request):
    user = getattr(request, 'user', None)
    return {
        'user_role': get_user_role(user),
        'can_grade': can_grade(user),
        'is_ta': is_teaching_assistant(user),
    }
