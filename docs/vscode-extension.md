# VS Code extension

Source: `vscode-extension/`  
Package README: `vscode-extension/README.md`

## Purpose

The extension lets a student (or instructor/TA) work with ClassForge project
snapshots from the editor:

- secure token sign-in via VS Code SecretStorage,
- course and assignment selection,
- local manifest preview with exclusions and SHA-256 checksums,
- upload progress and clear API errors,
- assessment status and feedback documents,
- local revision-branch creation from an open revision request,
- quick access to the web dashboard.

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

## Sign-in and tokens

1. **ClassForge: Sign In** asks for username/password.
2. The extension calls `POST /api/v1/auth/token/` and stores only the returned
   token in SecretStorage under `classforge.token`.
3. Passwords are never persisted.
4. **ClassForge: Sign Out** deletes the local token. To invalidate it on the
   server, revoke it at `/projects/tokens/`.

If the token expires or is revoked, API calls return `401`; the extension offers
to sign in again.

## Push and pull from VS Code

ClassForge does not expose a Git remote to VS Code: there is no `git push` to
ClassForge and no `git pull`/clone from it. In this extension, **push** means
uploading an immutable project snapshot, and **pull** means fetching assessment
status/feedback and open revision requests. Normal Git can still be used
separately for GitHub/GitLab.

Full step-by-step instructions for both actions are in
[`vscode-extension/README.md`](../vscode-extension/README.md#push-and-pull-from-vs-code-step-by-step)
and the root [`README.md`](../README.md#push-and-pull-from-vs-code).

## Submission flow

1. Select a course, then a published assignment.
2. Optionally run **Preview Submission Manifest**.
3. Run **Submit Project Snapshot**, confirm the modal summary, and add an
   optional note.
4. The extension uploads multipart `files[]` + `paths` + `.classforgeignore`
   to `POST /api/v1/assignments/{id}/submit/`.
5. The server re-applies exclusions, validates the archive, stores an immutable
   snapshot, optionally mirrors it to Git, and optionally queues an assessment.
6. The extension records the snapshot ID in workspace state for status/feedback.

If no AI key is configured, feedback comes from the deterministic inspector and
is labelled with the local engine. It is still only a draft.

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

## Revision branches

**ClassForge: Create Revision Branch**:

1. fetches open revision requests for the selected project,
2. lets you choose one,
3. creates and checks out a local branch named after the request
   (`revision/<project>-<slug>` or the instructor-provided name),
4. optionally opens the submit command.

Branch operations are local only. The extension does not push, force-push, or
rewrite history. Pull requests are opened in the web UI/API.

## Tests

`npm test` runs:

- API client tests with an injected `fetch` (auth, multipart, errors, timeouts),
- exclusion/glob/manifest tests against a temporary workspace,
- Git helper tests, including real temporary repositories.

Git tests require `git` on `PATH`. Network access is not required.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| “Sign in to ClassForge first” | Run **ClassForge: Sign In**; check `classforge.serverUrl`. |
| “Could not reach the ClassForge server” | Start Django, verify URL/port/firewall. |
| `401` after working previously | Token expired/revoked; sign in again. |
| `403` on submit | Account not enrolled or assignment not published. |
| Empty manifest/“no files remain” | Check `.classforgeignore`, assignment exclusions, and mandatory secret filters. |
| “more than N files” / “snapshot limit” | Remove generated files or raise the limits on both client and server. |
| Revision command says no open requests | Instructor/TA has not created one for this project. |
| “not a Git repository” | Open a workspace inside a Git repository (or run `git init`). |
| Branch already exists | Check it out/delete it, or let the instructor supply another name. |

## Limitations

- No Marketplace publication.
- No push/PR creation inside VS Code.
- No webview/inline diff; feedback opens as Markdown.
- No offline queue: uploads require a reachable server.
- Assessment feedback is only as good as the configured rubric/provider; final
  grades are instructor-controlled.
