"""Celery task entry points for the assessment pipeline.

Celery is optional.  The tasks are only imported when
``ASSESSMENT_DISPATCH_MODE=celery``; without Celery the messenger falls back to
inline or threaded execution.
"""

from __future__ import annotations

try:  # pragma: no cover - Celery is an optional deployment dependency
    from celery import shared_task
except Exception:  # pragma: no cover
    shared_task = None


def _run(assessment_id):
    from .assessment import run_assessment

    return run_assessment(assessment_id)


if shared_task is not None:  # pragma: no cover - exercised only with Celery

    @shared_task(bind=True, max_retries=3, default_retry_delay=30)
    def run_assessment_task(self, assessment_id):
        from .models import Assessment

        assessment = Assessment.objects.filter(pk=assessment_id).first()
        if assessment is None or assessment.status == Assessment.STATUS_COMPLETED:
            return assessment_id
        result = _run(assessment_id)
        if (
            result is not None
            and result.status == Assessment.STATUS_FAILED
            and self.request.retries < self.max_retries
        ):
            raise self.retry(exc=RuntimeError(result.error or 'assessment failed'))
        return assessment_id

else:  # pragma: no cover - local development without Celery

    def run_assessment_task(assessment_id):
        return _run(assessment_id)
