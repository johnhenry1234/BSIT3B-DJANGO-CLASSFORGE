import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promises as fs } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { promisify } from 'node:util';

import {
  branchExists,
  createRevisionBranch,
  currentBranch,
  isGitRepository,
  revisionBranchName,
  slugifyBranchPart,
  validateBranchName,
} from '../git';

const run = promisify(execFile);

async function makeTempDir(): Promise<string> {
  return fs.mkdtemp(path.join(tmpdir(), 'classforge-git-'));
}

async function initRepo(): Promise<string> {
  const root = await makeTempDir();
  await run('git', ['init', '--initial-branch=main'], { cwd: root });
  await run('git', ['config', 'user.email', 'test@classforge.local'], { cwd: root });
  await run('git', ['config', 'user.name', 'ClassForge Test'], { cwd: root });
  await fs.writeFile(path.join(root, 'README.md'), '# demo\n');
  await run('git', ['add', '.'], { cwd: root });
  await run('git', ['commit', '-m', 'initial'], { cwd: root });
  return root;
}

test('slugifyBranchPart produces safe, readable branch components', () => {
  assert.equal(slugifyBranchPart('Database Schema: Revision #2'), 'database-schema-revision-2');
  assert.equal(slugifyBranchPart('  Ünïcode  Spaces  '), 'unicode-spaces');
  assert.equal(slugifyBranchPart(''), 'revision');
  assert.equal(slugifyBranchPart('...'), 'revision');
  assert.equal(slugifyBranchPart('a'.repeat(120)).length, 60);
});

test('revisionBranchName namespaces branches by project', () => {
  assert.equal(revisionBranchName(42, 'Fix ERD'), 'revision/42-fix-erd');
  assert.equal(revisionBranchName(7, ''), 'revision/7-revision');
});

test('validateBranchName accepts normal names and rejects unsafe ones', () => {
  assert.equal(validateBranchName('revision/42-fix-erd'), 'revision/42-fix-erd');
  assert.equal(validateBranchName(' main '), 'main');

  for (const invalid of [
    '',
    '-oops',
    '.hidden',
    'trailing.',
    'trailing/',
    'has..dots',
    'double//slash',
    'has space',
    'ref@{1}',
    'caret^',
    'colon:name',
    'question?',
    'star*',
    'back\\slash',
    'tilde~',
  ]) {
    assert.throws(() => validateBranchName(invalid), /required|not a valid/, invalid);
  }
});

test('isGitRepository is false outside a repository and true inside one', async (t) => {
  const plain = await makeTempDir();
  const repo = await initRepo();
  t.after(async () => {
    await Promise.all([
      fs.rm(plain, { recursive: true, force: true }),
      fs.rm(repo, { recursive: true, force: true }),
    ]);
  });

  assert.equal(await isGitRepository(plain), false);
  assert.equal(await isGitRepository(repo), true);
});

test('createRevisionBranch refuses to run outside a Git repository', async (t) => {
  const plain = await makeTempDir();
  t.after(async () => {
    await fs.rm(plain, { recursive: true, force: true });
  });

  await assert.rejects(
    () => createRevisionBranch(plain, 1, 'Fix ERD'),
    /inside a Git repository/,
  );
});

test('createRevisionBranch creates and checks out a new branch', async (t) => {
  const repo = await initRepo();
  t.after(async () => {
    await fs.rm(repo, { recursive: true, force: true });
  });

  const branch = await createRevisionBranch(repo, 12, 'Fix ERD');

  assert.equal(branch, 'revision/12-fix-erd');
  assert.equal(await currentBranch(repo), branch);
  assert.equal(await branchExists(repo, branch), true);
});

test('createRevisionBranch uses an explicit name and rejects duplicates', async (t) => {
  const repo = await initRepo();
  t.after(async () => {
    await fs.rm(repo, { recursive: true, force: true });
  });

  const branch = await createRevisionBranch(repo, 12, 'ignored', 'main', 'revision/custom-name');
  assert.equal(branch, 'revision/custom-name');

  await assert.rejects(
    () => createRevisionBranch(repo, 12, 'ignored', 'main', 'revision/custom-name'),
    /already exists/,
  );
  await assert.rejects(
    () => createRevisionBranch(repo, 12, 'ignored', 'main', 'bad name'),
    /not a valid Git branch name/,
  );
});
