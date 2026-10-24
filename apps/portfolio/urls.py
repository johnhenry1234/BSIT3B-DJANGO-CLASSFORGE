from django.urls import path

from . import views

app_name = 'portfolio'

urlpatterns = [
    path('', views.my_portfolio, name='my_portfolio'),
    path('visibility/', views.toggle_visibility, name='toggle_visibility'),
    path('add/<int:grade_pk>/', views.add_from_grade, name='add_from_grade'),
    path('feature/<int:pk>/', views.feature_toggle, name='feature_toggle'),
]
