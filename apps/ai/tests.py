from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.ai import inspector


class SubmissionFeedbackTests(SimpleTestCase):
    def setUp(self):
        self.assignment = SimpleNamespace(
            max_score=Decimal('100.00'),
            effective_max_score=Decimal('100.00'),
            rubric=None,
        )
        self.report = {
            'version': 2,
            'submission_type': 'archive',
            'file_count': 3,
            'source_file_count': 1,
            'doc_file_count': 1,
            'pdf_pages': 0,
            'has_readme': True,
            'issues': [
                {
                    'severity': 'warning',
                    'kind': 'missing_requirement',
                    'message': 'The assignment asks for a test file.',
                }
            ],
        }

    def test_local_feedback_is_written_for_students(self):
        result = inspector.local_suggestions(self.report, self.assignment)

        self.assertIn('What you did well', result['suggested_feedback'])
        self.assertIn('What to improve', result['suggested_feedback'])
        self.assertIn('Next steps', result['suggested_feedback'])
        self.assertIn('did not run your code, tests, or SQL', result['suggested_feedback'])
        self.assertTrue(result['feedback_sections']['strengths'])
        self.assertTrue(result['feedback_sections']['next_steps'])
        self.assertEqual(result['feedback_sections']['note'], inspector.FEEDBACK_NOTE)

    def test_structured_llm_feedback_is_normalised(self):
        data = {
            'summary': 'The files are mostly complete.',
            'suggested_score': 80,
            'suggested_feedback': {
                'overview': 'You included the main project files.',
                'strengths': ['The README explains the project.'],
                'improvements': ['Add the test file required by the assignment.'],
                'next_steps': ['Add a test file and check it before submitting again.'],
            },
            'criteria': [],
            'flags': [],
        }

        result, _ = inspector.merge_llm_result(
            self.report, self.assignment, data, 'fake-model'
        )

        self.assertIn('What you did well', result['suggested_feedback'])
        self.assertIn('Add a test file', result['suggested_feedback'])
        self.assertIn(inspector.FEEDBACK_NOTE, result['suggested_feedback'])
        self.assertEqual(
            result['feedback_sections']['strengths'],
            ['The README explains the project.'],
        )

    def test_legacy_string_llm_feedback_is_accepted(self):
        data = {
            'summary': 'The files are mostly complete.',
            'suggested_score': 80,
            'suggested_feedback': 'You included the main files. Add a test file next.',
            'criteria': [],
            'flags': [],
        }

        result, _ = inspector.merge_llm_result(
            self.report, self.assignment, data, 'fake-model'
        )

        self.assertIn('You included the main files.', result['suggested_feedback'])
        self.assertIn(inspector.FEEDBACK_NOTE, result['suggested_feedback'])
