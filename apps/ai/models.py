"""Independent AI evaluation records linked to submission versions."""

from django.conf import settings
from django.db import models


class AIEvaluation(models.Model):
    STATUS_QUEUED = 'queued'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    MODE_DRAFT = 'draft'
    MODE_CHOICES = [(MODE_DRAFT, 'Draft Assistant')]

    submission = models.ForeignKey(
        'courses.Submission',
        related_name='ai_evaluations',
        on_delete=models.CASCADE,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='ai_evaluations_requested',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True
    )
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default=MODE_DRAFT)
    model_name = models.CharField(max_length=120, blank=True, default='')

    suggested_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    suggested_feedback = models.TextField(blank=True, default='')
    summary = models.TextField(blank=True, default='')
    suggested_criteria = models.JSONField(default=list, blank=True)
    guideline_snapshot = models.TextField(blank=True, default='')
    inspection = models.JSONField(default=dict, blank=True)
    raw_response = models.TextField(blank=True, default='')
    error = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='ai_evaluations_applied',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ai_evaluations'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['submission', '-created_at'],
                name='idx_ai_eval_submission_time',
            ),
        ]

    def __str__(self):
        return f'AI {self.status} for {self.submission}'

    @property
    def is_completed(self):
        return self.status == self.STATUS_COMPLETED

    @property
    def is_applied(self):
        return self.applied_at is not None

    @property
    def flag_count(self):
        return len(self.flags.all())


class AIFlag(models.Model):
    KIND_MISSING_REQUIREMENT = 'missing_requirement'
    KIND_STRUCTURAL = 'structural_discrepancy'
    KIND_CODE_ANOMALY = 'code_anomaly'
    KIND_CHOICES = [
        (KIND_MISSING_REQUIREMENT, 'Missing requirement'),
        (KIND_STRUCTURAL, 'Structural discrepancy'),
        (KIND_CODE_ANOMALY, 'Code anomaly'),
    ]

    SEVERITY_INFO = 'info'
    SEVERITY_WARNING = 'warning'
    SEVERITY_CRITICAL = 'critical'
    SEVERITY_CHOICES = [
        (SEVERITY_INFO, 'Info'),
        (SEVERITY_WARNING, 'Warning'),
        (SEVERITY_CRITICAL, 'Critical'),
    ]

    evaluation = models.ForeignKey(
        AIEvaluation, related_name='flags', on_delete=models.CASCADE
    )
    kind = models.CharField(max_length=32, choices=KIND_CHOICES)
    severity = models.CharField(
        max_length=16, choices=SEVERITY_CHOICES, default=SEVERITY_INFO
    )
    message = models.TextField()
    evidence = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_flags'
        ordering = ['severity', 'id']

    def __str__(self):
        return f'[{self.severity}] {self.message}'
