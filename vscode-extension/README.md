# ClassForge for VS Code

Upload ClassForge project files, check feedback, and start requested changes
without leaving VS Code.

The extension never executes workspace code. It collects files that pass the
ClassForge exclusion policy, uploads a saved version to the ClassForge server,
and displays AI feedback. AI feedback is not a final grade; teachers review and
share grades in the web app.

## Requirements

- A running ClassForge server (default `http://localhost:8000`).
- A ClassForge account that has joined the target course (or a teacher/TA
  account).
- VS Code 1.85+.
- Git, only for the requested-changes command.

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

- **Push** = upload the current workspace as a new saved version.
- **Pull** = fetch feedback status, feedback, and change requests.

Use normal Git separately if you also want GitHub/GitLab push/pull.

1. **Open your project folder** in VS Code. The extension uploads the first
   workspace folder. Add a `.classforgeignore` if you need extra exclusions;
   secrets, `.git`, dependency folders, and virtual environments are always
   excluded.
2. **Check the server URL** in Settings:

   ```json
   "classforge.serverUrl": "http://localhost:8000"
   ```

3. **Sign in:** run **ClassForge: Sign In** from the Command Palette
   (`Ctrl+Shift+P`). Enter your ClassForge username/password. The server returns
   a scoped, expiring access key; the extension stores only that key in VS Code
   SecretStorage (never the password).
4. **Select course and assignment:** run **ClassForge: Select Course**, then
   **ClassForge: Select Assignment**. Your account must have joined the course
   and the assignment must be published.
5. **Preview the push:** run **ClassForge: Preview Files to Upload** to inspect
   exactly which files and checksums will be uploaded and what was excluded.
6. **Push your files:** run **ClassForge: Upload Project Files**, confirm, and
   optionally add a note. The server stores a new saved version (`v1`, `v2`, …),
   optionally records it in the server-owned project history, and optionally
   starts automatic feedback.
7. **Pull status/feedback:** run **ClassForge: Check Feedback** or
   **ClassForge: View Feedback**. The ClassForge website is available with
   **ClassForge: Open ClassForge Website**.
8. **Pull requested changes:** when a teacher/TA requests changes, run
   **ClassForge: Start Requested Changes**, choose the request, commit locally,
   then upload your new files. Send the changes for review from the project page
   in the web app.

| Action | Command | Result |
| --- | --- | --- |
| Push project | `ClassForge: Upload Project Files` | New saved version uploaded. |
| Pull status | `ClassForge: Check Feedback` | Latest saved version and feedback status. |
| Pull feedback | `ClassForge: View Feedback` | Summary, checklist, and shared grade. |
| Pull requested changes | `ClassForge: Start Requested Changes` | Creates a local branch for an open change request. |
| Open ClassForge | `ClassForge: Open ClassForge Website` | Opens `/projects/` in the browser. |

Not supported: `git push` to ClassForge, `git pull`/clone of saved versions, or
automatic branch push/change-review creation. The server project history is
internal; your local workspace remains the source of truth.

The status bar shows the signed-in user and opens feedback status when clicked.

## Commands

| Command | Purpose |
| --- | --- |
| `ClassForge: Sign In` | Sign in and store an access key in SecretStorage. |
| `ClassForge: Sign Out` | Delete the local access key. Server-side key management is handled by an administrator. |
| `ClassForge: Select Course` | Choose a visible course. |
| `ClassForge: Select Assignment` | Choose a published assignment in the course. |
| `ClassForge: Preview Files to Upload` | Show files, sizes, SHA-256 checksums, and exclusions as JSON. |
| `ClassForge: Upload Project Files` | Collect, confirm, and upload files with progress/errors. |
| `ClassForge: Check Feedback` | Show saved-version details and the latest feedback status. |
| `ClassForge: View Feedback` | Markdown view of the summary, checklist, and shared grade (if any). |
| `ClassForge: Start Requested Changes` | Pick an open change request and create/check out a local branch. |
| `ClassForge: Open ClassForge Website` | Open `/projects/` on the configured server. |

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `classforge.serverUrl` | `http://localhost:8000` | ClassForge base URL. |
| `classforge.maxFiles` | `500` | Client-side file count limit. |
| `classforge.maxBytes` | `52428800` | Client-side total size limit (bytes). |
| `classforge.requestTimeoutMs` | `120000` | HTTP timeout per request. |

Server-side limits still apply and win if they are stricter.

## What gets uploaded

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
rejected. The preview file list is generated locally with SHA-256 checksums.

## Requested-changes workflow

1. The teacher/TA creates a change request in the web app or API.
2. In VS Code, run **ClassForge: Start Requested Changes**, choose the request,
   and commit your work on the created `revision/<project>-<title>` branch.
3. Upload your new files (they become a new saved version).
4. Send the changes for review from the project page or API.

Branch creation is local and does not push. The extension never force-pushes or
rewrites Git history.

## Security

- Passwords are used only to request an access key and are never stored.
- Access keys live in VS Code SecretStorage and are sent only as
  `Authorization: Bearer …` to `classforge.serverUrl`.
- Access keys expire (`CLASSFORGE_TOKEN_TTL_DAYS`) and can be turned off by an
  administrator in Django admin or through the token revoke API.
- Workspace files are read locally and uploaded only after an explicit
  confirmation dialog.
- No workspace code is executed; `git` is invoked with fixed arguments (no
  shell interpolation).

## Tests

```powershell
npm test
```

This compiles TypeScript and runs Node's built-in test runner over
`out/test/*.test.js`. Coverage includes the API client, exclusion/file-list
logic, and Git branch helpers (including a real temporary repository). Tests use
only Node built-ins and require `git` on `PATH` for the Git cases.

## Limitations

- No push/change-review creation from the extension; use the web app/API to send
  changes for review.
- No inline diff viewer/Source Control integration yet.
- Feedback is rendered as a Markdown document, not a webview.
- The extension is not published to the Marketplace; build/install locally.
- AI feedback is a suggestion and may come from the automatic checker when the
  server has no AI key configured.
