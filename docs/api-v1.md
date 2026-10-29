# ClassForge JSON API v1

Base path: `/api/v1/`

The API is implemented with plain Django views in `apps/projects/api.py`. It does
not require Django REST Framework. Responses are JSON unless noted.

## Authentication

Create a token with a real ClassForge username/password:

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "student1",
  "password": "…",
  "name": "VS Code extension",
  "scopes": "read write",
  "days": 30
}
```

Response `201`:

```json
{
  "ok": true,
  "token": "cf_…",
  "prefix": "cf_abcd",
  "expires_at": "2026-11-28T...",
  "scopes": ["read", "write"]
}
```

The raw token is returned **once**. The server stores only its SHA-256 hash and
a short display prefix. Send it on every authenticated request:

```http
Authorization: Bearer cf_…
```

- Tokens support `read` and `write` scopes.
- Tokens expire after `CLASSFORGE_TOKEN_TTL_DAYS` when `days` is omitted. When
  supplied, `days` is clamped to 1–3650.
- Revoked/expired tokens and inactive users are rejected.
- Per-token and per-IP rate limits apply (`CLASSFORGE_API_RATE_LIMIT` per
  `CLASSFORGE_API_RATE_WINDOW` seconds). Exceeding the limit returns `429`.
- Token list/revoke endpoints are session-authenticated (web UI); token creation
  accepts either a session or username/password.

## Response conventions

- Success: HTTP 2xx with `{"ok": true, ...}`.
- Error: HTTP 4xx/5xx with `{"ok": false, "error": "human-readable message"}`.
- Decimal values are serialized as strings (for example `"8.5"`).
- Timestamps are ISO 8601 strings.
- CSRF is not required for token endpoints or bearer-token endpoints.
- Course access is re-checked server-side for every project/snapshot endpoint.

## Endpoints

### Public

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health/` | Liveness/configuration summary: version, time, `test_runner`, `ai_configured`, `git_enabled`. No auth. |

### Tokens (session)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/auth/tokens/` | List up to 50 tokens for the signed-in user. |
| `POST` | `/auth/tokens/` | Create a token from the web session (`name` form field). Raw token returned once. |
| `POST` | `/auth/tokens/{id}/revoke/` | Revoke one of the signed-in user's tokens. |

### Identity and courses (`read`)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/me/` | User profile, scopes, expiry, configured upload limits. |
| `GET` | `/courses/` | Courses visible to the user (taught/enrolled/assisting). |
| `GET` | `/assignments/?course={id}` | Assignments visible to the user; students see published assignments only. |
| `GET` | `/assignments/{id}/` | Assignment detail plus rubric criteria, latest published rubric version, and the student's project summary when applicable. |

### Projects and snapshots (`read`)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/projects/` | Up to 100 visible projects with latest snapshot and open revision/PR counts. |
| `GET` | `/projects/{id}/` | Project detail, 50 newest snapshots, revision requests, pull requests. |
| `GET` | `/projects/{id}/snapshots/` | Up to 100 snapshots for a project. |
| `GET` | `/snapshots/{id}/` | Snapshot detail with full manifest, validation, metadata, parent/previous IDs. |
| `GET` | `/snapshots/{id}/status/` | Snapshot summary plus latest assessment. |
| `GET` | `/snapshots/{id}/feedback/` | Latest assessment with checks/structure/artifacts plus published grade. |
| `GET` | `/snapshots/{id}/diff/?base={snapshot_id}` | File-level diff against another snapshot (defaults to the previous version). |

### Submission (`write`)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/assignments/{id}/submit/` | Create a snapshot (and optionally a `courses.Submission`). |
| `POST` | `/snapshots/{id}/assess/` | Queue/run an assessment for a snapshot. Returns `202`. |

#### Multipart upload contract

Preferred format (used by the VS Code extension and tested):

