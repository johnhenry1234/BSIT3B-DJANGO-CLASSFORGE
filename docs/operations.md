# Operations, configuration, and security

## 1. Prerequisites

- Python 3.12+ (the repository was developed/tested with Python 3.15 and
  Django 6.1.2).
- Node.js 18+ and npm (extension build/test only; Node 24 was used).
- Git (optional, for the server-owned snapshot mirror and revision branches).
- MySQL/MariaDB (optional; SQLite is the default).
- A virtual environment is recommended.

## 2. Install and migrate

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
```

SQLite is used by default (`db.sqlite3`). For MySQL:

```powershell
$env:DB_ENGINE = 'mysql'
$env:DB_NAME = 'bsitcrud'
$env:DB_USER = 'root'
$env:DB_PASSWORD = '...'
python manage.py migrate
```

Migrations added by this work:

- `apps/courses/migrations/0005_assignment_accepted_formats_and_more.py`
- `apps/projects/migrations/0001_initial.py`

Verify there are no missing migrations:

```powershell
python manage.py makemigrations --check --dry-run
python manage.py check
```

## 3. Environment variables

Django does not auto-load `.env`. Copy `.env.example` and export the values in
your shell/process manager, or use your deployment platform's secret store.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | insecure dev key | Set a strong secret in production. |
| `DJANGO_DEBUG` | `1` | Set `0` in production. |
| `DJANGO_ALLOWED_HOSTS` | localhost/127.0.0.1 when DEBUG | Comma-separated host names. Required in production. |
| `DB_ENGINE` | `sqlite` | `sqlite` or `mysql`. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | SQLite defaults / `bsitcrud` | MySQL connection. |
| `DJANGO_MEDIA_ROOT` | `./media` | Uploaded files root. |
| `AI_API_BASE` | `https://api.openai.com/v1` | OpenAI-compatible API base. |
| `AI_API_KEY` | empty | Empty = deterministic local inspector only. |
| `AI_MODEL` | `gpt-4o-mini` | Model label/name sent to the provider. |
| `AI_API_TIMEOUT` | `45` | Provider request timeout in seconds. |
| `AI_EVALUATION_MODE` | `inline` | Legacy AI evaluation mode; also used as fallback for assessment dispatch. |
| `ASSESSMENT_DISPATCH_MODE` | value of `AI_EVALUATION_MODE` | `inline`, `thread`, or `celery`. |
| `CLASSFORGE_MAX_UPLOAD_MB` | `25` | Per-upload limit. |
| `CLASSFORGE_MAX_SNAPSHOT_FILES` | `500` | Max files in a snapshot. |
| `CLASSFORGE_MAX_SNAPSHOT_BYTES` | `52428800` (50 MB) | Max uncompressed snapshot size. |
| `CLASSFORGE_SNAPSHOT_ROOT` | `./media/project_snapshots` | Archive root (must be writable). |
| `CLASSFORGE_TEST_RUNNER` | `disabled` | `disabled` reports required tests as not run. Any other value is labelled “runner configured” but this deployment still does not execute student code. |
| `CLASSFORGE_TEST_TIMEOUT` | `120` | Runner timeout (only relevant with an external runner). |
| `CLASSFORGE_GIT_ENABLED` | `1` | Commit snapshots into server-owned Git workspaces. |
| `CLASSFORGE_GIT_AUTHOR` | `ClassForge` | Git commit author name. |
| `CLASSFORGE_GIT_EMAIL` | `classforge@localhost` | Git commit author email. |
| `CLASSFORGE_TOKEN_TTL_DAYS` | `30` | Default API token lifetime. |
| `CLASSFORGE_API_RATE_LIMIT` | `120` | Requests per window per token/IP; `0` disables. |
| `CLASSFORGE_API_RATE_WINDOW` | `60` | Rate-limit window in seconds. |
| `ASSESSMENT_MAX_ATTEMPTS` | `3` | Attempt cap per assessment. |
| `ASSESSMENT_STALE_AFTER_MINUTES` | `30` | Stale job detection threshold. |

## 4. Tests

Backend (pytest + pytest-django):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Focused project suite:

```powershell
.\.venv\Scripts\python.exe -m pytest apps/projects/tests.py -q
```

The tests override `ALLOWED_HOSTS`, media/snapshot roots, and disable Git and
external dispatch. They use Django's test database.

VS Code extension:

```powershell
cd vscode-extension
npm install
npm test
```

`npm test` compiles TypeScript (`tsc -p ./`) and runs `node --test
out/test/*.test.js`. Tests use only Node built-ins; no runtime npm dependencies.

> `python manage.py test` is not the recommended runner in this repository
> because `apps` is a namespace package and discovery is unreliable. Use pytest
> as configured in `pytest.ini`.

## 5. Running the app

```powershell
python manage.py runserver
```

