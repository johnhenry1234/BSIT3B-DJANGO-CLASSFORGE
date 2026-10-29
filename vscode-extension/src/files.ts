/**
 * Workspace file collection and manifest preview.
 *
 * Exclusion rules mirror the server's defence-in-depth policy.  The server
 * re-applies every rule, so a misconfigured extension cannot exfiltrate
 * ``.env`` files or accidentally include ``node_modules``.
 */

import { createHash } from 'node:crypto';
import { promises as fs } from 'node:fs';
import path from 'node:path';

import type { ManifestEntry, UploadFile } from './api';

/** Security exclusions that can never be re-included by a negation rule. */
export const SERVER_EXCLUSIONS = [
  '.git/',
  '.git/**',
  '.hg/**',
  '.svn/**',
  'node_modules/**',
  '.venv/**',
  'venv/**',
  'env/**',
  '__pycache__/**',
  '*.pyc',
  '*.pyo',
  '.pytest_cache/**',
  '.mypy_cache/**',
  '.ruff_cache/**',
  '.tox/**',
  '.DS_Store',
  'Thumbs.db',
  '.env',
  '.env.local',
  '.env.development',
  '.env.production',
  '.env.test',
  '.env.staging',
  '*.pem',
  '*.key',
  '*.p12',
  '*.pfx',
  'id_rsa',
  'id_rsa.*',
  '.npmrc',
  '.netrc',
  '.pgpass',
];

/** Non-security defaults that keep submissions small and reproducible. */
export const DEFAULT_EXCLUSIONS = [
  '.classforgeignore',
  'media/**',
  'staticfiles/**',
  '*.log',
];

const IGNORE_FILENAME = '.classforgeignore';
const MANDATORY_DIRECTORIES = new Set(['.git', '.hg', '.svn', 'node_modules', '__pycache__']);

export interface ExcludedEntry {
  path: string;
  reason: string;
}

export interface CollectResult {
  files: UploadFile[];
  excluded: ExcludedEntry[];
  totalBytes: number;
  ignoreFile?: { name: string; content: Uint8Array };
}

