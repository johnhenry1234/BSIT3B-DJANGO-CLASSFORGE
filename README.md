# ClassForge Code Management System

ClassForge is a web-based system built for Information Technology courses. It lets
**instructors** create courses and assignments (code projects, ERDs, database designs,
documentation), and lets **students** upload their work online — so teachers can check
everyone's submissions in one place instead of going through laptops one by one.

## What it can do

- **Role-based accounts** — sign up as a Student or Instructor (ID number, age, and
  address are required at registration and saved to Students Info).
- **Courses** — instructors create courses with a unique code; students enroll.
- **Assignments with categories** — Code Project, ERD / Diagram, Database Design,
  Documentation, or Other, each with a due date and max score.
- **Versioned submissions** — resubmitting creates a new version (v1, v2, …), so no
  work is ever overwritten; late submissions are flagged.
- **Grading** — instructors grade each submission version with score + feedback and
  choose when to publish it; students only see published grades on My Grades.
- **Dashboards** — role-aware stats for admins, instructors, and students.
- **User & Students Info management** - admin-only user list, per-user info records.

## Tech stack

- Backend: Django (Python)
- Database: MySQL / MariaDB (XAMPP) by default, SQLite for local dev and tests
- Frontend: Tabler UI + Bootstrap 5
- Raw schema: [`SQL/classforge_db.sql`](SQL/classforge_db.sql) (mirrors the Django models)

## Run it locally

```bash
pip install -r requirements.txt

# With MySQL (default): create the DB, set credentials via
# DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT, then:
python manage.py migrate

# Or with SQLite (no MySQL needed):
DB_ENGINE=sqlite python manage.py migrate

python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign in, or create an account (choose Student or
Instructor on the signup page).

## Run the tests

```bash
DB_ENGINE=sqlite python manage.py test apps.core
DB_ENGINE=sqlite python manage.py test apps.courses
```

## Team

- Cyrus Wheng Pagador
- John Henry Pabilona
- Cymone John Masilac
