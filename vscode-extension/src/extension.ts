/**
 * ClassForge VS Code extension entry point.
 *
 * The extension is deliberately small: it authenticates with a hashed API
 * token stored in SecretStorage, collects workspace files honouring
 * ``.classforgeignore``, submits an immutable snapshot, and renders assessment
 * feedback returned by the server.  It never runs student code.
 */

import * as vscode from 'vscode';

import {
  AssessmentSummary,
  ClassForgeApiError,
  ClassForgeClient,
  RevisionRequestSummary,
  SnapshotSummary,
} from './api';
import { collectFiles, humanBytes, manifestFor } from './files';
import { createRevisionBranch } from './git';

const TOKEN_KEY = 'classforge.token';
const COURSE_KEY = 'classforge.courseId';
const ASSIGNMENT_KEY = 'classforge.assignmentId';
const SNAPSHOT_KEY = 'classforge.lastSnapshotId';

interface PreparedSubmission {
  client: ClassForgeClient;
  assignmentId: number;
  root: string;
  files: Awaited<ReturnType<typeof collectFiles>>;
  summary: string;
}

export function activate(context: vscode.ExtensionContext): void {
  const output = vscode.window.createOutputChannel('ClassForge');
  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
  status.command = 'classforge.checkStatus';
  status.show();
  context.subscriptions.push(output, status);

  const log = (message: string): void => {
    output.appendLine(`[${new Date().toISOString()}] ${message}`);
  };

  const configuredClient = (): ClassForgeClient => {
    const config = vscode.workspace.getConfiguration('classforge');
    return new ClassForgeClient({
      baseUrl: config.get<string>('serverUrl', 'http://localhost:8000'),
      timeoutMs: config.get<number>('requestTimeoutMs', 120_000),
      fetchImpl: globalThis.fetch.bind(globalThis),
    });
  };

  const authenticatedClient = async (): Promise<ClassForgeClient> => {
    const client = configuredClient();
    const token = await context.secrets.get(TOKEN_KEY);
    if (!token) {
      throw new Error('Sign in to ClassForge first (ClassForge: Sign In).');
    }
    client.setToken(token);
    return client;
  };

  const refreshStatusBar = async (): Promise<void> => {
    const token = await context.secrets.get(TOKEN_KEY);
    if (!token) {
      status.text = '$(account) ClassForge: sign in';
      status.tooltip = 'Run "ClassForge: Sign In" to connect this workspace.';
      return;
    }
    const username = context.globalState.get<string>('classforge.username', '');
    status.text = `$(cloud-upload) ClassForge${username ? `: ${username}` : ''}`;
    status.tooltip = 'Upload project files or check feedback.';
  };

  const reportError = async (error: unknown): Promise<void> => {
    const message = error instanceof Error ? error.message : String(error);
    log(`ERROR ${message}`);
    if (error instanceof ClassForgeApiError && error.status === 401) {
      const choice = await vscode.window.showErrorMessage(message, 'Sign In');
      if (choice === 'Sign In') {
        await vscode.commands.executeCommand('classforge.signIn');
      }
      return;
    }
    await vscode.window.showErrorMessage(`ClassForge: ${message}`);
  };

  const workspaceRoot = (): string => {
    const folder = vscode.workspace.workspaceFolders?.[0];
    if (!folder) {
      throw new Error('Open a folder before using ClassForge.');
    }
    return folder.uri.fsPath;
  };

  const selectCourse = async (): Promise<number | undefined> => {
    const client = await authenticatedClient();
    const courses = await client.listCourses();
    if (!courses.length) {
      throw new Error('You have not joined any ClassForge course.');
    }
    const picked = await vscode.window.showQuickPick(
      courses.map((course) => ({
        label: `${course.code} — ${course.name}`,
        description: course.instructor,
        course,
      })),
      { placeHolder: 'Select a ClassForge course' },
    );
    if (!picked) {
      return undefined;
    }
    await context.workspaceState.update(COURSE_KEY, picked.course.id);
    log(`Selected course ${picked.course.code}`);
    return picked.course.id;
  };

  const selectAssignment = async (): Promise<number | undefined> => {
    const client = await authenticatedClient();
    let courseId = context.workspaceState.get<number>(COURSE_KEY);
    if (!courseId) {
      courseId = await selectCourse();
    }
    if (!courseId) {
      return undefined;
    }
    const assignments = await client.listAssignments(courseId);
    if (!assignments.length) {
      throw new Error('There are no available assignments in this course.');
    }
    const picked = await vscode.window.showQuickPick(
      assignments.map((assignment) => ({
        label: assignment.title,
        description: assignment.due_date
          ? `due ${new Date(assignment.due_date).toLocaleString()}`
          : assignment.status,
        detail:
          assignment.required_files.length || assignment.required_directories.length
            ? `Required: ${[...assignment.required_files, ...assignment.required_directories].join(', ')}`
            : undefined,
        assignment,
      })),
      { placeHolder: 'Select a ClassForge assignment' },
    );
    if (!picked) {
      return undefined;
    }
    await context.workspaceState.update(ASSIGNMENT_KEY, picked.assignment.id);
    await context.workspaceState.update(COURSE_KEY, courseId);
    log(`Selected assignment ${picked.assignment.title}`);
    return picked.assignment.id;
  };

  const prepareSubmission = async (): Promise<PreparedSubmission> => {
    const client = await authenticatedClient();
    let assignmentId = context.workspaceState.get<number>(ASSIGNMENT_KEY);
    if (!assignmentId) {
      assignmentId = await selectAssignment();
    }
    if (!assignmentId) {
      throw new Error('Select an assignment before submitting.');
    }
    const assignment = await client.assignmentDetail(assignmentId);
    const config = vscode.workspace.getConfiguration('classforge');
    const files = await collectFiles(workspaceRoot(), {
      maxFiles: config.get<number>('maxFiles', 500),
      maxBytes: config.get<number>('maxBytes', 50 * 1024 * 1024),
      extraPatterns: assignment.default_exclusions ?? [],
    });
    const manifest = manifestFor(files.files);
    const summary = `${manifest.length} file(s), ${humanBytes(files.totalBytes)}${
      files.excluded.length ? `, ${files.excluded.length} excluded` : ''
    }`;
    return { client, assignmentId, root: workspaceRoot(), files, summary };
  };

  const register = (command: string, handler: (...args: unknown[]) => Promise<void>): void => {
    context.subscriptions.push(
      vscode.commands.registerCommand(command, async (...args: unknown[]) => {
        try {
          await handler(...args);
        } catch (error) {
          await reportError(error);
        }
      }),
    );
  };

  register('classforge.signIn', async () => {
    const client = configuredClient();
    const username = await vscode.window.showInputBox({
      title: 'ClassForge sign in',
      prompt: 'Your ClassForge username',
      value: context.globalState.get<string>('classforge.lastUsername', ''),
      ignoreFocusOut: true,
    });
    if (!username) {
      return;
    }
    const password = await vscode.window.showInputBox({
      title: 'ClassForge sign in',
      prompt: 'Your ClassForge password (never stored)',
      password: true,
      ignoreFocusOut: true,
    });
    if (!password) {
      return;
    }
    const token = await client.createToken(username, password, 'VS Code extension');
    await context.secrets.store(TOKEN_KEY, token);
    await context.globalState.update('classforge.lastUsername', username);
    client.setToken(token);
    const me = await client.me();
    await context.globalState.update('classforge.username', me.user.username);
    await refreshStatusBar();
    log(`Signed in as ${me.user.username}`);
    await vscode.window.showInformationMessage(
      `Signed in to ClassForge as ${me.user.name || me.user.username}.`,
    );
  });

  register('classforge.signOut', async () => {
    await context.secrets.delete(TOKEN_KEY);
    await context.globalState.update('classforge.username', undefined);
    await refreshStatusBar();
    await vscode.window.showInformationMessage('Signed out of ClassForge.');
  });

  register('classforge.selectCourse', async () => {
    await selectCourse();
  });

  register('classforge.selectAssignment', async () => {
    await selectAssignment();
  });

  register('classforge.previewSubmission', async () => {
    const prepared = await prepareSubmission();
    const assignment = await prepared.client.assignmentDetail(prepared.assignmentId);
    const payload = {
      assignment: {
        id: assignment.id,
        title: assignment.title,
        course: assignment.course,
        max_score: assignment.max_score,
        required_files: assignment.required_files,
        required_directories: assignment.required_directories,
        validation_rules: assignment.validation_rules,
      },
      summary: prepared.summary,
      files: manifestFor(prepared.files.files),
      excluded: prepared.files.excluded,
    };
    const document = await vscode.workspace.openTextDocument({
      content: JSON.stringify(payload, null, 2),
      language: 'json',
    });
    await vscode.window.showTextDocument(document, { preview: true });
  });

  let submitting = false;
  register('classforge.submitProject', async () => {
    if (submitting) {
      await vscode.window.showWarningMessage(
        'Your files are still uploading. Please wait, then try again.',
      );
      return;
    }

    // Hold the lock for the whole flow, including file collection and the
    // confirmation prompt, so two command invocations cannot upload at once.
    submitting = true;
    try {
      const prepared = await prepareSubmission();
      const assignment = await prepared.client.assignmentDetail(prepared.assignmentId);
      const choice = await vscode.window.showWarningMessage(
        `Submit ${prepared.summary} for "${assignment.title}"?`,
        { modal: true },
        'Submit',
      );
      if (choice !== 'Submit') {
        return;
      }
      const note = await vscode.window.showInputBox({
        title: 'Note (optional)',
        prompt: 'Describe what changed since the last saved version',
        ignoreFocusOut: true,
      });
      const result = await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: 'Uploading project files…',
          cancellable: false,
        },
        async () =>
          prepared.client.submitFiles(prepared.assignmentId, prepared.files.files, {
            note: note || undefined,
            ignoreFile: prepared.files.ignoreFile,
            createSubmission: true,
          }),
      );

      // The upload is finished; release the lock before waiting for the user
      // to dismiss the success notification or choose a follow-up action.
      submitting = false;
      await context.workspaceState.update(SNAPSHOT_KEY, result.snapshot.id);
      await context.workspaceState.update(ASSIGNMENT_KEY, prepared.assignmentId);
      log(
        `Uploaded saved version v${result.snapshot.version} (${result.snapshot.file_count} files)`,
      );
      const actions = result.assessment ? ['View Feedback', 'Check Feedback'] : ['Check Feedback'];
      const message = `Saved version v${result.snapshot.version} uploaded (${result.snapshot.file_count} files).${
        result.assessment
          ? ' AI feedback is ready for your teacher to review.'
          : ''
      }`;
      const action = await vscode.window.showInformationMessage(message, ...actions);
      if (action === 'View Feedback') {
        await vscode.commands.executeCommand('classforge.showFeedback');
      } else if (action === 'Check Feedback') {
        await vscode.commands.executeCommand('classforge.checkStatus');
      }
    } finally {
      submitting = false;
    }
  });

  const resolveSnapshot = async (client: ClassForgeClient): Promise<SnapshotSummary | undefined> => {
    const snapshotId = context.workspaceState.get<number>(SNAPSHOT_KEY);
    if (snapshotId) {
      const status = await client.snapshotStatus(snapshotId);
      return status.snapshot;
    }
    const projects = await client.listProjects();
    const withSnapshots = projects.filter((project) => project.latest_snapshot);
    if (!withSnapshots.length) {
      throw new Error('No saved versions have been uploaded for your projects yet.');
    }
    const picked = await vscode.window.showQuickPick(
      withSnapshots.map((project) => ({
        label: project.title,
        description: `v${project.latest_snapshot!.version} · ${project.latest_snapshot!.file_count} files`,
        project,
      })),
      { placeHolder: 'Select a saved version' },
    );
    if (!picked) {
      return undefined;
    }
    await context.workspaceState.update(SNAPSHOT_KEY, picked.project.latest_snapshot!.id);
    return picked.project.latest_snapshot!;
  };

  const describeAssessment = (assessment: AssessmentSummary | null): string => {
    if (!assessment) {
      return 'No feedback has been requested for this saved version yet.';
    }
    const lines = [
      `- Status: **${assessment.status}** (method: \`${assessment.engine}\`)`,
      `- Review: **${assessment.review_status}**${assessment.requires_review ? ' — teacher review required' : ''}`,
      assessment.score !== null
        ? `- Suggested score: **${assessment.score} / ${assessment.max_score}**${
            assessment.instructor_score !== null
              ? ` · teacher score: **${assessment.instructor_score}**`
              : ''
          }`
        : '- Suggested score: not available',
    ];
    if (assessment.model_name) {
      lines.push(`- Method: \`${assessment.model_name}\``);
    }
    if (assessment.error) {
      lines.push(`- Error: ${assessment.error}`);
    }
    return lines.join('\n');
  };

  register('classforge.checkStatus', async () => {
    const client = await authenticatedClient();
    const snapshot = await resolveSnapshot(client);
    if (!snapshot) {
      return;
    }
    const status = await client.snapshotStatus(snapshot.id);
    const markdown = [
      `# ClassForge saved version v${snapshot.version}`,
      '',
      `- Files: **${snapshot.file_count}** (${humanBytes(snapshot.total_bytes)})`,
      `- Checksum: \`${snapshot.checksum}\``,
      `- Branch: \`${snapshot.branch}\``,
      `- Commit: \`${snapshot.commit_sha || 'not saved (Git disabled)'}\``,
      '',
      '## Feedback',
      '',
      describeAssessment(status.assessment),
      '',
      '> Automatic results are suggestions. Your teacher reviews and shares the final grade.',
    ].join('\n');
    const document = await vscode.workspace.openTextDocument({
      content: markdown,
      language: 'markdown',
    });
    await vscode.window.showTextDocument(document, { preview: true });
  });

  register('classforge.showFeedback', async () => {
    const client = await authenticatedClient();
    const snapshot = await resolveSnapshot(client);
    if (!snapshot) {
      return;
    }
    const feedback = await client.snapshotFeedback(snapshot.id);
    const assessment = feedback.assessment;
    const lines = [`# ClassForge feedback — v${snapshot.version}`, ''];
    if (!assessment) {
      lines.push('No feedback has been requested for this saved version yet.');
    } else {
      lines.push(describeAssessment(assessment), '');
      if (assessment.summary) {
        lines.push('## Summary', '', assessment.summary, '');
      }
      if (assessment.feedback) {
        lines.push('## Feedback', '', assessment.feedback, '');
      }
      if (assessment.criteria?.length) {
        lines.push('## Grading checklist', '', '| Checklist item | Points | Comment |', '| --- | --- | --- |');
        for (const criterion of assessment.criteria) {
          const comment = (criterion.comment || '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
          lines.push(
            `| ${criterion.name.replace(/\|/g, '\\|')} | ${criterion.points ?? '—'} / ${criterion.max_points ?? '—'} | ${comment} |`,
          );
        }
        lines.push('');
      }
    }
    if (feedback.grade) {
      lines.push(
        '## Shared grade',
        '',
        `- Score: **${feedback.grade.score} / ${feedback.grade.max_score}**`,
        `- Shared with you: **${feedback.grade.is_published ? 'yes' : 'not yet — waiting for teacher review'}**`,
        feedback.grade.feedback ? `- Feedback: ${feedback.grade.feedback}` : '',
      );
    } else {
      lines.push(
        '> No grade has been shared yet. AI feedback is not a grade.',
      );
    }
    const document = await vscode.workspace.openTextDocument({
      content: lines.join('\n'),
      language: 'markdown',
    });
    await vscode.window.showTextDocument(document, { preview: true });
  });

  register('classforge.createRevisionBranch', async () => {
    const client = await authenticatedClient();
    let assignmentId = context.workspaceState.get<number>(ASSIGNMENT_KEY);
    if (!assignmentId) {
      assignmentId = await selectAssignment();
    }
    if (!assignmentId) {
      return;
    }
    const assignment = await client.assignmentDetail(assignmentId);
    if (!assignment.project) {
      throw new Error('Upload project files before starting requested changes.');
    }
    const revisions = (await client.listRevisions(assignment.project.id)).filter(
      (revision) => revision.status === 'open',
    );
    if (!revisions.length) {
      await vscode.window.showInformationMessage(
        'There are no open change requests for this project.',
      );
      return;
    }
    const picked = await vscode.window.showQuickPick(
      revisions.map((revision: RevisionRequestSummary) => ({
        label: revision.title,
        description: revision.branch_name || undefined,
        detail: revision.description,
        revision,
      })),
      { placeHolder: 'Select the change request to work on' },
    );
    if (!picked) {
      return;
    }
    const branch = await createRevisionBranch(
      workspaceRoot(),
      assignment.project.id,
      picked.revision.title,
      undefined,
      picked.revision.branch_name || undefined,
    );
    log(`Created revision branch ${branch}`);
    const action = await vscode.window.showInformationMessage(
      `Created and checked out branch "${branch}". Commit your changes, then upload your new files.`,
      'Upload Files',
    );
    if (action === 'Upload Files') {
      await vscode.commands.executeCommand('classforge.submitProject');
    }
  });

  register('classforge.openDashboard', async () => {
    const config = vscode.workspace.getConfiguration('classforge');
    const baseUrl = config.get<string>('serverUrl', 'http://localhost:8000').replace(/\/+$/, '');
    await vscode.env.openExternal(vscode.Uri.parse(`${baseUrl}/projects/`));
  });

  context.subscriptions.push(
    context.secrets.onDidChange((event) => {
      if (event.key === TOKEN_KEY) {
        void refreshStatusBar();
      }
    }),
  );

  void refreshStatusBar();
  log('ClassForge extension activated.');
}

export function deactivate(): void {
  // Nothing to clean up: command disposables are owned by the extension context.
}
