"""Project workspace, snapshot, revision and assessment models.

The app deliberately keeps ``courses`` (assignment/submission/grade) as the
source of truth for grading.  A :class:`Project` is the durable workspace for
one student on one assignment; a :class:`ProjectSnapshot` is an immutable
archive plus manifest, optionally mirrored into a server-owned Git repository.

AI output is stored in :class:`Assessment` / :class:`CriterionAssessment` and
is never treated as a final grade.  Applying an assessment creates an
*unpublished* ``Grade`` that an instructor must review and publish.
"""

from __future__ import annotations

import hashlib
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Project(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    assignment = models.ForeignKey(
        'courses.Assignment', related_name='projects', on_delete=models.CASCADE
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='classforge_projects',
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_workspaces'
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'student'], name='uq_project_assignment_student'
            )
        ]
        indexes = [
            models.Index(fields=['student', 'status'], name='idx_project_student_status'),
        ]

    def __str__(self):
        return self.title or f'{self.student} / {self.assignment}'

    @property
    def course(self):
        return self.assignment.course

    @property
    def latest_snapshot(self):
        return self.snapshots.order_by('-version').first()

    @property
    def snapshot_count(self):
        return self.snapshots.count()

    @property
    def open_revisions(self):
        return self.revision_requests.filter(status=RevisionRequest.STATUS_OPEN)

    @property
    def is_archived(self):
        return self.status == self.STATUS_ARCHIVED


class Repository(models.Model):
    """Server-owned Git workspace metadata for a project.

    Actual Git commands are executed by :mod:`apps.projects.git_workspace` in a
    directory owned by the server.  Student code is never executed.
    """

    provider = models.CharField(max_length=32, blank=True, default='local')
    project = models.OneToOneField(
        Project, related_name='repository', on_delete=models.CASCADE
    )
    remote_url = models.URLField(max_length=500, blank=True, default='')
    default_branch = models.CharField(max_length=128, default='main')
    current_branch = models.CharField(max_length=128, default='main')
    last_commit_sha = models.CharField(max_length=64, blank=True, default='')
    git_initialised = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_repositories'

    def __str__(self):
        return f'Repository for {self.project}'


class ProjectSnapshot(models.Model):
    """An immutable, checksummed project archive."""

    SOURCE_VSCODE = 'vscode'
    SOURCE_API = 'api'
    SOURCE_WEB = 'web'
    SOURCE_SYSTEM = 'system'
    SOURCE_CHOICES = [
        (SOURCE_VSCODE, 'VS Code extension'),
        (SOURCE_API, 'API client'),
        (SOURCE_WEB, 'Web upload'),
        (SOURCE_SYSTEM, 'System import'),
    ]

    project = models.ForeignKey(
        Project, related_name='snapshots', on_delete=models.CASCADE
    )
    submission = models.OneToOneField(
        'courses.Submission',
        related_name='project_snapshot',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    version = models.PositiveIntegerField(default=1)
    source = models.CharField(
        max_length=16, choices=SOURCE_CHOICES, default=SOURCE_WEB
    )
    branch = models.CharField(max_length=128, default='main')
    parent = models.ForeignKey(
        'self',
        related_name='children',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    archive = models.FileField(
        upload_to='project_snapshots/%Y/%m/', max_length=255, blank=True
    )
    checksum = models.CharField(max_length=64, blank=True, default='')
    commit_sha = models.CharField(max_length=64, blank=True, default='')
    base_commit_sha = models.CharField(max_length=64, blank=True, default='')
    file_count = models.PositiveIntegerField(default=0)
    total_bytes = models.BigIntegerField(default=0)
    manifest = models.JSONField(default=list, blank=True)
    validation = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    note = models.CharField(max_length=500, blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='project_snapshots_created',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_snapshots'
        ordering = ['-version']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'version'], name='uq_snapshot_project_version'
            )
        ]
        indexes = [
            models.Index(
                fields=['project', '-version'], name='idx_snapshot_project_version'
            ),
            models.Index(fields=['checksum'], name='idx_snapshot_checksum'),
        ]

    def __str__(self):
        return f'{self.project} v{self.version}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                'Project snapshots are immutable. Create a new snapshot instead.'
            )
        if not self.checksum and self.archive:
            self.checksum = self.calculate_checksum()
        super().save(*args, **kwargs)

    def calculate_checksum(self):
        digest = hashlib.sha256()
        try:
            with self.archive.open('rb') as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                    digest.update(chunk)
        except (OSError, ValueError):
            return ''
        return digest.hexdigest()

    @property
    def short_commit(self):
        return (self.commit_sha or '')[:12]

    @property
    def short_checksum(self):
        return (self.checksum or '')[:12]

    @property
    def latest_assessment(self):
        return self.assessments.order_by('-created_at').first()

    @property
    def files(self):
        return [item.get('path', '') for item in (self.manifest or []) if item.get('path')]


