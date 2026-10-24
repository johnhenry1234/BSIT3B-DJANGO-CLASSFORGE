from django.contrib import admin

from .models import AIEvaluation, AIFlag


class AIFlagInline(admin.TabularInline):
    model = AIFlag
    extra = 0
    can_delete = False
    readonly_fields = ('kind', 'severity', 'message', 'evidence', 'created_at')


@admin.register(AIEvaluation)
class AIEvaluationAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'status', 'suggested_score', 'applied_at', 'created_at')
    list_filter = ('status', 'mode')
    search_fields = ('submission__assignment__title', 'submission__student__username')
    readonly_fields = (
        'submission', 'requested_by', 'status', 'model_name', 'suggested_score',
        'suggested_feedback', 'summary', 'suggested_criteria', 'inspection',
        'raw_response', 'error', 'created_at', 'started_at', 'completed_at',
        'applied_by', 'applied_at',
    )
    inlines = [AIFlagInline]

    def has_add_permission(self, request):
        return False


@admin.register(AIFlag)
class AIFlagAdmin(admin.ModelAdmin):
    list_display = ('evaluation', 'kind', 'severity', 'message')
    list_filter = ('kind', 'severity')
    search_fields = ('message', 'evaluation__submission__student__username')
