from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Assignment,
    Course,
    FeedbackAnnotation,
    Grade,
    Rubric,
    RubricCriterion,
    Submission,
)


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = [
            'title',
            'category',
            'description',
            'due_date',
            'max_score',
            'status',
            'guidelines',
            'required_files',
            'expected_outcomes',
            'accepted_formats',
            'required_directories',
            'documentation_requirements',
            'validation_rules',
            'required_tests',
            'max_upload_mb',
            'ai_grading_mode',
            'manual_review_required',
            'late_policy',
            'late_penalty_percent',
            'allow_resubmission',
            'revision_deadline_days',
            'default_exclusions',
            'accepts_zip',
            'accepts_pdf',
            'ai_auto_run',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'due_date': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
            'max_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'guidelines': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'e.g. Must include a working CRUD module, a README, and an ERD.',
                }
            ),
            'required_files': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'README.md\nrequirements.txt\nschema.sql',
                }
            ),
            'expected_outcomes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'accepted_formats': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': '.zip\n.sql\n.sqlite\n.pdf\n.md',
                }
            ),
            'required_directories': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'src\ndocs'}
            ),
            'documentation_requirements': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'validation_rules': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'require_readme\nrequire_primary_keys\nrequire_foreign_keys\nforbid_secrets',
                }
            ),
            'required_tests': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'python manage.py test',
                }
            ),
            'max_upload_mb': forms.NumberInput(attrs={'class': 'form-control'}),
            'ai_grading_mode': forms.Select(attrs={'class': 'form-select'}),
            'manual_review_required': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'late_policy': forms.Select(attrs={'class': 'form-select'}),
            'late_penalty_percent': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01'}
            ),
            'allow_resubmission': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'revision_deadline_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'default_exclusions': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': '*.log\ntmp/**\n.env.local',
                }
            ),
            'accepts_zip': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_pdf': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ai_auto_run': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned = super().clean()
        if not any(
            [
                cleaned.get('accepts_zip'),
                cleaned.get('accepts_pdf'),
            ]
        ):
            raise ValidationError(
                'Enable at least one accepted submission type (.zip or PDF).'
            )
        return cleaned


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file_attachment', 'text_content']
        widgets = {
            'file_attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'text_content': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 5}
            ),
        }

    def __init__(self, *args, assignment=None, **kwargs):
        self.assignment = assignment
        super().__init__(*args, **kwargs)
        if assignment:
            accepted = assignment.accepted_types
            self.fields['file_attachment'].help_text = (
                'Accepted: ' + (', '.join(accepted) if accepted else 'none configured')
            )

    def clean(self):
        cleaned = super().clean()
        file_attachment = cleaned.get('file_attachment')
        text_content = (cleaned.get('text_content') or '').strip()

        if not file_attachment and not text_content:
            raise forms.ValidationError(
                'Provide a file attachment or text content.'
            )

        assignment = self.assignment
        if assignment and file_attachment:
            name = (file_attachment.name or '').lower()
            if name.endswith('.zip') and not assignment.accepts_zip:
                self.add_error(
                    'file_attachment', 'This assignment does not accept .zip archives.'
                )
            elif name.endswith('.pdf') and not assignment.accepts_pdf:
                self.add_error(
                    'file_attachment', 'This assignment does not accept PDF files.'
                )
            elif not (name.endswith('.zip') or name.endswith('.pdf')):
                self.add_error(
                    'file_attachment',
                    'Only .zip code archives and PDF documentation are accepted.',
                )

        return cleaned


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['score', 'feedback', 'is_published']
        widgets = {
            'score': forms.NumberInput(attrs={'class': 'form-control'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_published': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }


class RubricForm(forms.ModelForm):
    class Meta:
        model = Rubric
        fields = ['title', 'instructions']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class RubricCriterionForm(forms.ModelForm):
    class Meta:
        model = RubricCriterion
        fields = [
            'name',
            'description',
            'max_points',
            'weight',
            'position',
            'expected_evidence',
            'scoring_guidance',
            'validation_rule',
            'ai_instructions',
            'feedback_requirements',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'max_points': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm', 'step': '0.01'}
            ),
            'weight': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm', 'step': '0.01'}
            ),
            'position': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'expected_evidence': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': 2}
            ),
            'scoring_guidance': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': 2}
            ),
            'validation_rule': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'require_primary_keys',
                }
            ),
            'ai_instructions': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': 2}
            ),
            'feedback_requirements': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': 2}
            ),
        }


class RubricGradeForm(forms.Form):
    """Dynamic rubric grading form.

    One decimal field is created per rubric criterion; the total is derived
    from these values and never trusted from the browser.
    """

    feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
    )
    is_published = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, rubric=None, grade=None, **kwargs):
        self.rubric = rubric
        self.grade = grade
        super().__init__(*args, **kwargs)
        existing = {}
        if grade is not None:
            existing = {
                cs.criterion_id: cs
                for cs in grade.criterion_scores.select_related('criterion')
            }
        for criterion in rubric.criteria.all():
            key = f'criterion_{criterion.id}'
            initial = None
            comment = ''
            if criterion.id in existing:
                initial = existing[criterion.id].points_awarded
                comment = existing[criterion.id].comment
            self.fields[key] = forms.DecimalField(
                label=criterion.name,
                required=False,
                min_value=Decimal('0'),
                max_value=criterion.max_points,
                initial=initial,
                decimal_places=2,
                widget=forms.NumberInput(
                    attrs={
                        'class': 'form-control form-control-sm rubric-points',
                        'step': '0.01',
                        'data-max': str(criterion.max_points),
                    }
                ),
            )
            self.fields[f'comment_{criterion.id}'] = forms.CharField(
                label=f'{criterion.name} comment',
                required=False,
                initial=comment,
                widget=forms.TextInput(
                    attrs={'class': 'form-control form-control-sm'}
                ),
            )

    def criteria_values(self):
        """Yield ``(criterion, points, comment)`` for every rubric row."""
        for criterion in self.rubric.criteria.all():
            points = self.cleaned_data.get(f'criterion_{criterion.id}')
            comment = (self.cleaned_data.get(f'comment_{criterion.id}') or '').strip()
            yield criterion, points or Decimal('0'), comment

    def criteria_rows(self):
        """Template-friendly rows pairing each criterion with its inputs."""
        if self.rubric is None:
            return
        for criterion in self.rubric.criteria.all():
            yield {
                'criterion': criterion,
                'points': self[f'criterion_{criterion.id}'],
                'comment': self[f'comment_{criterion.id}'],
            }


class AnnotationForm(forms.ModelForm):
    class Meta:
        model = FeedbackAnnotation
        fields = ['anchor', 'body', 'file_attachment']
        widgets = {
            'anchor': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'e.g. report.pdf p. 2'}
            ),
            'body': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Inline comment...'}
            ),
            'file_attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        if not (cleaned.get('body') or '').strip() and not cleaned.get('file_attachment'):
            raise ValidationError('Write a comment or attach a file.')
        return cleaned
