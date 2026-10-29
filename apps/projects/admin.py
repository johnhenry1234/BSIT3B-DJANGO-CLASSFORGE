from django.contrib import admin

from .models import (
    ApiToken,
    Assessment,
    CriterionAssessment,
    Notification,
    Project,
    ProjectSnapshot,
    PullRequest,
    PullRequestComment,
    Repository,
    RevisionRequest,
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment', 'student', 'status', 'updated_at')
    list_filter = ('status',)
    search_fields = ('assignment__title', 'student__username', 'title')


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('project', 'current_branch', 'git_initialised', 'last_commit_sha')
    list_filter = ('git_initialised',)
    search_fields = ('project__title', 'project__student__username')


@admin.register(ProjectSnapshot)
class ProjectSnapshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'version', 'source', 'file_count', 'created_at')
    list_filter = ('source',)
    search_fields = ('project__title', 'checksum', 'commit_sha')
    readonly_fields = ('checksum', 'manifest', 'validation')


@admin.register(RevisionRequest)
class RevisionRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'requested_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'project__student__username')


@admin.register(PullRequest)
class PullRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'project', 'status', 'source_branch', 'target_branch')
    list_filter = ('status',)
    search_fields = ('title', 'project__student__username')


@admin.register(PullRequestComment)
class PullRequestCommentAdmin(admin.ModelAdmin):
    list_display = ('pull_request', 'author', 'created_at')


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'snapshot', 'status', 'engine', 'overall_score', 'max_score',
        'review_status', 'requires_review', 'created_at',
    )
    list_filter = ('status', 'engine', 'review_status', 'requires_review')
    search_fields = (
        'snapshot__project__title',
        'snapshot__project__student__username',
        'model_name',
    )
    readonly_fields = ('validation', 'checks', 'structure', 'artifacts', 'evidence')


@admin.register(CriterionAssessment)
class CriterionAssessmentAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'criterion_name', 'ai_points', 'instructor_points', 'max_points')
    search_fields = ('criterion_name',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'kind', 'title', 'read_at', 'created_at')
    list_filter = ('kind',)
    search_fields = ('user__username', 'title')


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'prefix', 'created_at', 'expires_at', 'revoked_at')
    list_filter = ('revoked_at',)
    search_fields = ('user__username', 'name', 'prefix')
    readonly_fields = ('token_hash', 'prefix')
