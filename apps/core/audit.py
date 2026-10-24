"""Helpers for writing to the append-only activity audit trail."""

from .models import ActivityLog


def _client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip() or None
    return request.META.get('REMOTE_ADDR') or None


def log_activity(
    request=None,
    *,
    actor=None,
    action,
    entity=None,
    entity_type='',
    entity_id='',
    description='',
    metadata=None,
):
    """Record an auditable event.

    ``entity`` may be any model instance.  Failures are ignored so that an
    audit-table problem can never take down grading or submission flows.
    """
    if actor is None and request is not None:
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            actor = user

    if entity is not None:
        entity_type = entity_type or entity.__class__.__name__
        entity_id = entity_id or str(getattr(entity, 'pk', '') or '')

    try:
        return ActivityLog.objects.create(
            actor=actor if getattr(actor, 'pk', None) else None,
            action=(action or 'unknown')[:64],
            entity_type=(entity_type or '')[:64],
            entity_id=(entity_id or '')[:64],
            description=description or '',
            ip_address=_client_ip(request),
            user_agent=(request.META.get('HTTP_USER_AGENT', '') if request else '')[:2000],
            metadata=metadata or {},
        )
    except Exception:  # pragma: no cover - audit must never break the request
        return None