export interface CollectOptions {
  maxFiles?: number;
  maxBytes?: number;
  extraPatterns?: string[];
  /** Pre-read .classforgeignore content; when omitted the file is read from the root. */
  ignoreFileText?: string;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Locale-independent ordering so manifests are identical on every machine. */
export function comparePaths(left: string, right: string): number {
  if (left === right) {
    return 0;
  }
  return left < right ? -1 : 1;
}

/** Convert an fnmatch-style pattern into an anchored regular expression. */
export function globToRegExp(pattern: string): RegExp {
  let source = '';
  let index = 0;
  while (index < pattern.length) {
    const char = pattern[index];
    if (char === '*') {
      source += '.*';
    } else if (char === '?') {
      source += '.';
    } else {
      source += escapeRegExp(char);
    }
    index += 1;
  }
  return new RegExp(`^${source}$`);
}

export function normalisePath(raw: string): string {
  const value = (raw || '').replace(/\\/g, '/').trim();
  if (!value) {
    throw new Error('An empty file path cannot be submitted.');
  }
  if (/^[A-Za-z]:/.test(value)) {
    throw new Error(`Absolute paths are not allowed: ${raw}`);
  }
  const parts = value.replace(/^\/+/, '').split('/').filter((part) => part && part !== '.');
  if (parts.some((part) => part === '..')) {
    throw new Error(`Path traversal is not allowed: ${raw}`);
  }
  if (!parts.length) {
    throw new Error(`Invalid path: ${raw}`);
  }
  return parts.join('/');
}

export function parseIgnoreFile(text: string): string[] {
  return (text || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'));
}

export function patternMatches(filePath: string, pattern: string): boolean {
  let value = (pattern || '').trim();
  if (!value || value.startsWith('#')) {
    return false;
  }
  value = value.replace(/\\/g, '/');
  if (value.endsWith('/')) {
    value += '**';
  }
  const candidate = filePath.replace(/\\/g, '/');
  if (value === '.git' || value === '.git/') {
    return candidate === '.git' || candidate.startsWith('.git/');
  }
  const expression = globToRegExp(value);
  if (expression.test(candidate)) {
    return true;
  }
  const basename = candidate.split('/').pop() || '';
  return expression.test(basename);
}

export function shouldExclude(filePath: string, patterns: readonly string[]): boolean {
  let excluded = false;
  for (const raw of patterns) {
    const pattern = (raw || '').trim();
    if (!pattern || pattern.startsWith('#')) {
      continue;
    }
    if (pattern.startsWith('!')) {
      if (patternMatches(filePath, pattern.slice(1))) {
        excluded = false;
      }
      continue;
    }
    if (patternMatches(filePath, pattern)) {
      excluded = true;
    }
  }
  // A negation may never re-include a known secret/security path.
  return excluded || SERVER_EXCLUSIONS.some((pattern) => patternMatches(filePath, pattern));
}

export function buildPatterns(
  assignmentExclusions: readonly string[] = [],
  extraPatterns: readonly string[] = [],
  ignoreFileText = '',
): string[] {
  return [
    ...DEFAULT_EXCLUSIONS,
    ...SERVER_EXCLUSIONS,
    ...assignmentExclusions,
    ...parseIgnoreFile(ignoreFileText),
    ...extraPatterns,
  ];
}

export function manifestFor(files: readonly UploadFile[]): ManifestEntry[] {
  return files
    .map((file) => ({
      path: file.path,
      size: file.content.byteLength,
      sha256: createHash('sha256').update(file.content).digest('hex'),
      extension: path.posix.extname(file.path).toLowerCase(),
    }))
    .sort((left, right) => comparePaths(left.path, right.path));
}

export async function collectFiles(
  root: string,
  options: CollectOptions = {},
): Promise<CollectResult> {
  const maxFiles = options.maxFiles ?? 500;
  const maxBytes = options.maxBytes ?? 50 * 1024 * 1024;
  let ignoreFileText = options.ignoreFileText;
  if (ignoreFileText === undefined) {
    try {
      ignoreFileText = await fs.readFile(path.join(root, IGNORE_FILENAME), 'utf8');
    } catch {
      ignoreFileText = '';
    }
  }
  const patterns = buildPatterns(
    options.extraPatterns ?? [],
    [],
    ignoreFileText ?? '',
  );

  const files: UploadFile[] = [];
  const excluded: ExcludedEntry[] = [];
  let totalBytes = 0;

  const walk = async (relativeDirectory: string): Promise<void> => {
    const absoluteDirectory = relativeDirectory
      ? path.join(root, ...relativeDirectory.split('/'))
      : root;
    const entries = await fs.readdir(absoluteDirectory, { withFileTypes: true });
    entries.sort((left, right) => comparePaths(left.name, right.name));
    for (const entry of entries) {
      const relativePath = normalisePath(
        relativeDirectory ? `${relativeDirectory}/${entry.name}` : entry.name,
      );
      if (entry.isSymbolicLink()) {
        excluded.push({ path: relativePath, reason: 'symbolic links are not followed' });
        continue;
      }
      if (entry.isDirectory()) {
        if (MANDATORY_DIRECTORIES.has(entry.name) || shouldExclude(`${relativePath}/`, patterns)) {
          excluded.push({ path: relativePath, reason: 'excluded by policy' });
          continue;
        }
        await walk(relativePath);
        continue;
      }
      if (!entry.isFile()) {
        excluded.push({ path: relativePath, reason: 'not a regular file' });
        continue;
      }
      if (shouldExclude(relativePath, patterns)) {
        excluded.push({ path: relativePath, reason: 'excluded by policy' });
        continue;
      }
      if (files.length + 1 > maxFiles) {
        throw new Error(`This workspace has more than ${maxFiles} files to submit.`);
      }
      const content = await fs.readFile(path.join(root, ...relativePath.split('/')));
      totalBytes += content.byteLength;
      if (totalBytes > maxBytes) {
        throw new Error(
          `This workspace exceeds the ${Math.round(maxBytes / (1024 * 1024))} MB snapshot limit.`,
        );
      }
      files.push({ path: relativePath, content: new Uint8Array(content) });
    }
  };

  await walk('');
  files.sort((left, right) => comparePaths(left.path, right.path));
  if (!files.length) {
    throw new Error(
      'No files remain after applying .classforgeignore and the assignment exclusions.',
    );
  }
  const ignoreFile = ignoreFileText
    ? {
        name: IGNORE_FILENAME,
        content: new Uint8Array(Buffer.from(ignoreFileText, 'utf8')),
      }
    : undefined;
  return { files, excluded, totalBytes, ignoreFile };
}

export function humanBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}
