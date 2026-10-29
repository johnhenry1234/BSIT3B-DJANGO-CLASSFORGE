# ClassForge Code Management System

ClassForge is a web-based Assignment and Digital Portfolio Management System with Integrated AI-Assisted Evaluation. It is designed for Information Technology education to centralize assignment submission, grading, and feedback delivery. It lets **instructors/teaching assistants** create courses and assignments, configure rubrics, grade submissions, and deliver feedback, while **students** upload their work in one structured platform. The system also includes an **AI Auto-Grader and Submission Inspector** that assists instructors by generating draft evaluations while keeping final grading decisions with the instructor.

## What it can do

- **Role-based access control** — supports Administrator, Instructor, Teaching Assistant, and Student roles with activity logs to ensure data confidentiality and integrity in compliance with the Data Privacy Act.
- **Courses** — instructors create courses with a unique code; students enroll.
- **Assignments with categories** — Code Project, ERD / Diagram, Database Design, Documentation, or Other, each with a due date, instructions, and max score.
- **Versioned submissions** — resubmitting creates a new, append-only submission version (v1, v2, ...), so no work is ever overwritten; late submissions are flagged. Accepts code archives (.zip) and PDF documentation.
- **Rubric-based grading** — instructors/ TAs use customizable rubrics via a split-screen grading interface. Grades and AI evaluations are stored independently per submission version and computed dynamically.
- **Feedback engine** — supports comments, annotations, and file attachments. Instructors control publishing of grades in batch.
- **Grade visibility** — students only see published grades and feedback on My Grades.
- **AI Auto-Grader and Submission Inspector** — processes submissions asynchronously against instructor-defined guidelines using background tasks (Celery/Redis), produces suggested rubric scores, feedback, and annotations in Draft Assistant mode, flags missing mandatory requirements, structural discrepancies, and code anomalies. AI suggestions are for review only; final grades remain with the instructor.
- **Dashboards** — role-aware stats for admins, instructors, TAs, and students.
- **User & Students Info management** — admin-only user list, per-user info records.
- **Digital portfolios & audit trail** — maintains organized, auditable records of submissions, grades, and feedback to support transparency and student portfolios.

## Project Objectives (Summary)

1. **Student Portal** — View active assignments, deadlines, instructions, and rubric weights; submit .zip or PDF files with preserved submission versions.
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
| **Accepted Submissions** | Original uploads: code archives (.zip) and PDF documentation. Project workspaces additionally accept directory snapshots from the web/API/VS Code extension. |
| **Target Users** | Students, Instructors, Teaching Assistants (TAs), and System Administrators of the BSIT program. |

### Limitations

- **Deployment** — Operates within an intranet/local network or hosted web server for the target institution.
- **AI as Assistive Tool** — AI suggestions (scores, feedback, flags) are subject to instructor review; final grades are determined by instructors.
- **AI Quality Dependency** — Quality depends on clarity of guidelines/prompts and LLM capability.
- **Submission Types** — Classic uploads remain .zip and PDF. Project workspaces also accept directory snapshots. Automated execution of submitted code is excluded in the current phase; test/code runner integration reports "not run" unless an isolated runner is configured.
- **Anomaly Scope** — Flags cover missing mandatory requirements, structural discrepancies, and code anomalies; no comparison against external online sources.
- **Integrations Excluded** — External LMS, online payment, and SMS gateway notifications are excluded in the current phase.

## Tech stack

- Backend: Django (Python)
- Database: MySQL / MariaDB (XAMPP) by default, SQLite for local dev and tests
- Task Queue: Celery with Redis (for async AI evaluation)
- AI: LLM pipeline for AI-assisted evaluation
- Frontend: Tabler UI + Bootstrap 5
- Project workflow: `apps.projects` (snapshots, local Git mirror, revisions, pull requests, assessments, notifications, API tokens)
- VS Code extension: TypeScript (`vscode-extension/`), Node built-in tests, no runtime npm dependencies
- Testing: pytest + pytest-django for Django; `node --test` for the extension
- Raw schema: [`SQL/classforge_db.sql`](SQL/classforge_db.sql) (mirrors the original Django models)

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

## Project workspaces, Git versioning, and automated assessment

ClassForge now also provides a full project-development workflow on top of the
original assignment submission system:

- **Project workspaces** for every student/assignment pair, with immutable,
  checksummed snapshots and a deterministic canonical archive.
- **Web, API, and VS Code submission** — upload a ZIP or a directory snapshot;
  `.classforgeignore`, assignment exclusions, secret filtering, path-traversal
  protection, and size/file limits are enforced server-side.
- **Server-owned Git mirror** — snapshots are committed locally (never
  executed); new versions, branches, and pull-request merges are tracked.
- **Rubric versions and staged assessment** — deterministic checks (required
  files/directories, formats, documentation, tests, risky patterns) produce an
  evidence-based draft; an optional AI provider creates a validated draft when
  configured. AI output is never a final grade.
- **Instructor review** — drafts are reviewed, overridden, rejected, or applied
  as an **unpublished** grade; publication remains an explicit instructor action.
