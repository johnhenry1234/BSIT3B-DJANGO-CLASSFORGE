# ClassForge Code Management System

ClassForge is a web-based Assignment and Digital Portfolio Management System with Integrated AI-Assisted Evaluation. It is designed for Information Technology education to centralize assignment submission, grading, and feedback delivery. It lets **teachers/teaching assistants** create courses and assignments, set up grading checklists, grade submissions, and share feedback, while **students** upload their work in one structured platform. The system also includes **AI feedback and automatic checks** that help teachers by preparing draft feedback while keeping final grading decisions with the teacher.

## What it can do

- **Role-based access control** — supports Administrator, Teacher, Teaching Assistant, and Student roles with activity history to ensure data confidentiality and integrity in compliance with the Data Privacy Act.
- **Courses** — teachers create courses with a unique code; students join.
- **Assignments with categories** — Code Project, ERD / Diagram, Database Design, Documentation, or Other, each with a due date, instructions, and maximum score.
- **Versioned submissions** — resubmitting creates a new, append-only submission version (v1, v2, ...), so no work is ever overwritten; late submissions are flagged. Accepts code archives (.zip) and PDF documentation.
- **Checklist-based grading** — teachers/TAs use customizable grading checklists via a split-screen grading interface. Grades and AI feedback are stored independently per submission version and computed dynamically.
- **Feedback tools** — supports comments, notes, and file attachments. Teachers control sharing of grades in batch.
- **Grade visibility** — students only see shared grades and feedback on My Grades.
- **AI feedback and automatic checks** — processes submissions asynchronously against teacher-defined guidelines using background tasks (Celery/Redis), produces suggested checklist scores, feedback, and notes in draft mode, and flags missing mandatory requirements, structural discrepancies, and code problems. AI suggestions are for review only; final grades remain with the teacher.
- **Dashboards** — role-aware stats for admins, teachers, TAs, and students.
- **User & Students Info management** — admin-only user list, per-user info records.
- **Digital portfolios & activity history** — maintains organized, auditable records of submissions, grades, and feedback to support transparency and student portfolios.

## Project Objectives (Summary)

1. **Student Portal** — View active assignments, deadlines, instructions, and checklist item points; submit .zip or PDF files with preserved submission versions.
2. **Teacher/TA Portal** — Filterable submissions to grade, split-screen grading with customizable grading checklists, feedback tools, and batch grade sharing.
3. **AI Feedback & Automatic Checks** — Async processing, draft suggestions, and problem flags (missing requirements, structural discrepancies, code problems).
4. **Decoupled Architecture** — Grades and AI feedback stored independently per submission version; class averages/final grades/checklist totals computed dynamically via DB aggregations.
5. **Role-based Access Control & Activity History** — Ensure data confidentiality/integrity in compliance with the Data Privacy Act.
6. **User Acceptance Testing (UAT)** — Evaluate usability, performance, and operational efficiency.

## Significance

- **Students** — Organized submissions, version tracking, checklist-based feedback with inline notes once shared.
- **Teachers & TAs** — Less time on collection/repetitive checks, consistent grading via checklists, review AI-prepared drafts.
- **Academic Department/Institution** — Auditable record of submissions/grades/feedback supporting transparency and student portfolios.
- **Future Researchers/Students** — Reference framework for web-based learning management and AI-assisted feedback.

## Alignment

- **Institutional Research Agenda** — Information Technology and Education Innovation (web technologies + AI to improve grading/feedback).
- **SDG 4 (Quality Education)** — Timely, checklist-based feedback and more consistent grading.
- **SDG 9 (Industry, Innovation, and Infrastructure)** — Innovation in academic infrastructure through web-based systems and AI-assisted feedback.

## Scope and Limitations

### Scope & Technical Architecture

| Component | Description & Coverage |
|-----------|------------------------|
| **Core Modules** | Student Portal (assignments, uploads, grades and feedback); Teacher/TA Portal (submissions to grade, split-screen grading, feedback tools, grade sharing); AI feedback and automatic checks (guideline/prompt settings, draft help, problem flags); Activity history. |
| **Architecture** | Non-transactional, decoupled design. Re-submissions stored as append-only `SubmissionVersion`. Grades and AI feedback stored independently per `SubmissionVersion`. Class averages, final grades, checklist totals computed dynamically via Django ORM aggregations. |
| **Technology Stack** | Python/Django backend, MySQL/PostgreSQL (or SQLite), Celery with Redis for async tasks, LLM pipeline for AI feedback, HTML5/CSS3/JavaScript/Bootstrap frontend. |
| **Accepted Submissions** | Original uploads: code archives (.zip) and PDF documentation. Projects additionally accept folder uploads from the web/API/VS Code extension. |
| **Target Users** | Students, Teachers, Teaching Assistants (TAs), and System Administrators of the BSIT program. |

### Limitations

