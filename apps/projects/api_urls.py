from django.urls import path

from . import api

app_name = 'projects_api'

urlpatterns = [
    path('health/', api.health, name='health'),
    path('auth/token/', api.token_create, name='token_create'),
    path('auth/tokens/', api.token_list, name='token_list'),
    path('auth/tokens/<int:pk>/revoke/', api.token_revoke, name='token_revoke'),
    path('me/', api.me, name='me'),
    path('courses/', api.courses, name='courses'),
    path('assignments/', api.assignments, name='assignments'),
    path('assignments/<int:pk>/', api.assignment_detail, name='assignment_detail'),
    path('assignments/<int:pk>/submit/', api.assignment_submit, name='assignment_submit'),
    path('projects/', api.project_list, name='project_list'),
    path('projects/<int:pk>/', api.project_detail, name='project_detail'),
    path('projects/<int:project_id>/snapshots/', api.snapshot_list, name='snapshot_list'),
    path('projects/<int:project_id>/revisions/', api.revision_list_by_project, name='revision_list_by_project'),
    path('projects/<int:project_id>/revisions/new/', api.revision_create, name='revision_create'),
    path('projects/<int:project_id>/pull-requests/', api.pull_request_list, name='pull_request_list'),
    path('projects/<int:project_id>/pull-requests/new/', api.pull_request_create, name='pull_request_create'),
    path('snapshots/<int:pk>/', api.snapshot_detail, name='snapshot_detail'),
    path('snapshots/<int:pk>/status/', api.snapshot_status, name='snapshot_status'),
    path('snapshots/<int:pk>/feedback/', api.snapshot_feedback, name='snapshot_feedback'),
    path('snapshots/<int:pk>/diff/', api.snapshot_diff, name='snapshot_diff'),
    path('snapshots/<int:pk>/assess/', api.snapshot_assess, name='snapshot_assess'),
    path('revisions/', api.revision_list, name='revision_list'),
    path('revisions/<int:pk>/', api.revision_update, name='revision_update'),
    path('pull-requests/', api.pull_request_global_list, name='pull_request_global_list'),
    path('pull-requests/<int:pk>/action/', api.pull_request_action, name='pull_request_action'),
    path('notifications/', api.notification_list, name='notification_list'),
    path('notifications/<int:pk>/read/', api.notification_read, name='notification_read'),
]
