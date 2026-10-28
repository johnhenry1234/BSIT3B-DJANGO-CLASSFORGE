# ClassForge Code Management System

ClassForge is a web-based Assignment and Digital Portfolio Management System with Integrated AI-Assisted Evaluation. It is designed for Information Technology education to centralize assignment submission, grading, and feedback delivery. It lets **instructors/teaching assistants** create courses and assignments, configure rubrics, grade submissions, and deliver feedback, while **students** upload their work in one structured platform. The system also includes an **AI Auto-Grader and Submission Inspector** that assists instructors by generating draft evaluations while keeping final grading decisions with the instructor.

## What it can do

- **Role-based access control** — supports Administrator, Instructor, Teaching Assistant, and Student roles with activity logs to ensure data confidentiality and integrity in compliance with the Data Privacy Act.
- **Courses** — instructors create courses with a unique code; students enroll.
- **Assignments with categories** — Code Project, ERD / Diagram, Database Design, Documentation, or Other, each with a due date, instructions, and max score.
- **Versioned submissions** — resubmitting creates a new, append-only submission version (v1, v2, ...), so no work is ever overwritten; late submissions are flagged. Accepts code archives (.zip), PDF documentation, and GitHub repository links.
- **Rubric-based grading** — instructors/ TAs use customizable rubrics via a split-screen grading interface. Grades and AI evaluations are stored independently per submission version and computed dynamically.
- **Feedback engine** — supports comments, annotations, and file attachments. Instructors control publishing of grades in batch.
- **Grade visibility** — students only see published grades and feedback on My Grades.
- **AI Auto-Grader and Submission Inspector** — processes submissions asynchronously against instructor-defined guidelines using background tasks (Celery/Redis), produces suggested rubric scores, feedback, and annotations in Draft Assistant mode, flags missing mandatory requirements, structural discrepancies, and code anomalies. AI suggestions are for review only; final grades remain with the instructor.
- **Dashboards** — role-aware stats for admins, instructors, TAs, and students.
- **User & Students Info management** — admin-only user list, per-user info records.
- **Digital portfolios & audit trail** — maintains organized, auditable records of submissions, grades, and feedback to support transparency and student portfolios.

## Project Objectives (Summary)

1. **Student Portal** — View active assignments, deadlines, instructions, and rubric weights; submit .zip, PDF, or GitHub repo links with preserved submission versions.
2. **Instructor/TA Portal** — Filterable submission queue, split-screen grading with customizable rubrics, feedback engine, and batch grade publishing.
3. **AI Auto-Grader & Submission Inspector** — Async processing, draft suggestions, and anomaly flagging (missing requirements, structural discrepancies, code anomalies).
4. **Decoupled Architecture** — Grades and AI evaluations stored independently per submission version; class averages/final grades/rubric totals computed dynamically via DB aggregations.
5. **Role-based Access Control & Audit Logs** — Ensure data confidentiality/integrity in compliance with the Data Privacy Act.
6. **User Acceptance Testing (UAT)** — Evaluate usability, performance, and operational efficiency.

## Significance

- **Students** — Organized submissions, version tracking, rubric-based feedback with inline commentary once published.
- **Instructors & TAs** — Less time on collection/repetitive checks, consistent grading via rubrics, review AI-prepared drafts.
- **Academic Department/Institution** — Auditable record of submissions/grades/feedback supporting transparency and student portfolios.
- **Future Researchers/Students** — Reference framework for web-based learning management and AI-assisted assessment.

## Alignment

- **Institutional Research Agenda** — Information Technology and Education Innovation (web technologies + AI to improve assessment/feedback).
- **SDG 4 (Quality Education)** — Timely, rubric-based feedback and more consistent assessment.
- **SDG 9 (Industry, Innovation, and Infrastructure)** — Innovation in academic infrastructure through web-based systems and AI-assisted evaluation.

## Scope and Limitations

### Scope & Technical Architecture

| Component | Description & Coverage |
|-----------|------------------------|
| **Core Modules** | Student Portal (Assignment Feed, Submission Engine, Grade & Feedback Viewer); Instructor/TA Portal (Submission Queue, Split-Screen Grading, Feedback Engine, Grade Release Control); AI Auto-Grader & Submission Inspector (Guideline/Prompt Config, Draft Assistant Mode, Anomaly Flagging); System Activity Audit Trail. |
| **Architecture** | Non-transactional, decoupled design. Re-submissions stored as append-only `SubmissionVersion`. Grades and AI evaluations stored independently per `SubmissionVersion`. Class averages, final grades, rubric totals computed dynamically via Django ORM aggregations. |
| **Technology Stack** | Python/Django backend, MySQL/PostgreSQL (or SQLite), Celery with Redis for async tasks, LLM pipeline for AI evaluation, HTML5/CSS3/JavaScript/Bootstrap frontend. |
| **Accepted Submissions** | Code archives (.zip), PDF documentation, and GitHub repository links. |
| **Target Users** | Students, Instructors, Teaching Assistants (TAs), and System Administrators of the BSIT program. |

### Limitations

- **Deployment** — Operates within an intranet/local network or hosted web server for the target institution.
- **AI as Assistive Tool** — AI suggestions (scores, feedback, flags) are subject to instructor review; final grades are determined by instructors.
- **AI Quality Dependency** — Quality depends on clarity of guidelines/prompts and LLM capability.
- **Submission Types** — Limited to .zip, PDF, and GitHub repo links. Automated execution of submitted code is excluded in the current phase.
- **Anomaly Scope** — Flags cover missing mandatory requirements, structural discrepancies, and code anomalies; no comparison against external online sources.
- **Integrations Excluded** — External LMS, online payment, and SMS gateway notifications are excluded in the current phase.

## Tech stack

- Backend: Django (Python)
- Database: MySQL / MariaDB (XAMPP) by default, SQLite for local dev and tests
- Task Queue: Celery with Redis (for async AI evaluation)
- AI: LLM pipeline for AI-assisted evaluation
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

Open http://127.0.0.1:8000/ and sign in, or create an account (choose Student or Instructor on the signup page).

## Run the tests

```bash
DB_ENGINE=sqlite python manage.py test apps.core
DB_ENGINE=sqlite python manage.py test apps.courses
```

## Team

- Cyrus Wheng Pagador
- John Henry Pabilona
- Cymone John Masilac
