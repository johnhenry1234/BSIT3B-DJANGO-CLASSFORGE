"""ClassForge models.

The grading architecture is intentionally decoupled:

* ``Submission`` is an append-only *submission version*.  Re-submitting never
  updates an earlier row; it inserts a new row with ``version = MAX + 1``.
* ``Grade`` and ``AIEvaluation`` are independent records that point at a
  specific submission version.  An AI draft can therefore exist without a
  grade, and an instructor grade can exist without (or in spite of) an AI
  draft.
* Rubric totals, assignment averages and class averages are computed from
  database aggregations at read time rather than stored as denormalised
  fields.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Max, Sum


class Course(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    code = models.CharField(max_length=50, unique=True)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='courses_taught',
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'

    def clean(self):
        super().clean()
        if self.code:
            self.code = self.code.strip().upper()

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)


class CourseAssistant(models.Model):
    """A Teaching Assistant assigned to grade one course."""

    course = models.ForeignKey(
        Course, related_name='assistants', on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='assisting_courses',
        on_delete=models.CASCADE,
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='assistants_added',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_assistants'
        ordering = ['user__username']
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'user'], name='uq_course_assistants_course_user'
            )
        ]

    def __str__(self):
        return f'{self.user} assists {self.course.code}'


class Enrollment(models.Model):
    course = models.ForeignKey(
        Course, related_name='enrollments', on_delete=models.CASCADE
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='enrollments',
        on_delete=models.CASCADE,
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'enrollments'
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'student'], name='uq_enrollments_course_student'
            )
        ]
        ordering = ['-enrolled_at']

    def __str__(self):
        return f'{self.student} enrolled in {self.course.code}'


class Assignment(models.Model):
    CATEGORY_CODE_PROJECT = 'code_project'
    CATEGORY_ERD = 'erd'
    CATEGORY_DATABASE_DESIGN = 'database_design'
    CATEGORY_DOCUMENTATION = 'documentation'
    CATEGORY_OTHER = 'other'
    CATEGORY_CHOICES = [
        (CATEGORY_CODE_PROJECT, 'Code Project'),
        (CATEGORY_ERD, 'ERD / Diagram'),
        (CATEGORY_DATABASE_DESIGN, 'Database Design'),
        (CATEGORY_DOCUMENTATION, 'Documentation'),
        (CATEGORY_OTHER, 'Other'),
    ]

    course = models.ForeignKey(
        Course, related_name='assignments', on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_CODE_PROJECT
    )
    description = models.TextField(blank=True, default='')
    due_date = models.DateTimeField()
    max_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(1), MaxValueValidator(999.99)],
    )

    # AI Auto-Grader / Submission Inspector configuration.
    guidelines = models.TextField(
        blank=True,
        default='',
        help_text='Instructions the AI assistant should evaluate against.',
    )
    required_files = models.TextField(
        blank=True,
        default='',
        help_text='One mandatory file name per line (e.g. README.md).',
    )
    accepts_zip = models.BooleanField(default=True)
    accepts_pdf = models.BooleanField(default=True)
    ai_auto_run = models.BooleanField(
        default=True,
        help_text='Queue an AI draft automatically once guidelines are configured.',
    )

    # --- Project platform configuration (migration 0005) -------------------
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    AI_MODE_INSTRUCTOR_APPROVED = 'instructor_approved'
    AI_MODE_AUTOMATIC = 'automatic'
    AI_MODE_ADVISORY = 'advisory'
    AI_MODE_CHOICES = [
        (AI_MODE_INSTRUCTOR_APPROVED, 'Instructor-approved assessment'),
        (AI_MODE_AUTOMATIC, 'Automatic assessment (score proposed, review still available)'),
        (AI_MODE_ADVISORY, 'Advisory assessment (instructor grades)'),
    ]

    LATE_ACCEPT = 'accept'
    LATE_PENALTY = 'penalty'
    LATE_REJECT = 'reject'
    LATE_POLICY_CHOICES = [
        (LATE_ACCEPT, 'Accept late submissions'),
        (LATE_PENALTY, 'Accept with a recorded penalty'),
        (LATE_REJECT, 'Reject after the deadline'),
    ]

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PUBLISHED
    )
    published_at = models.DateTimeField(null=True, blank=True)
    expected_outcomes = models.TextField(
        blank=True,
        default='',
        help_text='What a successful project should demonstrate.',
    )
    accepted_formats = models.TextField(
        blank=True,
        default='',
        help_text='One format per line, e.g. .zip, .sql, .sqlite, .db, .pdf, .md.',
    )
    required_directories = models.TextField(
        blank=True,
        default='',
        help_text='One mandatory directory per line, e.g. src, docs.',
    )
    documentation_requirements = models.TextField(
        blank=True,
        default='',
        help_text='Documentation the submission must contain.',
    )
    validation_rules = models.TextField(
        blank=True,
        default='',
        help_text=(
            'One deterministic rule per line. Supported: require_sql, '
            'require_primary_keys, require_foreign_keys, require_readme, '
            'sql_syntax, require_tests, naming_snake_case, forbid_secrets.'
        ),
    )
    required_tests = models.TextField(
        blank=True,
        default='',
        help_text='Tests the isolated runner should execute (one command per line).',
    )
    max_upload_mb = models.PositiveIntegerField(
        default=25, validators=[MinValueValidator(1), MaxValueValidator(500)]
    )
    ai_grading_mode = models.CharField(
        max_length=32,
        choices=AI_MODE_CHOICES,
        default=AI_MODE_INSTRUCTOR_APPROVED,
        help_text='Default favours instructor review until grading is calibrated.',
    )
    manual_review_required = models.BooleanField(default=True)
    late_policy = models.CharField(
        max_length=16, choices=LATE_POLICY_CHOICES, default=LATE_ACCEPT
    )
    late_penalty_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    allow_resubmission = models.BooleanField(default=True)
    revision_deadline_days = models.PositiveIntegerField(default=7)
    default_exclusions = models.TextField(
        blank=True,
        default='',
        help_text='Extra ignore patterns applied to VS Code/API uploads.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignments'
        ordering = ['due_date']

    def __str__(self):
        return f'{self.title} ({self.course.code})'

    @property
    def has_ai_guidelines(self):
        return bool((self.guidelines or '').strip() or self.required_files_list)

    @property
    def required_files_list(self):
        return [
            line.strip()
            for line in (self.required_files or '').splitlines()
            if line.strip()
        ]

    @property
    def required_directories_list(self):
        return [
            line.strip().strip('/')
            for line in (self.required_directories or '').splitlines()
            if line.strip().strip('/')
        ]

    @property
    def accepted_formats_list(self):
        return [
            line.strip().lower()
            for line in (self.accepted_formats or '').splitlines()
            if line.strip()
        ]

    @property
    def validation_rules_list(self):
        return [
            line.strip().lower().replace('-', '_')
            for line in (self.validation_rules or '').splitlines()
            if line.strip()
        ]

    @property
    def required_tests_list(self):
        return [
            line.strip()
            for line in (self.required_tests or '').splitlines()
            if line.strip()
        ]

    @property
    def default_exclusions_list(self):
        return [
            line.strip()
            for line in (self.default_exclusions or '').splitlines()
            if line.strip()
        ]

    @property
    def is_published(self):
        return self.status == self.STATUS_PUBLISHED

    @property
    def rubric_total_points(self):
        rubric = getattr(self, 'rubric', None)
        return rubric.total_points if rubric else Decimal('0')

    @property
    def effective_max_score(self):
        return self.rubric_total_points or self.max_score

    @property
    def accepted_types(self):
        types = []
        if self.accepts_zip:
            types.append('.zip')
        if self.accepts_pdf:
            types.append('.pdf')
        return types


class Submission(models.Model):
    """An immutable submission version.

    ``SubmissionVersion`` is exported as an alias at the bottom of this module
    so the concept-paper terminology can be used in new code without a risky
    model/table rename.
    """

    assignment = models.ForeignKey(
        Assignment, related_name='submissions', on_delete=models.CASCADE
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='submissions',
        on_delete=models.CASCADE,
    )
    version = models.PositiveIntegerField(default=1, editable=False)
    file_attachment = models.FileField(
        upload_to='submissions/%Y/%m/', max_length=255, blank=True, null=True
    )
    text_content = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'submissions'
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'student', 'version'],
                name='uq_submissions_assignment_student_version',
            )
        ]
        ordering = ['assignment_id', 'student_id', '-version']
        indexes = [
            models.Index(
                fields=['assignment', 'student'],
                name='idx_submissions_asgmt_student',
            ),
        ]

    def __str__(self):
        return f'v{self.version} by {self.student} for {self.assignment}'

    def clean(self):
        super().clean()
        has_file = bool(self.file_attachment)
        has_text = bool((self.text_content or '').strip())
        if not (has_file or has_text):
            raise ValidationError(
                'Provide a file attachment or text content.'
            )

    def save(self, *args, **kwargs):
        # Append-only versioning: on insert the version is always set to
        # MAX(version) + 1 for this (assignment, student) pair.  The UNIQUE
        # constraint remains a race-condition backstop.
        if self._state.adding:
            existing_max = (
                Submission.objects.filter(
                    assignment=self.assignment, student=self.student
                ).aggregate(Max('version'))['version__max']
                or 0
            )
            self.version = existing_max + 1
        self.full_clean(exclude=['version'])
        super().save(*args, **kwargs)

    @property
    def is_late(self):
        return self.submitted_at > self.assignment.due_date

    @property
    def is_latest(self):
        latest = (
            Submission.objects.filter(
                assignment=self.assignment, student=self.student
            ).aggregate(Max('version'))['version__max']
        )
        return latest is not None and self.version == latest

    @property
    def submission_type(self):
        if self.file_attachment:
            name = (self.file_attachment.name or '').lower()
            if name.endswith('.zip'):
                return 'zip'
            if name.endswith('.pdf'):
                return 'pdf'
            return 'file'
        return 'text'


class Rubric(models.Model):
    assignment = models.OneToOneField(
        Assignment, related_name='rubric', on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255, default='Grading Rubric')
    instructions = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rubrics'

    def __str__(self):
        return f'{self.title} for {self.assignment.title}'

    @property
    def total_points(self):
        total = self.criteria.aggregate(total=Sum('max_points'))['total']
        return total or Decimal('0')

    @property
    def weight_total(self):
        total = self.criteria.aggregate(total=Sum('weight'))['total']
        return total or Decimal('0')


class RubricCriterion(models.Model):
    rubric = models.ForeignKey(
        Rubric, related_name='criteria', on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    max_points = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=10,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('999.99'))],
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Optional percentage weight for reporting.',
    )
    position = models.PositiveIntegerField(default=0)

    # --- Rich rubric builder fields (migration 0005) -----------------------
    expected_evidence = models.TextField(
        blank=True,
        default='',
        help_text='Evidence the assessor should look for (files, tables, behaviours).',
    )
    scoring_guidance = models.TextField(
        blank=True,
        default='',
        help_text='How to award partial credit for this criterion.',
    )
    validation_rule = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text='Optional deterministic rule key, e.g. require_primary_keys.',
    )
    ai_instructions = models.TextField(
        blank=True,
        default='',
        help_text='Criterion-specific assessment instructions for the AI.',
    )
    feedback_requirements = models.TextField(
        blank=True,
        default='',
        help_text='What the feedback for this criterion must include.',
    )

    class Meta:
        db_table = 'rubric_criteria'
        ordering = ['position', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['rubric', 'name'], name='uq_rubric_criteria_rubric_name'
            )
        ]

    def __str__(self):
        return f'{self.name} ({self.max_points} pts)'


class RubricVersion(models.Model):
    """Immutable snapshot of a rubric at publication time.

    Assessments reference this record so historical results stay explainable
    after the instructor edits the rubric.
    """

    rubric = models.ForeignKey(
        Rubric, related_name='versions', on_delete=models.CASCADE
    )
    assignment = models.ForeignKey(
        Assignment, related_name='rubric_versions', on_delete=models.CASCADE
    )
    version = models.PositiveIntegerField(default=1)
    snapshot = models.JSONField(default=dict, blank=True)
    total_points = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal('0')
    )
    notes = models.TextField(blank=True, default='')
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='rubric_versions_published',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rubric_versions'
        ordering = ['-version']
        constraints = [
            models.UniqueConstraint(
                fields=['rubric', 'version'],
                name='uq_rubric_versions_rubric_version',
            )
        ]
        indexes = [
            models.Index(
                fields=['assignment', '-version'],
                name='idx_rubric_versions_assignment',
            )
        ]

    def __str__(self):
        return f'{self.rubric.title} v{self.version}'

    @property
    def criteria_snapshot(self):
        return (self.snapshot or {}).get('criteria', [])


class Grade(models.Model):
    submission = models.OneToOneField(
        Submission, related_name='grade', on_delete=models.CASCADE
    )
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='grades_given',
        on_delete=models.CASCADE,
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(999.99)],
    )
    feedback = models.TextField(blank=True, default='')
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='grades_published',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'grades'
        ordering = ['-graded_at']

    def __str__(self):
        return f'{self.score} for {self.submission}'

    @property
    def max_score(self):
        return self.submission.assignment.effective_max_score

    @property
    def percentage(self):
        max_score = self.max_score
        if not max_score:
            return Decimal('0')
        return (self.score / max_score) * Decimal('100')

    def clean(self):
        super().clean()
        assignment = None
        if getattr(self, 'submission_id', None):
            try:
                assignment = self.submission.assignment
            except Submission.DoesNotExist:
                assignment = None
        max_score = getattr(assignment, 'max_score', None)
        if max_score is not None and self.score is not None and self.score > max_score:
            raise ValidationError(
                {'score': f'Score cannot exceed max score of {max_score}.'}
            )

    def sync_score_from_criteria(self, save=True):
        """Recompute the total from criterion scores using an aggregation."""
        total = self.criterion_scores.aggregate(total=Sum('points_awarded'))['total']
        self.score = min(total or Decimal('0'), self.max_score)
        if save:
            self.save(update_fields=['score', 'graded_at'])
        return self.score


class CriterionScore(models.Model):
    """Instructor-entered points for one rubric criterion of one grade."""

    grade = models.ForeignKey(
        Grade, related_name='criterion_scores', on_delete=models.CASCADE
    )
    criterion = models.ForeignKey(
        RubricCriterion, related_name='scores', on_delete=models.CASCADE
    )
    points_awarded = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(Decimal('999.99'))],
    )
    comment = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'criterion_scores'
        ordering = ['criterion__position', 'criterion_id']
        constraints = [
            models.UniqueConstraint(
                fields=['grade', 'criterion'],
                name='uq_criterion_scores_grade_criterion',
            )
        ]

    def __str__(self):
        return f'{self.points_awarded}/{self.criterion.max_points} on {self.criterion.name}'

    def clean(self):
        super().clean()
        if (
            self.criterion_id
            and self.points_awarded is not None
            and self.points_awarded > self.criterion.max_points
        ):
            raise ValidationError(
                {'points_awarded': f'Cannot exceed {self.criterion.max_points} points.'}
            )
        if self.grade_id and self.criterion_id:
            grade_rubric = getattr(self.grade.submission.assignment, 'rubric', None)
            if grade_rubric and self.criterion.rubric_id != grade_rubric.id:
                raise ValidationError('Criterion does not belong to this assignment.')


class FeedbackAnnotation(models.Model):
    """Inline feedback anchored to a page, line or file, with optional file."""

    grade = models.ForeignKey(
        Grade, related_name='annotations', on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='feedback_annotations',
        on_delete=models.CASCADE,
    )
    anchor = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Where the comment applies, e.g. "report.pdf p. 2" or "app.py line 14".',
    )
    body = models.TextField()
    file_attachment = models.FileField(
        upload_to='feedback/%Y/%m/', max_length=255, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feedback_annotations'
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on {self.grade.submission}'


class AssignmentSeen(models.Model):
    """Track which assignments a student has viewed on the dashboard."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='assignment_seen',
        on_delete=models.CASCADE,
    )
    assignment = models.ForeignKey(
        Assignment,
        related_name='seen_by',
        on_delete=models.CASCADE,
    )
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'assignment_seen'
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'assignment'], name='uq_assignment_seen_student_assignment'
            )
        ]
        ordering = ['-seen_at']

    def __str__(self):
        return f'{self.student} seen {self.assignment}'


# Concept-paper terminology alias (no table/model rename required).
SubmissionVersion = Submission
