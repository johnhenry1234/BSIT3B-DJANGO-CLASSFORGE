from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_renders_for_authenticated_user(self):
        user = get_user_model().objects.create_user(username='admin', password='secret1234')

        self.client.force_login(user)
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_home_requires_login(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 302)


class RegisterRoleTests(TestCase):
    def _register(self, username, role, **overrides):
        data = {
            'username': username,
            'first_name': 'Test',
            'last_name': 'User',
            'email': f'{username}@example.com',
            'password': 'StrongPass123!',
            'confirm_password': 'StrongPass123!',
            'role': role,
            'id_number': f'ID-{username}',
            'age': '20',
            'address': 'Sample Street',
        }
        data.update(overrides)
        return self.client.post(reverse('register'), data)

    def test_student_signup_is_not_staff(self):
        response = self._register('stu1', 'student')

        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username='stu1')
        self.assertFalse(user.is_staff)

    def test_instructor_signup_is_staff(self):
        response = self._register('ins1', 'instructor')

        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username='ins1')
        self.assertTrue(user.is_staff)

    def test_default_role_is_student_when_missing(self):
        data = {
            'username': 'stu2',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'stu2@example.com',
            'password': 'StrongPass123!',
            'confirm_password': 'StrongPass123!',
            'id_number': 'ID-stu2',
            'age': '19',
            'address': 'Default Road',
        }
        response = self.client.post(reverse('register'), data)

        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username='stu2')
        self.assertFalse(user.is_staff)

    def test_invalid_role_is_rejected(self):
        response = self._register('bad1', 'admin')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(username='bad1').exists()
        )


class RegisterProfileTests(TestCase):
    def _base_data(self, username='prof1'):
        return {
            'username': username,
            'first_name': 'Pro',
            'last_name': 'File',
            'email': f'{username}@example.com',
            'password': 'StrongPass123!',
            'confirm_password': 'StrongPass123!',
            'role': 'student',
            'id_number': f'ID-{username}',
            'age': '21',
            'address': 'Profile Ave',
        }

    def test_signup_creates_info_record(self):
        from apps.info.models import Info

        response = self.client.post(reverse('register'), self._base_data())

        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username='prof1')
        info = Info.objects.get(user=user)
        self.assertEqual(info.id_number, 'ID-prof1')
        self.assertEqual(info.age, 21)
        self.assertEqual(info.address, 'Profile Ave')
        self.assertEqual(info.email, 'prof1@example.com')

    def test_missing_profile_fields_rejected(self):
        for field in ('id_number', 'age', 'address'):
            data = self._base_data(username=f'miss_{field}')
            data[field] = ''
            response = self.client.post(reverse('register'), data)

            self.assertEqual(response.status_code, 200)
            self.assertFalse(
                get_user_model().objects.filter(
                    username=f'miss_{field}'
                ).exists()
            )

    def test_invalid_age_rejected(self):
        for bad_age in ('abc', '0', '151'):
            data = self._base_data(username=f'age_{bad_age}')
            data['age'] = bad_age
            data['id_number'] = f'ID-age-{bad_age}'
            response = self.client.post(reverse('register'), data)

            self.assertEqual(response.status_code, 200)
            self.assertFalse(
                get_user_model().objects.filter(
                    username=f'age_{bad_age}'
                ).exists()
            )

    def test_duplicate_id_number_rejected(self):
        from apps.info.models import Info

        self.client.post(reverse('register'), self._base_data('dup1'))
        self.client.logout()
        data = self._base_data('dup2')
        data['id_number'] = 'ID-dup1'
        response = self.client.post(reverse('register'), data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(username='dup2').exists()
        )
        self.assertEqual(Info.objects.filter(id_number='ID-dup1').count(), 1)