- Web UI: <http://127.0.0.1:8000/>
- Projects: <http://127.0.0.1:8000/projects/>
- Assessment queue: <http://127.0.0.1:8000/projects/assessments/>
- API health: <http://127.0.0.1:8000/api/v1/health/>
- API tokens: <http://127.0.0.1:8000/projects/tokens/>

In production run `python manage.py collectstatic`, serve `STATIC_ROOT`/media
through the web server, and put Django behind HTTPS.

## 6. Optional integrations

### AI provider

Set `AI_API_KEY` (and optionally `AI_API_BASE`, `AI_MODEL`) to enable AI drafts.
Without it, the deterministic inspector produces evidence-based drafts and the
engine label says `local`. Invalid or failed AI output is rejected; the local
draft is kept. AI output is never treated as an instructor-approved grade.

### Celery / Redis

`ASSESSMENT_DISPATCH_MODE=celery` imports
`apps.projects.tasks.run_assessment_task`. Celery and Redis are **not** included
in `requirements.txt`; install/configure them and run a worker:

```powershell
celery -A mysite worker -l info
```

If dispatch fails, the pipeline logs the error and falls back to inline
execution. For production isolation, prefer a dedicated worker/queue and an
external sandbox for any code or test execution.

### Isolated code/test runner

No sandbox is bundled. `CLASSFORGE_TEST_RUNNER=disabled` means required-test and
code-execution checks report “not run/disabled” rather than pretending to pass.
Only connect an external runner that provides OS/container isolation, resource
limits, no network by default, and read-only input mounts.

### Server-owned Git

Leave `CLASSFORGE_GIT_ENABLED=1` to mirror snapshots into local Git workspaces.
Git failures are logged and snapshots are still stored. The extension's
revision-branch command operates on the student's local repository; it does not
push.

## 7. Security notes

- Student code/SQL is **never executed** in the Django process. Archives are
  inspected in memory; SQLite is opened read-only with an authorizer.
- Mandatory exclusions cover `.env` files, keys/certificates, VCS metadata, virtual
  environments, dependency/cache directories, and common secret files. Negation
  rules cannot re-include them.
- Snapshots are immutable and checksummed. Grades created by assessments remain
  unpublished until an instructor reviews/publishes.
- API tokens are hashed (SHA-256), scoped, expiring, revocable, and rate limited.
- Every sensitive action (token issue/revoke, snapshot upload, assessment
  request/completion/failure, revision/PR lifecycle) writes an activity log
  entry using the existing `apps.core.audit` module.
- Secrets belong in environment variables/secret stores, never in git. `.env`
  is ignored; `.env.example` contains placeholders only.

### Production hardening checklist

- [ ] Strong `DJANGO_SECRET_KEY`; `DJANGO_DEBUG=0`; explicit `DJANGO_ALLOWED_HOSTS`.
- [ ] HTTPS and secure cookies (configure through your reverse proxy/Django).
- [ ] Shared cache backend for rate limiting if running multiple processes.
- [ ] Writable `CLASSFORGE_SNAPSHOT_ROOT` with backups and size monitoring.
- [ ] Dedicated Celery worker if `ASSESSMENT_DISPATCH_MODE=celery`.
- [ ] No AI key in client code; rotate keys and API tokens.
- [ ] External runner (if any) sandboxed, network-restricted, and resource-capped.
- [ ] Log aggregation/alerting for `assessment.failed` and API `429`/`5xx`.

## 8. Backup and retention

Back up:

1. the database (`db.sqlite3` or MySQL dump),
2. `DJANGO_MEDIA_ROOT` (including project snapshot archives),
3. `CLASSFORGE_SNAPSHOT_ROOT`/Git workspaces if stored separately.

Snapshots are append-only; deleting a project cascades to its snapshots and
assessments, so prefer archival (`Project.status=archived`) over deletion.

## 9. Monitoring

- `GET /api/v1/health/` is public and returns `ok`, version, current time,
  `test_runner`, `ai_configured`, and `git_enabled`.
- Assessment queue UI shows queued/running/failed drafts and supports retry.
- Failed assessments store a bounded error message and increment `attempts`.
- Use the existing activity log for audit trails and incident review.

## 10. Troubleshooting

| Symptom | Check |
| --- | --- |
| `400` on upload | Path traversal/absolute/duplicate paths, file count/size limits, or unsupported archive. |
| `401` from the extension | Token expired/revoked; sign in again. |
| `403` on a project | User is not the owner or course staff; check enrollment/role. |
| Assessment stays queued | Dispatch mode/worker; use `inline` for development. |
| AI label says “AI output rejected” | Provider returned invalid JSON/IDs/points; inspect `raw_response`/logs; local draft was kept. |
| `no such table` after deploy | Run `python manage.py migrate`. |
| Git commit missing | `CLASSFORGE_GIT_ENABLED`, Git availability, and snapshot-root write permissions. |
| MySQL connection error | `DB_ENGINE=mysql` plus credentials; PyMySQL is installed as MySQLdb by `apps.info`. |
