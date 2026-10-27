#!/usr/bin/env python
import os
import sys
from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
execute_from_command_line(['manage.py', 'shell', '-c', r"""
from django.contrib.auth import get_user_model
from django.db import transaction, connection
from apps.core.models import ActivityLog
from apps.courses.models import (
    Course, CourseAssistant, Enrollment, Assignment, Submission, Rubric, RubricCriterion,
    Grade, CriterionScore, FeedbackAnnotation, AssignmentSeen
)
from apps.info.models import Info
from apps.portfolio.models import Portfolio, PortfolioItem
from apps.ai.models import AIEvaluation, AIFlag
from apps.users.models import UserProfile

User = get_user_model()
PRESERVE = {'cj1', 'cj', 'cjinstructor'}
to_delete_users = User.objects.exclude(username__in=PRESERVE)
print('Users to delete:', list(to_delete_users.values_list('username', flat=True)))
confirm = input('Type WIPE to confirm deletion of all data except preserved users: ')
if confirm.strip() != 'WIPE':
    print('Aborted')
    sys.exit(0)

with transaction.atomic():
    # Clear in dependency order
    CriterionScore.objects.all().delete()
    FeedbackAnnotation.objects.all().delete()
    Grade.objects.all().delete()
    AIFlag.objects.all().delete()
    AIEvaluation.objects.all().delete()
    RubricCriterion.objects.all().delete()
    Rubric.objects.all().delete()
    AssignmentSeen.objects.all().delete()
    Submission.objects.all().delete()
    Assignment.objects.all().delete()
    CourseAssistant.objects.all().delete()
    Enrollment.objects.all().delete()
    Course.objects.all().delete()
    PortfolioItem.objects.all().delete()
    Portfolio.objects.all().delete()
    Info.objects.exclude(user__username__in=PRESERVE).delete()
    ActivityLog.objects.all().delete()
    UserProfile.objects.exclude(user__username__in=PRESERVE).delete()
    to_delete_users.delete()

# Reset sequences if using sqlite/postgres/mysql
try:
    if connection.vendor == 'sqlite':
        with connection.cursor() as c:
            tables = [
                'activity_logs','courses','course_assistants','enrollments','assignments',
                'submissions','rubrics','rubric_criteria','grades','criterion_scores',
                'feedback_annotations','assignment_seen','portfolio','portfolio_items',
                'ai_evaluations','ai_conversations','info','user_profiles'
            ]
            for t in tables:
                try:
                    c.execute(f"DELETE FROM sqlite_sequence WHERE name='{t}'")
                except Exception:
                    pass
    elif connection.vendor == 'postgresql':
        with connection.cursor() as c:
            c.execute("SELECT setval(pg_get_serial_sequence('activity_logs','id'), 1, false);")
            # Add more as needed if using serials
    # MySQL - truncate resets auto_increment
except Exception as e:
    print('Sequence reset warning:', e)

print('Done. Preserved:', list(User.objects.filter(username__in=PRESERVE).values_list('username', flat=True)))
"""])
