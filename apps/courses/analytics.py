"""Read-time grading aggregations.

Nothing in this module stores a class average or a rubric total.  Every value
is derived from ``Grade`` / ``CriterionScore`` rows so that edits to a grade
or rubric are reflected immediately, matching the decoupled architecture in
the concept paper.
"""

from decimal import Decimal

from django.db.models import Avg, DecimalField, ExpressionWrapper, F, Max, Subquery

from .models import Grade, Submission

PERCENT_FIELD = DecimalField(max_digits=7, decimal_places=2)


def latest_submission_ids():
    """IDs of the newest submission version per (assignment, student)."""
    return (
        Submission.objects.values('assignment_id', 'student_id')
        .annotate(latest_id=Max('id'))
        .values('latest_id')
    )


def latest_submissions(*, course=None, student=None):
    qs = Submission.objects.filter(id__in=Subquery(latest_submission_ids()))
    if course is not None:
        qs = qs.filter(assignment__course=course)
    if student is not None:
        qs = qs.filter(student=student)
    return qs


def published_latest_grades(*, course=None, student=None):
    """Published grades attached to the latest version of each submission."""
    qs = Grade.objects.filter(
        is_published=True,
        submission_id__in=Subquery(latest_submission_ids()),
    )
    if course is not None:
        qs = qs.filter(submission__assignment__course=course)
    if student is not None:
        qs = qs.filter(submission__student=student)
    return qs.select_related(
        'submission__assignment__course', 'submission__student'
    ).annotate(
        percent=ExpressionWrapper(
            100.0 * F('score') / F('submission__assignment__max_score'),
            output_field=PERCENT_FIELD,
        )
    )


def course_average(course):
    value = published_latest_grades(course=course).aggregate(avg=Avg('percent'))['avg']
    return _round(value)


def assignment_average(assignment):
    value = (
        published_latest_grades(course=assignment.course)
        .filter(submission__assignment=assignment)
        .aggregate(avg=Avg('percent'))['avg']
    )
    return _round(value)


def student_average(student):
    value = published_latest_grades(student=student).aggregate(
        avg=Avg('percent')
    )['avg']
    return _round(value)


def student_performance(student):
    grades = list(published_latest_grades(student=student))
    total = len(grades)
    passing = sum(1 for g in grades if g.percent is not None and g.percent >= 60)
    return {
        'published_count': total,
        'average': _round(
            (sum((g.percent or Decimal('0')) for g in grades) / total)
            if total
            else None
        ),
        'passing': passing,
        'pass_rate': _round((Decimal(passing) / Decimal(total)) * 100) if total else None,
    }


def _round(value):
    if value is None:
        return None
    return Decimal(value).quantize(Decimal('0.01'))