- **Revision requests and pull requests** with comments, merge/close actions,
  notifications, audit events, and assessment queue retries.
- **Safe DB/ERD inspection** — SQLite files are opened read-only with an
  authorizer; SQL/ERD/documentation artifacts are inspected statically. Student
  code and SQL are never executed in the Django process.
- **VS Code extension** — token auth via SecretStorage, course/assignment
  selection, manifest preview, submission progress/errors, status/feedback, and
  local revision-branch creation.

Additional documentation:

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/api-v1.md`](docs/api-v1.md)
- [`docs/operations.md`](docs/operations.md)
- [`docs/vscode-extension.md`](docs/vscode-extension.md)

Configuration lives in environment variables; see
[`.env.example`](.env.example) and `docs/operations.md`. No AI key, Celery/Redis,
or sandboxed code runner is required for local development. Without an AI key
the deterministic inspector is used. Automated code/test execution stays
disabled and is reported as not run.

### Push and pull from VS Code

ClassForge does **not** expose a Git remote to VS Code. There is no `git push`
to ClassForge and no `git pull`/clone from it. In this system:

- **Push** = upload the current workspace as an immutable project snapshot.
- **Pull** = fetch the latest assessment status, feedback, and revision requests.

Use normal Git separately if you also want GitHub/GitLab push/pull.

1. **Start the ClassForge server** and sign in to the web app once to confirm
   your account works:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

2. **Install/run the VS Code extension.** For development:

   ```bash
   cd vscode-extension
   npm install
   npm run compile
   ```

   Open the `vscode-extension` folder in VS Code and press **F5**, or build and
   install the VSIX:

   ```bash
   npx @vscode/vsce package
   code --install-extension classforge-vscode-0.1.0.vsix
   ```

3. **Open your project folder in VS Code.** The extension submits the first
   workspace folder. Add a `.classforgeignore` if needed (secrets are always
   excluded regardless).

4. **Set the server URL** in VS Code settings if it is not the default:

   ```json
   "classforge.serverUrl": "http://localhost:8000"
   ```

5. **Sign in.** Open the Command Palette (`Ctrl+Shift+P`) and run:

   ```text
   ClassForge: Sign In
   ```

   Enter your ClassForge username/password. Only a server-issued token is saved,
   in VS Code SecretStorage.

6. **Select the course and assignment:**

   ```text
   ClassForge: Select Course
   ClassForge: Select Assignment
   ```

   The account must be enrolled and the assignment must be published.

7. **Preview the push (optional but recommended):**

   ```text
   ClassForge: Preview Submission Manifest
   ```

   This shows every file, its size/SHA-256, and why other files were excluded.

8. **Push the snapshot:**

   ```text
   ClassForge: Submit Project Snapshot
   ```

   Confirm the dialog, optionally add a note, and wait for the progress
   notification. The server stores an immutable version (`v1`, `v2`, …),
   optionally mirrors it to the server-owned Git repository, and optionally
   starts an assessment.

9. **Pull status/feedback:**

   ```text
   ClassForge: Check Assessment Status
   ClassForge: Show Feedback
   ```

   These open the latest snapshot status, rubric draft/feedback, and the
   published grade if the instructor has released one. The web dashboard is
   available with `ClassForge: Open Web Dashboard`.

10. **Handle revision requests:**

    ```text
    ClassForge: Create Revision Branch
    ```

    Select an open revision request; the extension creates and checks out a
    local branch (for example `revision/42-fix-erd`). Commit your changes
    locally, then run **Submit Project Snapshot** again to push a new snapshot.
    Open/review the pull request in the web UI.

| Action | VS Code command | What happens |
| --- | --- | --- |
| Push project | `ClassForge: Submit Project Snapshot` | Uploads files and creates a new immutable snapshot version. |
| Pull latest status | `ClassForge: Check Assessment Status` | Fetches the latest snapshot and assessment status. |
| Pull feedback | `ClassForge: Show Feedback` | Shows summary, rubric criteria, and published grade. |
| Pull revision work | `ClassForge: Create Revision Branch` | Lists open revision requests and creates a local branch. |
| Open system | `ClassForge: Open Web Dashboard` | Opens `/projects/` in the browser. |

**Not supported:** `git push` to ClassForge, `git pull`/clone snapshots back to
VS Code, or automatic branch push/PR creation. The server Git mirror is internal;
the source of truth for your code remains your local workspace.

## Run the tests

Backend tests use pytest + pytest-django:

```bash
pip install -r requirements-dev.txt
DB_ENGINE=sqlite .venv/Scripts/python.exe -m pytest -q
```

On macOS/Linux use `.venv/bin/python -m pytest -q`.

VS Code extension tests:

```bash
cd vscode-extension
npm install
npm test
```

`pytest.ini` configures the Django settings module. Prefer pytest over
`python manage.py test` in this repository: `apps` is a namespace package, which
makes Django's default test discovery unreliable.

## Team

- Cyrus Wheng Pagador
- John Henry Pabilona
- Cymone John Masilac
