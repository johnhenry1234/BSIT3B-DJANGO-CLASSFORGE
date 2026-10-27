from django.urls import path

from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('create/', views.course_create, name='course_create'),
    path('my-grades/', views.my_grades, name='my_grades'),
    path('history/', views.student_history, name='student_history'),
    path('grading-queue/', views.grading_queue, name='grading_queue'),
    path('audit/', views.audit_log, name='audit_log'),
    path('<int:pk>/', views.course_detail, name='course_detail'),
    path('<int:pk>/edit/', views.course_update, name='course_update'),
    path('<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('<int:pk>/enroll/', views.course_enroll, name='course_enroll'),
    path('<int:pk>/unenroll/', views.course_unenroll, name='course_unenroll'),
    path('<int:pk>/assistants/', views.manage_assistants, name='manage_assistants'),
    path(
        '<int:course_pk>/assignments/create/',
        views.assignment_create,
        name='assignment_create',
    ),
    path(
        'assignments/<int:pk>/',
        views.assignment_detail,
        name='assignment_detail',
    ),
    path(
        'assignments/<int:pk>/edit/',
        views.assignment_update,
        name='assignment_update',
    ),
    path(
        'assignments/<int:pk>/delete/',
        views.assignment_delete,
        name='assignment_delete',
    ),
    path(
        'assignments/<int:pk>/rubric/',
        views.assignment_rubric,
        name='assignment_rubric',
    ),
    path(
        'assignments/<int:pk>/submit/',
        views.submission_create,
        name='submission_create',
    ),
    path(
        'submissions/<int:pk>/grade/',
        views.submission_grade,
        name='submission_grade',
    ),
    path(
        'grades/<int:pk>/publish-toggle/',
        views.grade_publish_toggle,
        name='grade_publish_toggle',
    ),
    path(
        'grades/<int:pk>/publish/',
        views.grade_publish,
        name='grade_publish',
    ),
    path(
        'grades/<int:pk>/unpublish/',
        views.grade_unpublish,
        name='grade_unpublish',
    ),
    path(
        'grades/publish-batch/',
        views.grade_publish_batch,
        name='grade_publish_batch',
    ),
    path(
        'submissions/<int:pk>/annotations/add/',
        views.add_annotation,
        name='add_annotation',
    ),
    path('assignments/<int:pk>/mark-seen/', views.mark_assignment_seen, name='mark_assignment_seen'),
    path('dashboard/submit/<int:pk>/', views.dashboard_submit, name='dashboard_submit'),
]
