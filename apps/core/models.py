"""Shared ClassForge models: the system activity audit trail."""

from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    """Append-only audit record for security-relevant events.

    Logging must never break a request, so callers should use
    :func:`apps.core.audit.log_activity`, which swallows write errors.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='activity_logs',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=64, db_index=True)
    entity_type = models.CharField(max_length=64, blank=True, default='')
    entity_id = models.CharField(max_length=64, blank=True, default='')
    description = models.TextField(blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'activity_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id'], name='idx_activity_entity'),
            models.Index(fields=['actor', '-created_at'], name='idx_activity_actor_time'),
        ]

    def __str__(self):
        return f'{self.action} by {self.actor or "system"} at {self.created_at:%Y-%m-%d %H:%M}'
