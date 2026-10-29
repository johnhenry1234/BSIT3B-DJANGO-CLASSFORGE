# ClassForge architecture

This document describes the project workspace and assessment platform added on
top of the original ClassForge submission/grading system. The existing
`courses` app remains the source of truth for assignments, submissions, rubrics,
grades, and audit events.

## 1. Request flow

```
VS Code extension ─┐
Web browser ───────┼─> Django views / JSON API v1
API clients ───────┘         │
                             ├─ apps.projects.services    snapshots, archives, Git, review
                             ├─ apps.projects.parsers     safe artifact + SQL analysis
                             ├─ apps.projects.assessment  staged assessment pipeline
                             └─ apps.courses              Submission / Grade / Rubric tables
```

There is no SPA and no separate frontend build. Web pages are server-rendered
Django templates using the existing Tabler theme. The VS Code extension is a
separate TypeScript package under `vscode-extension/`.

## 2. Application boundaries

| Module | Responsibility |
| --- | --- |
| `apps.courses` | Courses, enrollments, assignments, append-only submissions, rubric criteria, published rubric versions, grades, feedback. |
| `apps.projects` | Student project workspaces, immutable snapshots, server-owned Git mirrors, revision requests, pull requests, assessment drafts, criterion scores, notifications, API tokens. |
| `apps.ai` | Legacy AI evaluation inspector used by the original submission flow. |
| `apps.projects.api` | Bearer-token JSON API v1 consumed by the extension. |
| `apps.projects.views` | Instructor/student web UI for projects, assessment review, revisions, pull requests, notifications, tokens. |
| `vscode-extension` | Workspace file collection, snapshot upload, status/feedback display, revision branch creation. |

### Why a separate app?

`projects` depends on `courses`, never the reverse. This avoids migration cycles
and keeps grading data in one place. A snapshot is linked to an existing
submission through a nullable one-to-one field on `ProjectSnapshot`
(`ProjectSnapshot.submission`), so `courses` does not need a new foreign key.

## 3. Data model

| Model | Purpose | Key invariants |
| --- | --- | --- |
| `Project` | One durable workspace per `(assignment, student)`. | Unique constraint on assignment + student. |
| `Repository` | Metadata for the server-owned Git mirror. | One-to-one with project; stores branch/commit only. |
| `ProjectSnapshot` | Immutable canonical archive + manifest + validation data. | Unique `(project, version)`; `save()` rejects updates; SHA-256 checksum. |
| `RevisionRequest` | Instructor/TA request for changes, optionally tied to a snapshot and branch. | `open` → `addressed`/`closed`. |
| `PullRequest` | Proposed snapshot/branch merge with comments and review state. | `open` → `merged`/`closed`; merge records reviewer and commit. |
| `PullRequestComment` | Discussion on a pull request. | Author required. |
| `Assessment` | One automated evaluation of a snapshot. | Status `queued/running/completed/failed`; `requires_review` defaults to true; engine recorded. |
| `CriterionAssessment` | Per-rubric-criterion AI and instructor points. | `instructor_points` overrides `ai_points`; points bounded by validators. |
| `Notification` | In-app notification for staff/students. | Per-user read timestamp. |
| `ApiToken` | Hashed bearer token for API clients. | SHA-256 hash only; prefix shown once; expiry and revocation. |

Assignment fields added in `courses` cover publication state, outcomes,
accepted formats, required files/directories, documentation requirements,
validation rules, required tests, upload limits, AI grading mode, manual review,
late policy, resubmission, revision window, and default exclusions. Rubric
criteria gained descriptions, expected evidence, validation rules, and position.
`RubricVersion` stores an immutable published snapshot of rubric criteria.

## 4. Snapshot lifecycle

1. A student submits from the web, API, or VS Code.
2. Server-side exclusion rules are applied, including `.classforgeignore`,
   assignment defaults, and mandatory secret/dependency exclusions.
3. Files are normalised to POSIX relative paths; archive traversal, duplicate
   paths, absolute paths, and unsafe names are rejected.
4. A deterministic ZIP is built (stable entry order, fixed timestamps).
5. Limits are enforced: files, total uncompressed bytes, per-file upload size.
6. The archive is stored under `CLASSFORGE_SNAPSHOT_ROOT` (or Django media).
7. A `ProjectSnapshot` row is created with manifest, checksum, and validation.
8. If `CLASSFORGE_GIT_ENABLED` is on, the archive is committed into a
   server-owned Git workspace. Git failures are logged and do not lose the
   snapshot.
9. Optionally a `courses.Submission` is created, preserving the existing
   versioned submission workflow.
10. Assessment is requested automatically when the assignment enables it.

Snapshots are never updated in place. Corrections always create a new version.

## 5. Assessment pipeline

