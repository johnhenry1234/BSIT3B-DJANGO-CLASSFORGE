from django.urls import path

from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('create/', views.course_create, name='course_create'),
    path('my-grades/', views.my_grades, name='my_grades'),
    path('<int:pk>/', views.course_detail, name='course_detail'),
    path('<int:pk>/edit/', views.course_update, name='course_update'),
    path('<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('<int:pk>/enroll/', views.course_enroll, name='course_enroll'),
    path('<int:pk>/unenroll/', views.course_unenroll, name='course_unenroll'),
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
]
