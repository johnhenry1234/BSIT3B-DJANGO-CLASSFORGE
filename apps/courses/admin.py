from django.contrib import admin

from .models import Assignment, Course, Enrollment, Grade, Submission


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'instructor', 'created_at')
    search_fields = ('code', 'name', 'instructor__username')
    list_filter = ('created_at',)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('course', 'student', 'enrolled_at')
    search_fields = ('course__code', 'student__username')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'category', 'due_date', 'max_score')
    search_fields = ('title', 'course__code')
    list_filter = ('category', 'due_date')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'version', 'submitted_at')
    search_fields = ('assignment__title', 'student__username')
    list_filter = ('submitted_at',)
    readonly_fields = ('version',)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('submission', 'score', 'instructor', 'is_published', 'graded_at')
    list_filter = ('is_published',)
    search_fields = ('submission__assignment__title', 'submission__student__username')
