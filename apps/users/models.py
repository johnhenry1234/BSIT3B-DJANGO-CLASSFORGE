"""ClassForge role profile.

Roles are stored in a one-to-one ``UserProfile`` so the built-in Django
``User`` model stays untouched.  Users created before this model existed are
still supported: :mod:`apps.users.roles` falls back to ``is_superuser`` and
``is_staff`` when no profile row is present.
"""

from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    ROLE_ADMIN = 'admin'
    ROLE_INSTRUCTOR = 'instructor'
    ROLE_TA = 'ta'
    ROLE_STUDENT = 'student'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Administrator'),
        (ROLE_INSTRUCTOR, 'Instructor'),
        (ROLE_TA, 'Teaching Assistant'),
        (ROLE_STUDENT, 'Student'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name='classforge_profile',
        on_delete=models.CASCADE,
    )
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'
        ordering = ['user__username']

    def __str__(self):
        return f'{self.user} ({self.get_role_display()})'