class RevisionRequest(models.Model):
    STATUS_OPEN = 'open'
    STATUS_ADDRESSED = 'addressed'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_ADDRESSED, 'Addressed'),
        (STATUS_CLOSED, 'Closed'),
    ]

    project = models.ForeignKey(
        Project, related_name='revision_requests', on_delete=models.CASCADE
    )
    snapshot = models.ForeignKey(
        ProjectSnapshot,
        related_name='revision_requests',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    branch_name = models.CharField(max_length=128, blank=True, default='')
    due_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='revision_requests_created',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='revision_requests_resolved',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_revision_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status'], name='idx_revision_project_status'),
        ]

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        return self.status == self.STATUS_OPEN


class PullRequest(models.Model):
    STATUS_OPEN = 'open'
    STATUS_MERGED = 'merged'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_MERGED, 'Merged'),
        (STATUS_CLOSED, 'Closed'),
    ]

    project = models.ForeignKey(
        Project, related_name='pull_requests', on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    source_snapshot = models.ForeignKey(
        ProjectSnapshot,
        related_name='pull_requests_from',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    merged_snapshot = models.ForeignKey(
        ProjectSnapshot,
        related_name='pull_requests_merged',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    revision_request = models.ForeignKey(
        RevisionRequest,
        related_name='pull_requests',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    source_branch = models.CharField(max_length=128, default='feature')
    target_branch = models.CharField(max_length=128, default='main')
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='pull_requests_created',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='pull_requests_reviewed',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    merge_commit_sha = models.CharField(max_length=64, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    merged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'project_pull_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status'], name='idx_pr_project_status'),
        ]

    def __str__(self):
        return f'#{self.pk} {self.title}'

    @property
    def is_open(self):
        return self.status == self.STATUS_OPEN


class PullRequestComment(models.Model):
    pull_request = models.ForeignKey(
        PullRequest, related_name='comments', on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='pull_request_comments',
        on_delete=models.CASCADE,
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_pull_request_comments'
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author}'


class Assessment(models.Model):
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

    REVIEW_PENDING = 'pending'
    REVIEW_APPROVED = 'approved'
    REVIEW_OVERRIDDEN = 'overridden'
    REVIEW_REJECTED = 'rejected'
    REVIEW_CHOICES = [
        (REVIEW_PENDING, 'Pending instructor review'),
        (REVIEW_APPROVED, 'Approved by instructor'),
        (REVIEW_OVERRIDDEN, 'Overridden by instructor'),
        (REVIEW_REJECTED, 'Rejected'),
    ]

    ENGINE_LOCAL = 'local'
    ENGINE_AI = 'ai'
    ENGINE_CHOICES = [
        (ENGINE_LOCAL, 'Deterministic inspector'),
        (ENGINE_AI, 'AI model'),
    ]

    snapshot = models.ForeignKey(
        ProjectSnapshot, related_name='assessments', on_delete=models.CASCADE
    )
    rubric_version = models.ForeignKey(
        'courses.RubricVersion',
        related_name='assessments',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_QUEUED
    )
    mode = models.CharField(max_length=32, default='instructor_approved')
    engine = models.CharField(
        max_length=16, choices=ENGINE_CHOICES, default=ENGINE_LOCAL
    )
    model_name = models.CharField(max_length=255, blank=True, default='')
    overall_score = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    max_score = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    summary = models.TextField(blank=True, default='')
    feedback = models.TextField(blank=True, default='')
    validation = models.JSONField(default=dict, blank=True)
    checks = models.JSONField(default=list, blank=True)
    structure = models.JSONField(default=dict, blank=True)
    artifacts = models.JSONField(default=dict, blank=True)
    evidence = models.JSONField(default=list, blank=True)
    raw_response = models.TextField(blank=True, default='')
    error = models.TextField(blank=True, default='')
    attempts = models.PositiveIntegerField(default=0)
    requires_review = models.BooleanField(default=True)
    review_status = models.CharField(
        max_length=16, choices=REVIEW_CHOICES, default=REVIEW_PENDING
    )
    instructor_score = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    instructor_feedback = models.TextField(blank=True, default='')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='assessments_reviewed',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    applied_grade = models.OneToOneField(
        'courses.Grade',
        related_name='source_assessment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    applied_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='assessments_requested',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'project_assessments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['snapshot', '-created_at'], name='idx_assess_snapshot'),
            models.Index(fields=['status', 'created_at'], name='idx_assess_status'),
        ]

    def __str__(self):
        return f'Assessment {self.pk} for {self.snapshot}'

    @property
    def is_completed(self):
        return self.status == self.STATUS_COMPLETED

    @property
    def percentage(self):
        if not self.max_score:
            return Decimal('0')
        score = self.instructor_score
        if score is None:
            score = self.overall_score or Decimal('0')
        return (score / self.max_score) * Decimal('100')

    @property
    def effective_score(self):
        if self.instructor_score is not None:
            return self.instructor_score
        return self.overall_score

    @property
    def is_ai_generated(self):
        return self.engine == self.ENGINE_AI


class CriterionAssessment(models.Model):
    assessment = models.ForeignKey(
        Assessment, related_name='criteria', on_delete=models.CASCADE
    )
    criterion = models.ForeignKey(
        'courses.RubricCriterion',
        related_name='project_assessments',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    criterion_name = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    max_points = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    ai_points = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(Decimal('999.99'))],
    )
    instructor_points = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(Decimal('999.99'))],
    )
    comment = models.TextField(blank=True, default='')
    evidence = models.TextField(blank=True, default='')
    confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_criterion_assessments'
        ordering = ['position', 'id']

    def __str__(self):
        return f'{self.criterion_name}: {self.points}/{self.max_points}'

    @property
    def points(self):
        return (
            self.instructor_points
            if self.instructor_points is not None
            else self.ai_points
        )


