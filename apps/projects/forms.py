from django import forms

from .models import Project, PullRequest


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class PullRequestForm(forms.ModelForm):
    class Meta:
        model = PullRequest
        fields = [
            'title',
            'description',
            'source_snapshot',
            'source_branch',
            'target_branch',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'source_snapshot': forms.Select(attrs={'class': 'form-select'}),
            'source_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'target_branch': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields['source_snapshot'].queryset = project.snapshots.order_by('-version')
            self.fields['source_snapshot'].required = True


class AssessmentReviewForm(forms.Form):
    ACTION_CHOICES = [
        ('approve', 'Use the feedback as is'),
        ('override', 'Use my scores'),
        ('reject', 'Reject the feedback'),
    ]
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    instructor_score = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=7,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        help_text='Leave blank to use the approved suggested total.',
    )
    instructor_feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
    )


class CommentForm(forms.Form):
    body = forms.CharField(
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add a comment…'}
        )
    )
