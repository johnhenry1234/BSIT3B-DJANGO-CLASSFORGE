/**
 * Local Git helpers used by the "Create Revision Branch" command.
 *
 * Only local branch operations are performed.  Pushing and force-updating
 * branches require an explicit user action in the Git UI.
 */

import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const run = promisify(execFile);

export function slugifyBranchPart(value: string): string {
  const slug = (value || '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^[-._]+|[-._]+$/g, '')
    .slice(0, 60);
  return slug || 'revision';
}

export function revisionBranchName(projectId: number, title: string): string {
  return `revision/${projectId}-${slugifyBranchPart(title)}`;
}

export function validateBranchName(name: string): string {
  const value = (name || '').trim();
  if (!value) {
    throw new Error('A branch name is required.');
  }
  if (
    value.startsWith('-') ||
    value.startsWith('.') ||
    value.endsWith('.') ||
    value.endsWith('/') ||
    value.includes('..') ||
    value.includes('//') ||
    value.includes('@{') ||
    /[\s~^:?*[\\\x00-\x1f\x7f]/.test(value)
  ) {
    throw new Error(`"${value}" is not a valid Git branch name.`);
  }
  return value;
}

async function git(cwd: string, args: string[]): Promise<string> {
  const { stdout } = await run('git', args, { cwd, timeout: 30_000 });
  return stdout.trim();
}

export async function isGitRepository(cwd: string): Promise<boolean> {
  try {
    return (await git(cwd, ['rev-parse', '--is-inside-work-tree'])) === 'true';
  } catch {
    return false;
  }
}

export async function currentBranch(cwd: string): Promise<string> {
  return git(cwd, ['rev-parse', '--abbrev-ref', 'HEAD']);
}

export async function branchExists(cwd: string, branch: string): Promise<boolean> {
  try {
    await git(cwd, ['rev-parse', '--verify', `refs/heads/${validateBranchName(branch)}`]);
    return true;
  } catch {
    return false;
  }
}

/**
 * Create and check out a local revision branch.
 * Returns the branch name that was created.
 */
export async function createRevisionBranch(
  cwd: string,
  projectId: number,
  title: string,
  baseBranch?: string,
  requestedName?: string,
): Promise<string> {
  if (!(await isGitRepository(cwd))) {
    throw new Error('Open a folder inside a Git repository before creating a revision branch.');
  }
  const branch = validateBranchName(
    requestedName?.trim() || revisionBranchName(projectId, title),
  );
  if (await branchExists(cwd, branch)) {
    throw new Error(`Branch "${branch}" already exists. Check it out or delete it first.`);
  }
  const args = ['checkout', '-b', branch];
  if (baseBranch) {
    args.push(validateBranchName(baseBranch));
  }
  await git(cwd, args);
  return branch;
}
