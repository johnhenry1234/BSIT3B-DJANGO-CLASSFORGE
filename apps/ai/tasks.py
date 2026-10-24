"""Optional Celery task wrappers.

Celery is an optional dependency.  If it is installed, these functions become
shared tasks; otherwise importing this module leaves plain callables that the
service layer invokes inline or in a thread.
"""

try:  # pragma: no cover - depends on the deployment environment
    from celery import shared_task
except Exception:  # pragma: no cover
    shared_task = None

from .services import run_evaluation


if shared_task is not None:  # pragma: no cover - requires Celery installed

    @shared_task(name='classforge.ai.evaluate_submission')
    def evaluate_submission_task(evaluation_id):
        return run_evaluation(evaluation_id)

else:

    def evaluate_submission_task(evaluation_id):
        return run_evaluation(evaluation_id)
