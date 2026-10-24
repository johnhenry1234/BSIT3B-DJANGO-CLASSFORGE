from django.contrib import admin

from .models import (
    Assignment,
    Course,
    CourseAssistant,
    CriterionScore,
    Enrollment,
    FeedbackAnnotation,
    Grade,
    Rubric,
    RubricCriterion,
    Submission,
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'instructor', 'created_at')
    search_fields = ('code', 'name', 'instructor__username')
    list_filter = ('created_at',)


@admin.register(CourseAssistant)
class CourseAssistantAdmin(admin.ModelAdmin):
    list_display = ('course', 'user', 'added_by', 'created_at')
    search_fields = ('course__code', 'user__username')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('course', 'student', 'enrolled_at')
    search_fields = ('course__code', 'student__username')


class RubricCriterionInline(admin.TabularInline):
    model = RubricCriterion
    extra = 0


@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'title', 'updated_at')
    search_fields = ('assignment__title',)
    inlines = [RubricCriterionInline]


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'category', 'due_date', 'max_score', 'ai_auto_run')
    search_fields = ('title', 'course__code')
    list_filter = ('category', 'due_date', 'ai_auto_run')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'version', 'submission_type', 'submitted_at')
    search_fields = ('assignment__title', 'student__username')
    list_filter = ('submitted_at',)
    readonly_fields = ('version',)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('submission', 'score', 'instructor', 'is_published', 'graded_at')
    list_filter = ('is_published',)
    search_fields = ('submission__assignment__title', 'submission__student__username')


@admin.register(CriterionScore)
class CriterionScoreAdmin(admin.ModelAdmin):
    list_display = ('grade', 'criterion', 'points_awarded')
    search_fields = ('grade__submission__student__username',)


@admin.register(FeedbackAnnotation)
class FeedbackAnnotationAdmin(admin.ModelAdmin):
    list_display = ('grade', 'author', 'anchor', 'created_at')
    search_fields = ('grade__submission__student__username', 'body')

