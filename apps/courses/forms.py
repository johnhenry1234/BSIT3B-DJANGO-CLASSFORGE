from django import forms

from .models import Assignment, Course, Grade, Submission


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
        fields = ['title', 'category', 'description', 'due_date', 'max_score']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'due_date': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
            'max_score': forms.NumberInput(attrs={'class': 'form-control'}),
        }


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

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('file_attachment') and not (
            cleaned.get('text_content') or ''
        ).strip():
            raise forms.ValidationError(
                'Provide either a file attachment or text content.'
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
