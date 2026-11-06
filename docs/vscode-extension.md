# VS Code extension

Source: `vscode-extension/`  
Package README: `vscode-extension/README.md`

## Purpose

The extension lets a student (or teacher/TA) work with ClassForge projects from
the editor:

- secure sign-in via VS Code SecretStorage,
- course and assignment selection,
- local preview of files to upload, including exclusions and SHA-256 checksums,
- upload progress and clear API errors,
- feedback status and feedback documents,
- local branch creation for an open change request,
- quick access to the ClassForge website.

It is intentionally not a code runner and does not execute workspace code.

## Build and test

```powershell
cd vscode-extension
npm install
npm run compile
npm test
```

`package.json` declares only dev dependencies (`typescript`, `@types/node`,
`@types/vscode`). Runtime code uses built-in `fetch`, `FormData`, `crypto`, and
`child_process`.

### Run from source

Open `vscode-extension/` in VS Code and press **F5**. The included
`.vscode/launch.json` starts an Extension Development Host and runs
`npm: compile` first.

### Package a VSIX

```powershell
npx @vscode/vsce package
code --install-extension classforge-vscode-0.1.0.vsix
```

The extension is not published to the Marketplace.

## Configuration

| Setting | Default | Notes |
| --- | --- | --- |
| `classforge.serverUrl` | `http://localhost:8000` | Must point at a running ClassForge server. |
| `classforge.maxFiles` | `500` | Client-side guard; the server limit also applies. |
| `classforge.maxBytes` | `52428800` | Client-side guard; the server limit also applies. |
| `classforge.requestTimeoutMs` | `120000` | Increase for slow uploads/networks. |

## Sign-in and access keys

1. **ClassForge: Sign In** asks for username/password.
2. The extension calls `POST /api/v1/auth/token/` and stores only the returned
   access key in SecretStorage under `classforge.token`.
3. Passwords are never persisted.
4. **ClassForge: Sign Out** deletes the local access key. An administrator can
   turn off a server-side key in Django admin or through the token revoke API.

If the access key expires or is turned off, API calls return `401`; the
extension offers to sign in again.

## Push and pull from VS Code

ClassForge does not expose a Git remote to VS Code: there is no `git push` to
ClassForge and no `git pull`/clone from it. In this extension, **push** means
uploading a new saved version, and **pull** means fetching feedback status,
feedback, and open change requests. Normal Git can still be used separately for
GitHub/GitLab.

Full step-by-step instructions for both actions are in
[`vscode-extension/README.md`](../vscode-extension/README.md#push-and-pull-from-vs-code-step-by-step)
and the root [`README.md`](../README.md#push-and-pull-from-vs-code).

## Upload flow

1. Select a course, then a published assignment.
2. Optionally run **Preview Files to Upload**.
3. Run **Upload Project Files**, confirm the summary, and add an optional note.
4. The extension uploads multipart `files[]` + `paths` + `.classforgeignore`
   to `POST /api/v1/assignments/{id}/submit/`.
5. The server re-applies exclusions, validates the archive, stores a saved
   version, optionally records it in project history, and optionally queues
   automatic feedback.
6. The extension records the saved-version ID in workspace state for
   status/feedback.

If no AI key is configured, feedback comes from the automatic checker and is
labelled with the local method. It is still only a suggestion.

## Exclusions

The extension mirrors the server policy (see `src/files.ts`):

- mandatory security exclusions cannot be re-included by `.classforgeignore`;
- assignment-level `default_exclusions` are applied;
- `.classforgeignore` supports blank lines, `#` comments, glob patterns, and
  `!` negation for non-security files;
- symlinks are not followed;
- absolute paths and `..` traversal are rejected;
- file count and total byte limits are enforced locally and on the server.

Preview shows the final list, sizes, checksums, and reasons for exclusions.

## Requested changes

**ClassForge: Start Requested Changes**:

1. fetches open change requests for the selected project,
2. lets you choose one,
3. creates and checks out a local branch named after the request
   (`revision/<project>-<slug>` or the teacher-provided name),
4. optionally opens the upload command.

Branch operations are local only. The extension does not push, force-push, or
rewrite history. Send changes for review in the web app/API.

## Tests

`npm test` runs:

- API client tests with an injected `fetch` (auth, multipart, errors, timeouts),
- exclusion/file-list tests against a temporary workspace,
- Git helper tests, including real temporary repositories.

Git tests require `git` on `PATH`. Network access is not required.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| “Sign in to ClassForge first” | Run **ClassForge: Sign In**; check `classforge.serverUrl`. |
| “Could not reach the ClassForge server” | Start Django, verify URL/port/firewall. |
| `401` after working previously | Access key expired or was turned off; sign in again. |
| `403` on upload | Account has not joined the course or the assignment is not published. |
| Empty file list/“no files remain” | Check `.classforgeignore`, assignment exclusions, and required secret filters. |
| “more than N files” / “upload limit” | Remove generated files or raise the limits on both client and server. |
| Change request command says no open requests | The teacher/TA has not created one for this project. |
| “not a Git repository” | Open a workspace inside a Git repository (or run `git init`). |
| Branch already exists | Check it out/delete it, or let the teacher supply another name. |

## Limitations

- No Marketplace publication.
- No push/change-review creation inside VS Code.
- No webview/inline diff; feedback opens as Markdown.
- No offline queue: uploads require a reachable server.
- AI feedback is only as good as the configured checklist/provider; final grades
  are teacher-controlled.
