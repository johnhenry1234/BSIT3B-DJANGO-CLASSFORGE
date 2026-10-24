from django.conf import settings
from django.db import models


class Portfolio(models.Model):
    VISIBILITY_PRIVATE = 'private'
    VISIBILITY_CLASS = 'class'
    VISIBILITY_PUBLIC = 'public'
    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, 'Private'),
        (VISIBILITY_CLASS, 'Class'),
        (VISIBILITY_PUBLIC, 'Public'),
    ]

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name='portfolio',
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=255, default='My Portfolio')
    bio = models.TextField(blank=True, default='')
    visibility = models.CharField(
        max_length=16, choices=VISIBILITY_CHOICES, default=VISIBILITY_PRIVATE
    )
    share_slug = models.SlugField(max_length=64, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'portfolios'
        ordering = ['student__username']

    def __str__(self):
        return f'{self.student} portfolio'


class PortfolioItem(models.Model):
    ITEM_ASSIGNMENT = 'assignment'
    ITEM_PROJECT = 'project'
    ITEM_CERTIFICATION = 'certification'
    ITEM_OTHER = 'other'
    ITEM_CHOICES = [
        (ITEM_ASSIGNMENT, 'Assignment'),
        (ITEM_PROJECT, 'Project'),
        (ITEM_CERTIFICATION, 'Certification'),
        (ITEM_OTHER, 'Other'),
    ]

    portfolio = models.ForeignKey(
        Portfolio, related_name='items', on_delete=models.CASCADE
    )
    grade = models.ForeignKey(
        'courses.Grade',
        related_name='portfolio_items',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    item_type = models.CharField(max_length=20, choices=ITEM_CHOICES, default=ITEM_ASSIGNMENT)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    reflection = models.TextField(blank=True, default='')
    skills = models.CharField(max_length=512, blank=True, default='')
    link = models.URLField(max_length=500, blank=True, default='')
    file_attachment = models.FileField(
        upload_to='portfolio/%Y/%m/', max_length=255, blank=True, null=True
    )
    is_featured = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'portfolio_items'
        ordering = ['position', '-created_at']

    def __str__(self):
        return self.title
