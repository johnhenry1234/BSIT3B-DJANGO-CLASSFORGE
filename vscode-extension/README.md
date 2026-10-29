# ClassForge for VS Code

Submit ClassForge project snapshots, check assessment status, read feedback, and
create revision branches without leaving VS Code.

The extension never executes workspace code. It collects files that pass the
ClassForge exclusion policy, uploads an immutable snapshot to the ClassForge
server, and displays the server's assessment draft. Assessment drafts are not
final grades; instructors review and publish grades in the web app.

## Requirements

- A running ClassForge server (default `http://localhost:8000`).
- A ClassForge account enrolled in the target course (or an instructor/TA
  account).
- VS Code 1.85+.
- Git, only for the revision-branch command.

## Install / develop

```powershell
cd vscode-extension
npm install
npm run compile
```

To run from source: open this folder in VS Code and press **F5** (uses
`.vscode/launch.json`). To build an installable VSIX:

```powershell
npx @vscode/vsce package
code --install-extension classforge-vscode-0.1.0.vsix
```

`vsce` is not a project dependency; `npx` downloads it on demand.

## Push and pull from VS Code (step by step)

ClassForge does **not** expose a Git remote to VS Code. There is no `git push`
to ClassForge and no `git pull`/clone from it. In this extension:

- **Push** = upload the current workspace as an immutable project snapshot.
- **Pull** = fetch assessment status, feedback, and revision requests.

Use normal Git separately if you also want GitHub/GitLab push/pull.

1. **Open your project folder** in VS Code. The extension submits the first
   workspace folder. Add a `.classforgeignore` if you need extra exclusions;
   secrets, `.git`, dependency folders, and virtual environments are always
   excluded.
2. **Check the server URL** in Settings:

   ```json
   "classforge.serverUrl": "http://localhost:8000"
   ```

3. **Sign in:** run **ClassForge: Sign In** from the Command Palette
   (`Ctrl+Shift+P`). Enter your ClassForge username/password. The server returns
   a scoped, expiring token; the extension stores only that token in VS Code
   SecretStorage (never the password).
4. **Select course and assignment:** run **ClassForge: Select Course**, then
   **ClassForge: Select Assignment**. The account must be enrolled and the
   assignment must be published.
5. **Preview the push:** run **ClassForge: Preview Submission Manifest** to
   inspect exactly which files/checksums will be uploaded and what was excluded.
6. **Push the snapshot:** run **ClassForge: Submit Project Snapshot**, confirm,
   and optionally add a note. The server stores a new immutable version
   (`v1`, `v2`, …), optionally mirrors it to the server-owned Git repository,
   and optionally starts an assessment.
7. **Pull status/feedback:** run **ClassForge: Check Assessment Status** or
   **ClassForge: Show Feedback**. The web dashboard is available with
   **ClassForge: Open Web Dashboard**.
8. **Pull revision work:** when an instructor/TA creates a revision request, run
   **ClassForge: Create Revision Branch**, choose the request, commit locally,
   then submit a new snapshot. Open/review the pull request in the web UI.

| Action | Command | Result |
| --- | --- | --- |
| Push project | `ClassForge: Submit Project Snapshot` | New immutable snapshot version uploaded. |
| Pull status | `ClassForge: Check Assessment Status` | Latest snapshot and assessment status. |
| Pull feedback | `ClassForge: Show Feedback` | Summary, criteria, and published grade. |
| Pull revision work | `ClassForge: Create Revision Branch` | Creates a local branch for an open revision request. |
| Open system | `ClassForge: Open Web Dashboard` | Opens `/projects/` in the browser. |

Not supported: `git push` to ClassForge, `git pull`/clone of snapshots, or
automatic branch push/PR creation. The server Git mirror is internal; your local
workspace remains the source of truth.

The status bar shows the signed-in user and opens status when clicked.

## Commands

| Command | Purpose |
| --- | --- |
| `ClassForge: Sign In` | Authenticate and store a server token in SecretStorage. |
| `ClassForge: Sign Out` | Delete the local token. Revoke it separately in the web UI. |
| `ClassForge: Select Course` | Choose a visible course. |
| `ClassForge: Select Assignment` | Choose a published assignment in the course. |
| `ClassForge: Preview Submission Manifest` | Show files, sizes, SHA-256 checksums, and exclusions as JSON. |
| `ClassForge: Submit Project Snapshot` | Collect, confirm, and upload files with progress/errors. |
| `ClassForge: Check Assessment Status` | Show snapshot metadata and the latest assessment status. |
| `ClassForge: Show Feedback` | Markdown view of summary, criteria, and the published grade (if any). |
| `ClassForge: Create Revision Branch` | Pick an open revision request and create/check out a local branch. |
| `ClassForge: Open Web Dashboard` | Open `/projects/` on the configured server. |

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `classforge.serverUrl` | `http://localhost:8000` | ClassForge base URL. |
| `classforge.maxFiles` | `500` | Client-side file count limit. |
| `classforge.maxBytes` | `52428800` | Client-side total size limit (bytes). |
| `classforge.requestTimeoutMs` | `120000` | HTTP timeout per request. |

Server-side limits still apply and win if they are stricter.

## What gets submitted

The extension mirrors the server policy:

- **Always excluded:** `.git`/`.hg`/`.svn`, `node_modules`, virtual
  environments, Python caches, compiled files, `.env` variants, key/certificate
  files, `.npmrc`, `.netrc`, `.pgpass`, OS metadata.
- **Default excludes:** `.classforgeignore`, `media/`, `staticfiles/`, `*.log`.
- **Assignment excludes** from `default_exclusions`.
- **Your `.classforgeignore`** (gitignore-like lines; `#` comments; `!` negation
  works for non-security files only).

A negation cannot re-include a mandatory secret/security path. The server
re-applies all rules, so a modified extension cannot exfiltrate excluded files.

Paths are normalised to POSIX relative paths; traversal and absolute paths are
rejected. The manifest preview is generated locally with SHA-256 checksums.

## Revision workflow

1. The instructor/TA creates a revision request in the web UI or API.
2. In VS Code, run **ClassForge: Create Revision Branch**, choose the request,
   and commit your work on the created `revision/<project>-<title>` branch.
3. Submit a new snapshot (it becomes a new immutable version).
4. Open a pull request from the project page or API for instructor review.

Branch creation is local and does not push. The extension never force-pushes or
rewrites Git history.

## Security

- Passwords are used only to request a token and are never stored.
- Tokens live in VS Code SecretStorage and are sent only as
  `Authorization: Bearer …` to `classforge.serverUrl`.
- Tokens expire (`CLASSFORGE_TOKEN_TTL_DAYS`) and can be revoked at
  `/projects/tokens/`.
- Workspace files are read locally and uploaded only after an explicit
  confirmation dialog.
- No workspace code is executed; `git` is invoked with fixed arguments (no
  shell interpolation).

## Tests

```powershell
npm test
```

This compiles TypeScript and runs Node's built-in test runner over
`out/test/*.test.js`. Coverage includes the API client, exclusion/manifest
logic, and Git branch helpers (including a real temporary repository). Tests use
only Node built-ins and require `git` on `PATH` for the Git cases.

## Limitations

- No push/PR creation from the extension; use the web app/API for pull requests.
- No inline diff viewer/Source Control integration yet.
- Feedback is rendered as a Markdown document, not a webview.
- The extension is not published to the Marketplace; build/install locally.
- Assessment output is a draft and may be produced by the deterministic local
  inspector when the server has no AI key configured.
