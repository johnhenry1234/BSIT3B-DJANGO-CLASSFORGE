from django.urls import path

from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('tokens/', views.token_manage, name='token_manage'),
    path('assessments/', views.assessment_queue, name='assessment_queue'),
    path('assessments/<int:pk>/review/', views.assessment_review, name='assessment_review'),
    path('assessments/<int:pk>/retry/', views.assessment_retry, name='assessment_retry'),
    path('snapshots/<int:pk>/', views.snapshot_detail, name='snapshot_detail'),
    path('snapshots/<int:pk>/assess/', views.snapshot_assess, name='snapshot_assess'),
    path('snapshots/<int:pk>/compare/', views.snapshot_compare, name='snapshot_compare'),
    path('pull-requests/<int:pk>/', views.pull_request_detail, name='pull_request_detail'),
    path('create/<int:assignment_pk>/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:project_pk>/revisions/new/', views.revision_create, name='revision_create'),
    path('revisions/<int:pk>/update/', views.revision_update, name='revision_update'),
    path('<int:project_pk>/pull-requests/new/', views.pull_request_create, name='pull_request_create'),
]