| Field | Type | Notes |
| --- | --- | --- |
| `files[]` | file(s) | One part per file. |
| `paths` | JSON string | Array of POSIX relative paths, same order as `files[]`. Required when names would collide. |
| `source` | string | `vscode` or omitted for `api`. |
| `note` | string | Optional snapshot note. |
| `branch` | string | Defaults to `main`. |
| `create_submission` | `1`/`0` | Defaults to `1`; creates a versioned `courses.Submission`. |
| `classforgeignore` | file | Optional `.classforgeignore` content; server re-applies exclusions. |
| `archive` | file | Alternative: a ZIP archive. The server inspects it without extracting. |

The server normalises paths, rejects traversal/absolute/duplicate paths, applies
mandatory secret/dependency exclusions, enforces file/size limits, and builds a
deterministic canonical ZIP. If both `archive` and `files[]` are sent, the
archive takes precedence.

`201` response shape:

```json
{
  "ok": true,
  "project": { "id": 1, "title": "...", "latest_snapshot": { "...": "..." } },
  "snapshot": { "id": 2, "version": 1, "file_count": 12, "manifest": [] },
  "submission": { "id": 3, "version": 1, "is_late": false },
  "assessment": { "id": 4, "status": "completed", "engine": "local" }
}
```

`submission` and `assessment` may be `null`. Assessments only run automatically
when the assignment enables `ai_auto_run`.

### Revision requests (`read` / `write`)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/revisions/` | Visible revision requests (students see their own). |
| `GET` | `/projects/{id}/revisions/` | Revision requests for one project. |
| `POST` | `/projects/{id}/revisions/new/` | Instructor/TA creates a revision request (`title` required; optional `description`, `snapshot_id`, `branch_name`). |
| `POST` | `/revisions/{id}/` | Instructor/TA updates `status` to `open`, `addressed`, or `closed`. |

### Pull requests (`read` / `write`)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/pull-requests/` | Visible pull requests. |
| `GET` | `/projects/{id}/pull-requests/` | Pull requests for one project. |
| `POST` | `/projects/{id}/pull-requests/new/` | Open a PR. Requires at least one snapshot. Fields: `title` (required), `description`, `source_snapshot_id`, `revision_request_id`, `source_branch`, `target_branch`. |
| `POST` | `/pull-requests/{id}/action/` | `{"action": "comment", "body": "..."}`, `{"action": "merge"}`, or `{"action": "close", "reason": "..."}`. Merge/close require instructor/TA. |

### Notifications (`read` / `write`)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/notifications/` | Up to 100 notifications plus unread count. |
| `POST` | `/notifications/{id}/read/` | Mark one notification read. |

## Examples

```bash
# Create a token
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"student1","password":"secret"}'

# Upload an archive
curl -X POST http://localhost:8000/api/v1/assignments/7/submit/ \
  -H "Authorization: Bearer cf_..." \
  -F "archive=@project.zip" \
  -F "note=first pass" \
  -F "create_submission=1"

# Check status and feedback
curl -H "Authorization: Bearer cf_..." \
  http://localhost:8000/api/v1/snapshots/12/status/
curl -H "Authorization: Bearer cf_..." \
  http://localhost:8000/api/v1/snapshots/12/feedback/
```

## Status codes

| Code | Meaning |
| --- | --- |
| `200` | Success. |
| `201` | Token/snapshot/revision/PR created. |
| `202` | Assessment accepted. |
| `400` | Invalid JSON/fields or unsatisfiable request. |
| `401` | Missing/invalid/expired token. |
| `403` | Missing scope or no course/project access. |
| `404` | Object not found or not visible. |
| `422` | Upload/archive validation failure. |
| `429` | Rate limit exceeded. |
| `500` | Unexpected server error; details are logged server-side. |

## Client

`vscode-extension/src/api.ts` is the reference client. It sends multipart
`files[]` + `paths`, stores tokens only in VS Code SecretStorage, and surfaces
`ClassForgeApiError` with the HTTP status and server error message.
