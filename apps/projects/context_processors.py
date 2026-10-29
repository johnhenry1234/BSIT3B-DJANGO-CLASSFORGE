"""Sidebar counters and small project helpers for every template."""

from .services import unread_notification_count


def project_context(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {'unread_notifications': 0}
    return {
        'unread_notifications': unread_notification_count(user),
    }