- **Deployment** — Operates within an intranet/local network or hosted web server for the target institution.
- **AI as Assistive Tool** — AI suggestions (scores, feedback, flags) are subject to teacher review; final grades are determined by teachers.
- **AI Quality Dependency** — Quality depends on clarity of guidelines/prompts and LLM capability.
- **Submission Types** — Classic uploads remain .zip and PDF. Projects also accept folder uploads. Automated execution of submitted code is excluded in the current phase; test/code runner integration reports "not run" unless an isolated runner is configured.
- **Anomaly Scope** — Flags cover missing mandatory requirements, structural discrepancies, and code anomalies; no comparison against external online sources.
- **Integrations Excluded** — External LMS, online payment, and SMS gateway notifications are excluded in the current phase.

## Tech stack

- Backend: Django (Python)
- Database: MySQL / MariaDB (XAMPP) by default, SQLite for local dev and tests
- Task Queue: Celery with Redis (for async AI evaluation)
- AI: LLM pipeline for AI-assisted evaluation
- Frontend: Tabler UI + Bootstrap 5
- Project workflow: `apps.projects` (saved versions, local Git mirror, change requests, change reviews, feedback, notifications, server-issued API access keys)
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

Open http://127.0.0.1:8000/ and sign in, or create an account (choose Student or Teacher on the signup page).

## Projects, Git versioning, and automatic feedback

ClassForge now also provides a full project-development workflow on top of the
original assignment submission system:

- **Projects** for every student/assignment pair, with immutable, checksummed
  saved versions and a deterministic canonical archive.
- **Web, API, and VS Code upload** — upload a ZIP or a folder;
  `.classforgeignore`, assignment exclusions, secret filtering, path-traversal
  protection, and size/file limits are enforced server-side.
- **Server-owned Git mirror** — saved versions are committed locally (never
  executed); new versions, branches, and change-review merges are tracked.
- **Grading checklist versions and staged feedback** — deterministic checks
  (required files/directories, formats, documentation, tests, risky patterns)
  produce an evidence-based draft; an optional AI provider creates a validated
  draft when configured. AI output is never a final grade.
- **Teacher review** — drafts are reviewed, overridden, rejected, or applied as
  a grade that is **not shared**; sharing remains an explicit teacher action.
- **Change requests and change reviews** with comments, merge/close actions,
  notifications, activity history, and feedback retries.
- **Safe DB/ERD inspection** — SQLite files are opened read-only with an
  authorizer; SQL/ERD/documentation artifacts are inspected statically. Student
  code and SQL are never executed in the Django process.
- **VS Code extension** — access-key sign-in via SecretStorage, course/assignment
  selection, file-preview, upload progress/errors, status/feedback, and local
  branch creation for change requests.

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

- **Push** = upload the current workspace as a saved version.
- **Pull** = fetch the latest feedback, shared grade, and change requests.

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

   Enter your ClassForge username/password. Only a server-issued access key is
   saved, in VS Code SecretStorage.

6. **Select the course and assignment:**

   ```text
   ClassForge: Select Course
   ClassForge: Select Assignment
   ```

   The account must have joined the course and the assignment must be available.

7. **Preview the push (optional but recommended):**

   ```text
   ClassForge: Preview Files to Upload
   ```

   This shows every file, its size/SHA-256, and why other files were excluded.

8. **Push your files:**

   ```text
   ClassForge: Upload Project Files
   ```

   Confirm the dialog, optionally add a note, and wait for the progress
   notification. The server stores a new saved version (`v1`, `v2`, …),
   optionally records it in the server-owned project history, and optionally
   starts automatic feedback.

9. **Pull status/feedback:**

   ```text
   ClassForge: Check Feedback
   ClassForge: View Feedback
   ```

   These open the latest saved-version status, feedback, and the shared grade if
   the teacher has released one. The ClassForge website is available with
   `ClassForge: Open ClassForge Website`.

10. **Handle change requests:**

    ```text
    ClassForge: Start Requested Changes
    ```

    Select an open change request; the extension creates and checks out a
    local branch (for example `revision/42-fix-erd`). Commit your changes
    locally, then run **Upload Project Files** again to upload a new saved
    version. Send the changes for review in the web app.

| Action | VS Code command | What happens |
| --- | --- | --- |
| Push project | `ClassForge: Upload Project Files` | Uploads files and creates a new saved version. |
| Pull latest status | `ClassForge: Check Feedback` | Fetches the latest saved version and feedback status. |
| Pull feedback | `ClassForge: View Feedback` | Shows the summary, grading checklist, and shared grade. |
| Pull requested changes | `ClassForge: Start Requested Changes` | Lists open change requests and creates a local branch. |
| Open ClassForge | `ClassForge: Open ClassForge Website` | Opens `/projects/` in the browser. |

**Not supported:** `git push` to ClassForge, `git pull`/clone saved versions back
to VS Code, or automatic branch push/change-review creation. The server project
history is internal; the source of truth for your code remains your local
workspace.

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
