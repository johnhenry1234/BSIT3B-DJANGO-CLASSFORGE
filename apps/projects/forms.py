from django import forms

from .models import Project, PullRequest, RevisionRequest


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class RevisionRequestForm(forms.ModelForm):
    class Meta:
        model = RevisionRequest
        fields = ['title', 'description', 'snapshot', 'branch_name', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'snapshot': forms.Select(attrs={'class': 'form-select'}),
            'branch_name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'revision/feedback-1'}
            ),
            'due_date': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields['snapshot'].queryset = project.snapshots.order_by('-version')
            self.fields['snapshot'].required = False
        self.fields['due_date'].required = False


class PullRequestForm(forms.ModelForm):
    class Meta:
        model = PullRequest
        fields = [
            'title',
            'description',
            'source_snapshot',
            'source_branch',
            'target_branch',
            'revision_request',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'source_snapshot': forms.Select(attrs={'class': 'form-select'}),
            'source_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'target_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'revision_request': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields['source_snapshot'].queryset = project.snapshots.order_by('-version')
            self.fields['source_snapshot'].required = True
            self.fields['revision_request'].queryset = project.revision_requests.filter(
                status=RevisionRequest.STATUS_OPEN
            )
        self.fields['revision_request'].required = False


class AssessmentReviewForm(forms.Form):
    ACTION_CHOICES = [
        ('approve', 'Approve the draft'),
        ('override', 'Override with my scores'),
        ('reject', 'Reject the draft'),
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
        help_text='Leave blank to use the approved draft total.',
    )
    instructor_feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
    )


class CommentForm(forms.Form):
    body = forms.CharField(
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add a review comment…'}
        )
    )