class Notification(models.Model):
    KIND_INFO = 'info'
    KIND_ASSESSMENT = 'assessment'
    KIND_REVISION = 'revision'
    KIND_PULL_REQUEST = 'pull_request'
    KIND_GRADE = 'grade'
    KIND_CHOICES = [
        (KIND_INFO, 'Information'),
        (KIND_ASSESSMENT, 'Assessment'),
        (KIND_REVISION, 'Revision request'),
        (KIND_PULL_REQUEST, 'Pull request'),
        (KIND_GRADE, 'Grade'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='classforge_notifications',
        on_delete=models.CASCADE,
    )
    kind = models.CharField(max_length=32, choices=KIND_CHOICES, default=KIND_INFO)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default='')
    url = models.CharField(max_length=500, blank=True, default='')
    project = models.ForeignKey(
        Project,
        related_name='notifications',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    snapshot = models.ForeignKey(
        ProjectSnapshot,
        related_name='notifications',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'classforge_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read_at'], name='idx_notify_user_read'),
        ]

    def __str__(self):
        return self.title

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])


class ApiToken(models.Model):
    """Hashed bearer token used by the VS Code extension and API clients."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='classforge_api_tokens',
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=120, default='API token')
    prefix = models.CharField(max_length=16, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    scopes = models.CharField(
        max_length=255, blank=True, default='read write'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'classforge_api_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.prefix}…)'

    @staticmethod
    def hash_token(raw):
        return hashlib.sha256((raw or '').encode('utf-8')).hexdigest()

    @classmethod
    def issue(cls, user, name='VS Code extension', scopes='read write', days=None):
        raw = 'cf_' + secrets.token_urlsafe(40)
        days = (
            settings.CLASSFORGE_TOKEN_TTL_DAYS if days is None else days
        )
        expires_at = (
            timezone.now() + timezone.timedelta(days=days) if days else None
        )
        token = cls.objects.create(
            user=user,
            name=(name or 'API token')[:120],
            prefix=raw[:10],
            token_hash=cls.hash_token(raw),
            scopes=scopes,
            expires_at=expires_at,
        )
        return token, raw

    @classmethod
    def authenticate(cls, raw):
        if not raw:
            return None
        token = (
            cls.objects.select_related('user')
            .filter(token_hash=cls.hash_token(raw), revoked_at__isnull=True)
            .first()
        )
        if token is None:
            return None
        if token.expires_at and token.expires_at < timezone.now():
            return None
        if not token.user.is_active:
            return None
        cls.objects.filter(pk=token.pk).update(last_used_at=timezone.now())
        return token

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < timezone.now())

    @property
    def is_revoked(self):
        return self.revoked_at is not None

    @property
    def scope_list(self):
        return [scope for scope in (self.scopes or '').split() if scope]
