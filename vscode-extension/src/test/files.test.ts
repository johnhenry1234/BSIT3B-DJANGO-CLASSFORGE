import assert from 'node:assert/strict';
import { promises as fs } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { test } from 'node:test';

import {
  buildPatterns,
  collectFiles,
  globToRegExp,
  manifestFor,
  normalisePath,
  parseIgnoreFile,
  patternMatches,
  shouldExclude,
} from '../files';

async function makeWorkspace(): Promise<string> {
  const root = await fs.mkdtemp(path.join(tmpdir(), 'classforge-vscode-'));
  const files: Record<string, string> = {
    'README.md': '# Project',
    'src/app.py': 'print("hi")',
    '.env': 'SECRET=1',
    '.git/config': '[core]',
    'node_modules/pkg/index.js': 'module.exports = {};',
    'debug.log': 'noise',
    'docs/erd.md': '# ERD',
    'dist/bundle.js': 'bundle',
  };
  for (const [relative, content] of Object.entries(files)) {
    const absolute = path.join(root, ...relative.split('/'));
    await fs.mkdir(path.dirname(absolute), { recursive: true });
    await fs.writeFile(absolute, content);
  }
  await fs.writeFile(path.join(root, '.classforgeignore'), 'dist/**\n');
  return root;
}

test('glob patterns mirror the server fnmatch behaviour', () => {
  assert.equal(globToRegExp('*.log').test('nested/debug.log'), true);
  assert.equal(globToRegExp('src/*.py').test('src/app.py'), true);
  assert.equal(patternMatches('docs/erd.md', 'docs/**'), true);
  assert.equal(patternMatches('docs/nested/erd.md', 'docs/**'), true);
  assert.equal(patternMatches('docs/erd.md', 'docs/'), true);
  assert.equal(patternMatches('src/app.py', '*.py'), true);
  assert.equal(patternMatches('src/app.py', '*.js'), false);
});

test('server exclusions cannot be re-included by negation', () => {
  assert.equal(shouldExclude('.env', []), true);
  assert.equal(shouldExclude('.env', ['!.env']), true);
  assert.equal(shouldExclude('node_modules/pkg/index.js', []), true);
  assert.equal(shouldExclude('config/key.pem', []), true);
  assert.equal(shouldExclude('.env.example', []), false);
  assert.equal(shouldExclude('src/app.py', ['src/**', '!src/app.py']), false);
});

test('parseIgnoreFile skips blanks and comments', () => {
  assert.deepEqual(parseIgnoreFile('# comment\n\n dist/** \n*.log\n'), ['dist/**', '*.log']);
});

test('normalisePath rejects traversal and absolute paths', () => {
  assert.equal(normalisePath('src\\app.py'), 'src/app.py');
  assert.throws(() => normalisePath('../secret'), /traversal/);
  assert.throws(() => normalisePath('C:\\secret'), /Absolute/);
  assert.throws(() => normalisePath(''));
});

test('collectFiles applies ignore files, defaults and security exclusions', async (t) => {
  const root = await makeWorkspace();
  t.after(async () => {
    await fs.rm(root, { recursive: true, force: true });
  });

  const result = await collectFiles(root);

  assert.deepEqual(
    result.files.map((file) => file.path),
    ['README.md', 'docs/erd.md', 'src/app.py'],
  );
  assert.ok(result.totalBytes > 0);
  const excluded = new Set(result.excluded.map((entry) => entry.path));
  for (const path of ['.env', '.git', 'node_modules', 'debug.log', 'dist']) {
    assert.equal(excluded.has(path), true, `${path} should be excluded`);
  }
  assert.ok(result.ignoreFile);
  assert.equal(result.ignoreFile?.name, '.classforgeignore');
});

test('collectFiles honours extra assignment patterns', async (t) => {
  const root = await makeWorkspace();
  t.after(async () => {
    await fs.rm(root, { recursive: true, force: true });
  });

  const result = await collectFiles(root, { extraPatterns: ['src/**'] });

  assert.deepEqual(
    result.files.map((file) => file.path),
    ['README.md', 'docs/erd.md'],
  );
});

test('collectFiles enforces file and size limits', async (t) => {
  const root = await makeWorkspace();
  t.after(async () => {
    await fs.rm(root, { recursive: true, force: true });
  });

  await assert.rejects(() => collectFiles(root, { maxFiles: 1 }), /more than 1 files/);
  await assert.rejects(() => collectFiles(root, { maxBytes: 5 }), /snapshot limit/);
});

test('manifestFor produces deterministic checksums and sizes', () => {
  const first = manifestFor([
    { path: 'b.txt', content: new Uint8Array(Buffer.from('bbb')) },
    { path: 'a.txt', content: new Uint8Array(Buffer.from('aa')) },
  ]);
  const second = manifestFor([
    { path: 'a.txt', content: new Uint8Array(Buffer.from('aa')) },
    { path: 'b.txt', content: new Uint8Array(Buffer.from('bbb')) },
  ]);

  assert.deepEqual(
    first.map((entry) => entry.path),
    ['a.txt', 'b.txt'],
  );
  assert.deepEqual(first, second);
  assert.equal(first[0].size, 2);
  assert.equal(first[0].sha256.length, 64);
  assert.equal(first[1].extension, '.txt');
});

test('buildPatterns combines all exclusion sources', () => {
  const patterns = buildPatterns(['build/**'], ['tmp/**'], 'secrets/**\n');
  assert.ok(patterns.includes('build/**'));
  assert.ok(patterns.includes('tmp/**'));
  assert.ok(patterns.includes('secrets/**'));
  assert.ok(patterns.includes('.env'));
});
