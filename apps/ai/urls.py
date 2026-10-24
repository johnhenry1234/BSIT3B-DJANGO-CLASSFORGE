from django.urls import path

from . import views

app_name = 'ai'

urlpatterns = [
    path(
        'submissions/<int:submission_pk>/run/',
        views.run_evaluation_view,
        name='run_evaluation',
    ),
    path(
        'assignments/<int:assignment_pk>/run/',
        views.run_assignment_view,
        name='run_assignment',
    ),
    path(
        'evaluations/<int:pk>/apply/',
        views.apply_evaluation_view,
        name='apply_evaluation',
    ),
]
