from django.contrib import admin

from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor', 'action', 'entity_type', 'entity_id', 'description')
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('actor__username', 'action', 'description', 'entity_id')
    readonly_fields = (
        'actor', 'action', 'entity_type', 'entity_id', 'description',
        'ip_address', 'user_agent', 'metadata', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
