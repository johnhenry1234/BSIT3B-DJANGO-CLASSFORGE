"""Run queued AI evaluations from the command line.

Useful when ``AI_EVALUATION_MODE = 'celery'`` is configured but a worker has
not processed the queue yet, or for scheduled catch-up runs.
"""

from django.core.management.base import BaseCommand

from apps.ai.models import AIEvaluation
from apps.ai.services import run_evaluation


class Command(BaseCommand):
    help = 'Process queued ClassForge AI evaluations.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit', type=int, default=50, help='Maximum evaluations to process.'
        )

    def handle(self, *args, **options):
        queryset = AIEvaluation.objects.filter(
            status__in=(AIEvaluation.STATUS_QUEUED, AIEvaluation.STATUS_RUNNING)
        ).order_by('created_at')[: options['limit']]
        processed = 0
        for evaluation in queryset:
            result = run_evaluation(evaluation.id)
            processed += 1
            self.stdout.write(
                f'Evaluation {evaluation.id}: {result.status if result else "missing"}'
            )
        self.stdout.write(self.style.SUCCESS(f'Processed {processed} evaluation(s).'))
