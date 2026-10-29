from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.courses.models import Assignment, Course, Enrollment, Submission
from apps.info.models import Info
from apps.projects.models import Project

User = get_user_model()


class StudentsInfoTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='teacher', password='secret1234', is_staff=True
        )
        self.other_instructor = User.objects.create_user(
            username='other-teacher', password='secret1234', is_staff=True
        )
        self.student = User.objects.create_user(
            username='learner', password='secret1234',
            first_name='Ada', last_name='Lovelace',
        )
        self.course = Course.objects.create(
            name='Capstone', code='CAP101', instructor=self.instructor
        )
        Enrollment.objects.create(course=self.course, student=self.student)
        Info.objects.create(
            user=self.student,
            name='Ada Lovelace',
            id_number='2026-0001',
            age=20,
            address='Manila',
            email='ada@example.com',
        )
        self.assignment = Assignment.objects.create(
            course=self.course,
            title='Database design',
            due_date=timezone.now() + timezone.timedelta(days=7),
            max_score=Decimal('100.00'),
            status=Assignment.STATUS_PUBLISHED,
        )
        Submission.objects.create(
            assignment=self.assignment,
            student=self.student,
            text_content='Schema and documentation.',
        )
        Project.objects.create(assignment=self.assignment, student=self.student)

    def test_instructor_can_open_students_info_page(self):
        self.client.force_login(self.instructor)
        response = self.client.get(reverse('info:info_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ada Lovelace')
        self.assertContains(response, reverse('info:student_detail', args=[self.student.pk]))

    def test_instructor_can_open_student_detail(self):
        self.client.force_login(self.instructor)
        response = self.client.get(
            reverse('info:student_detail', args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ada Lovelace')
        self.assertContains(response, '2026-0001')
        self.assertContains(response, 'Database design')
        self.assertContains(response, 'CAP101')

    def test_unrelated_instructor_cannot_open_student_detail(self):
        self.client.force_login(self.other_instructor)
        response = self.client.get(
            reverse('info:student_detail', args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_open_instructor_student_detail(self):
        self.client.force_login(self.student)
        response = self.client.get(
            reverse('info:student_detail', args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 403)