`apps.projects.assessment.run_assessment()` is idempotent for completed
assessments and bounded by `ASSESSMENT_MAX_ATTEMPTS`:

1. **Load and extract** — read the snapshot archive through the safe extractor;
   build a structure overview, SQL/ERD/documentation artifacts, secret and risk
   findings. Student code is not executed.
2. **Deterministic checks** — required files/directories, accepted formats,
   documentation, validation rules, tests, missing-file and risky-pattern
   checks. Test execution is reported as `disabled`/`not run` unless a separate
   isolated runner is configured.
3. **Local rubric draft** — evidence-based, deterministic scores and comments
   from the criteria. This is always available and is the fallback.
4. **Optional AI draft** — if `AI_API_KEY` is set, an OpenAI-compatible
   chat-completions request is made. The response must be valid JSON and is
   validated strictly (known criterion IDs, no duplicates, points within
   bounds, required fields, total score consistency). Invalid output is rejected
   and the local draft is kept; the engine label records the failure.
5. **Persist** — `Assessment` + `CriterionAssessment` records are written in a
   transaction.
6. **Apply (optional)** — only when the assignment is in automatic mode *and*
   manual review is disabled. Even then the created `Grade` is unpublished until
   an instructor publishes it.
7. **Notify + audit** — staff/student notifications and activity log entries.

### Grading modes

| `Assignment.ai_grading_mode` | `manual_review_required` | Behaviour |
| --- | --- | --- |
| `instructor_approved` (default) | any | Draft is stored; instructor must review and apply. |
| `automatic` | `True` | Draft is stored; review still required. |
| `automatic` | `False` | Draft is applied as an **unpublished** grade automatically. |

`Assessment.review_status` is one of `pending`, `approved`, `overridden`,
`rejected`. Applying a review creates/updates an unpublished `courses.Grade`.
Publishing remains the existing instructor-controlled action.

### Dispatch modes

| `ASSESSMENT_DISPATCH_MODE` | Behaviour |
| --- | --- |
| `inline` (default) | Assessment runs in the request/worker process. Best for development and tests. |
| `thread` | Runs in a daemon thread. Suitable for small single-process deployments; not a durable queue. |
| `celery` | Calls `apps.projects.tasks.run_assessment_task.delay()`. Celery/Redis must be installed and configured separately. Falls back to inline if dispatch fails. |

## 6. Safe inspection rules

- Archives are inspected in memory with size/count limits. Path traversal,
  absolute paths, duplicate upload paths, encrypted entries, and oversized
  expansions are rejected or reported; nothing is extracted to disk.
- Only read-only SQLite database files are opened, in immutable/read-only mode,
  with a SQLite authorizer that blocks writes and dangerous pragmas.
- SQL text is parsed with `sqlparse`; comments/strings are ignored for basic
  risk checks. This is static inspection, not execution.
- Secret/risky patterns are reported as findings; secret file names are excluded
  before upload.
- AI/provider payloads are treated as untrusted input and validated before use.
- API tokens are stored as hashes and compared by hash. Tokens are scoped,
  expire, and can be revoked.
- Web routes enforce the existing role/enrollment checks; API routes re-check
  course access independently of session state.

## 7. Server-owned Git

When enabled, each project gets a workspace directory outside the web root.
`apps.projects.services` runs Git via `subprocess` with fixed arguments (no shell
interpolation), commits snapshot content, and can merge a pull request branch.
Only the server's Git identity is used. Student code is committed, never
executed. Pull-request merges record the source snapshot and merge commit SHA.

If Git is unavailable or disabled, snapshots and assessments still work; the UI
shows that no commit was created.

## 8. VS Code extension architecture

| File | Role |
| --- | --- |
| `src/api.ts` | Typed API client; injectable `fetch`; no credential storage. |
| `src/files.ts` | Exclusion policy mirror, glob/ignore parsing, deterministic manifest, size limits. |
| `src/git.ts` | Local branch slug/validation and revision branch creation (no push). |
| `src/extension.ts` | Commands, SecretStorage token, status bar, progress, markdown views. |

The extension mirrors server exclusions but treats them as a UX convenience;
the server re-applies every rule. It has no runtime npm dependencies and never
executes workspace code.

## 9. Known boundaries

- No sandboxed code/test runner is bundled. Automated tests/command execution
  stays disabled by default and is reported honestly as not run.
- Celery/Redis are optional and not installed here. The `celery` dispatch mode
  requires a worker and broker.
- Git hosting (GitHub/GitLab) is not integrated. The Git mirror is local to the
  server; `remote_url` is metadata only.
- Rate limiting uses Django's cache. The default local-memory cache is
  per-process; production should configure a shared cache backend.
- AI quality depends on the configured model and prompt; all AI output remains a
  draft subject to instructor review.
