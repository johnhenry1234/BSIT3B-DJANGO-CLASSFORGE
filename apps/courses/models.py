"""ClassForge LMS models: Course, Enrollment, Assignment, Submission, Grade."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Max


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignments'
        ordering = ['due_date']

    def __str__(self):
        return f'{self.title} ({self.course.code})'


class Submission(models.Model):
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
        if not self.file_attachment and not (self.text_content or '').strip():
            raise ValidationError(
                'Provide either a file attachment or text content.'
            )

    def save(self, *args, **kwargs):
        # Append-only versioning: the version is fully managed. On insert it
        # is always set to MAX(version) + 1 for this (assignment, student)
        # pair, ignoring any caller-supplied value (the field is
        # editable=False). The UNIQUE(assignment, student, version)
        # constraint remains as a race-condition backstop and raises
        # IntegrityError on concurrent inserts.
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
    created_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'grades'
        ordering = ['-graded_at']

    def __str__(self):
        return f'{self.score} for {self.submission}'

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
