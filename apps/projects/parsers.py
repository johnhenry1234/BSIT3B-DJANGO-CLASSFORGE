"""Safe, read-only extraction of project artifacts from snapshot archives.

Nothing in this module executes student code.  SQLite databases are opened
with a read-only URI plus a SQLite authorizer that denies every operation
except reads, and archive members are never extracted outside a temporary
directory.
"""

from __future__ import annotations

import io
import json
import os
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from django.core.exceptions import ValidationError

from .services import (
    DB_EXTENSIONS,
    DOC_EXTENSIONS,
    IMAGE_EXTENSIONS,
    SQL_EXTENSIONS,
    TEST_NAME_RE,
    TEXT_EXTENSIONS,
    normalise_path,
    read_entry,
)

MAX_TEXT_BYTES = 160_000
MAX_DB_BYTES = 20 * 1024 * 1024
MAX_EXCERPT = 6000

SECRET_PATTERNS = [
    ('private_key', re.compile(r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('aws_key', re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ('generic_secret', re.compile(
        r'(?i)\b(api[_-]?key|secret|password|passwd|access[_-]?token)\b\s*[:=]\s*[\'"][^\'"\n]{6,}[\'"]'
    )),
    ('connection_string', re.compile(
        r'(?i)(postgres|mysql|mongodb)://[^\s\'"]+:[^\s\'"]+@'
    )),
]

SUSPICIOUS_PATTERNS = [
    ('dynamic_execution', re.compile(r'\b(eval|exec)\s*\('), 'warning',
     'Avoid eval/exec on untrusted input.'),
    ('shell_execution', re.compile(r'(?i)(os\.system\s*\(|subprocess\.\w+\([^\n]*shell\s*=\s*True)'), 'critical',
     'Avoid shell execution with untrusted input.'),
    ('debug_enabled', re.compile(r'\bDEBUG\s*=\s*True\b'), 'warning',
     'Disable debug mode for submitted projects.'),
    ('tls_verification_disabled', re.compile(r'verify\s*=\s*False'), 'warning',
     'Do not disable TLS certificate verification.'),
]

SECRET_FILENAMES = re.compile(
    r'(?i)^(\.env(\..+)?|id_rsa|id_dsa|id_ecdsa|id_ed25519|.*\.(pem|key|p12|pfx|keystore))$'
)

SQL_CREATE_RE = re.compile(
    r'(?i)^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["`\[]?([A-Za-z0-9_]+)["`\]]?'
)
SQL_TABLE_ANY_RE = re.compile(
    r'(?i)\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["`\[]?([A-Za-z0-9_]+)["`\]]?'
)
MERMAID_ENTITY_RE = re.compile(
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\{|\|\||})', re.MULTILINE
)


def _decode(data):
    for encoding in ('utf-8', 'utf-16', 'latin-1'):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode('utf-8', errors='replace')


def _entry_map(manifest):
    return {item['path']: item for item in manifest or [] if item.get('path')}


def _read(archive, path, item, limit=MAX_TEXT_BYTES):
    if item.get('size', 0) > limit:
        return ''
    try:
        data = archive.read(path)
    except (KeyError, RuntimeError, OSError, zipfile.BadZipFile):
        return ''
    return _decode(data[:limit])


def _safe_statements(sql_text):
    """Split SQL into statements without executing anything."""
    statements = []
    buffer = []
    in_string = None
    index = 0
    while index < len(sql_text):
        char = sql_text[index]
        if in_string:
            buffer.append(char)
            if char == in_string and (index == 0 or sql_text[index - 1] != '\\'):
                in_string = None
        elif char in ("'", '"'):
            in_string = char
            buffer.append(char)
        elif char == ';':
            statement = ''.join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
        else:
            buffer.append(char)
        index += 1
    tail = ''.join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements[:400]


def _parse_create_table(statement):
    match = SQL_CREATE_RE.match(statement)
    if not match:
        return None
    name = match.group(1)
    body_start = statement.find('(', match.end())
    body_end = statement.rfind(')')
    body = statement[body_start + 1:body_end] if body_start != -1 and body_end > body_start else ''
    columns = []
    primary_keys = []
    foreign_keys = []
    for raw_line in re.split(r',\s*(?![^()]*\))', body):
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith(('PRIMARY KEY', 'CONSTRAINT', 'FOREIGN KEY', 'UNIQUE', 'CHECK', 'INDEX')):
            primary_match = re.search(r'(?i)PRIMARY\s+KEY\s*\(([^)]+)\)', line)
            if primary_match:
                primary_keys.extend(
                    col.strip(' `"[]')
                    for col in primary_match.group(1).split(',')
                )
            references = re.search(
                r'(?i)FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+["`\[]?([A-Za-z0-9_]+)',
                line,
            )
            if references:
                foreign_keys.append(
                    {
                        'columns': [col.strip(' `"[]') for col in references.group(1).split(',')],
                        'references': references.group(2),
                    }
                )
            continue
        column_match = re.match(r'["`\[]?([A-Za-z0-9_]+)["`\]]?\s+([A-Za-z]+)', line)
        if not column_match:
            continue
        column = column_match.group(1)
        columns.append({'name': column, 'type': column_match.group(2)})
        if 'PRIMARY KEY' in upper:
            primary_keys.append(column)
        references = re.search(
            r'(?i)REFERENCES\s+["`\[]?([A-Za-z0-9_]+)', line
        )
        if references:
            foreign_keys.append({'columns': [column], 'references': references.group(1)})
    return {
        'name': name,
        'columns': columns[:80],
        'primary_keys': sorted(set(primary_keys)),
        'foreign_keys': foreign_keys[:40],
    }


def parse_sql(text):
    statements = _safe_statements(text)
    tables = []
    for statement in statements:
        table = _parse_create_table(statement)
        if table:
            tables.append(table)
    syntax_issues = []
    if text.strip():
        if text.count('(') != text.count(')'):
            syntax_issues.append('Unbalanced parentheses in SQL text.')
        if not tables and not re.search(r'(?i)\b(select|insert|update|delete|alter)\b', text):
            syntax_issues.append('No recognised SQL statement was found.')
    return {
        'table_count': len(tables),
        'tables': tables[:60],
        'has_primary_key': any(table['primary_keys'] for table in tables),
        'has_foreign_key': any(table['foreign_keys'] for table in tables),
        'statement_count': len(statements),
        'syntax_issues': syntax_issues,
    }


def _sqlite_authorizer(action, arg1, arg2, dbname, trigger):
    allowed = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
    }
    if action in allowed:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and str(arg1).lower() in (
        'table_info',
        'foreign_key_list',
        'table_list',
        'database_list',
    ):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def inspect_sqlite_bytes(data, name='database.sqlite'):
    """Inspect a SQLite database read-only using an authorizer."""
    if len(data) > MAX_DB_BYTES:
        return {'path': name, 'error': 'Database exceeds the inspection limit.', 'tables': []}
    if not data.startswith(b'SQLite format 3\x00'):
        return {'path': name, 'error': 'File is not a valid SQLite database.', 'tables': []}
    with tempfile.TemporaryDirectory(prefix='classforge-db-') as tmp:
        path = Path(tmp) / 'inspect.sqlite'
        path.write_bytes(data)
        uri = f'file:{path.as_posix()}?mode=ro&immutable=1'
        connection = None
        try:
            connection = sqlite3.connect(uri, uri=True, timeout=3)
            connection.set_authorizer(_sqlite_authorizer)
            cursor = connection.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            table_names = [row[0] for row in cursor.fetchall()][:80]
            tables = []
            for table_name in table_names:
                safe_name = str(table_name).replace('"', '""')
                cursor.execute(f'PRAGMA table_info("{safe_name}")')
                columns = [
                    {
                        'name': row[1],
                        'type': row[2],
                        'not_null': bool(row[3]),
                        'primary_key': bool(row[5]),
                    }
                    for row in cursor.fetchall()
                ][:80]
                cursor.execute(f'PRAGMA foreign_key_list("{safe_name}")')
                foreign_keys = [
                    {
                        'column': row[3],
                        'references_table': row[2],
                        'references_column': row[4],
                    }
                    for row in cursor.fetchall()
                ][:40]
                tables.append(
                    {
                        'name': table_name,
                        'columns': columns,
                        'foreign_keys': foreign_keys,
                        'primary_keys': [col['name'] for col in columns if col['primary_key']],
                    }
                )
            return {
                'path': name,
                'table_count': len(table_names),
                'tables': tables,
                'has_primary_key': any(table['primary_keys'] for table in tables),
                'has_foreign_key': any(table['foreign_keys'] for table in tables),
                'error': '',
            }
        except sqlite3.Error as exc:
            return {'path': name, 'error': f'{exc.__class__.__name__}: {exc}', 'tables': []}
        finally:
            if connection is not None:
                connection.close()


def _diagram_summary(paths, archive, entries, manifest):
    drawio = []
    mermaid = []
    images = []
    for path in paths:
        item = entries[path]
        ext = item.get('extension') or PurePosixPath(path).suffix.lower()
        if ext == '.drawio':
            text = _read(archive, path, item, 400_000)
            labels = re.findall(r'value="([^"]{1,120})"', text)
            drawio.append(
                {
                    'path': path,
                    'cells': len(re.findall(r'<mxCell\b', text)),
                    'labels': labels[:40],
                }
            )
        elif ext in ('.mmd', '.mermaid') or (
            ext in ('.md', '.txt') and path.lower().endswith(('erd.md', 'diagram.md'))
        ):
            text = _read(archive, path, item, 120_000)
            if 'erDiagram' in text or ext in ('.mmd', '.mermaid'):
                entities = sorted(set(MERMAID_ENTITY_RE.findall(text)))
                relationships = re.findall(
                    r'([A-Za-z_][A-Za-z0-9_]*)\s+([|}o{]+--[|{o]+)\s+([A-Za-z_][A-Za-z0-9_]*)',
                    text,
                )
                mermaid.append(
                    {
                        'path': path,
                        'entities': entities[:40],
                        'relationships': [
                            {'from': left, 'type': rel, 'to': right}
                            for left, rel, right in relationships[:60]
                        ],
                    }
                )
        elif ext in IMAGE_EXTENSIONS:
            images.append(path)
    return {
        'drawio': drawio,
        'mermaid': mermaid,
        'images': images[:60],
        'has_erd': bool(drawio or mermaid or any('erd' in path.lower() for path in images)),
    }


def extract_artifacts(archive_bytes, manifest, assignment=None):
    """Return a JSON-serialisable evidence bundle for one snapshot."""
    entries = _entry_map(manifest)
    paths = sorted(entries)
    results = {
        'readme': None,
        'docs': [],
        'sql': {'files': [], 'table_count': 0, 'has_primary_key': False,
                'has_foreign_key': False, 'syntax_issues': []},
        'databases': [],
        'erd': {'drawio': [], 'mermaid': [], 'images': [], 'has_erd': False},
        'tests': [],
        'project_files': [],
        'suspicious': [],
        'secrets': [],
        'structure': {
            'directories': [],
            'extensions': {},
            'entry_points': [],
            'top_level': [],
            'code_files': 0,
            'documentation_files': 0,
        },
    }
    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValidationError(f'Could not open archive for inspection: {exc.__class__.__name__}')

    with archive:
        directories = set()
        extensions = {}
        top_level = set()
        for path in paths:
            parts = path.split('/')
            top_level.add(parts[0])
            for index in range(1, len(parts)):
                directories.add('/'.join(parts[:index]))
            ext = entries[path].get('extension') or PurePosixPath(path).suffix.lower()
            extensions[ext or '(none)'] = extensions.get(ext or '(none)', 0) + 1

            item = entries[path]
            lower = path.lower()
            basename = PurePosixPath(lower).name
            if TEST_NAME_RE.match(basename):
                results['tests'].append(path)
            if ext in SQL_EXTENSIONS:
                text = _read(archive, path, item, 400_000)
                parsed = parse_sql(text)
                parsed['path'] = path
                results['sql']['files'].append(parsed)
                results['sql']['table_count'] += parsed['table_count']
                results['sql']['has_primary_key'] |= parsed['has_primary_key']
                results['sql']['has_foreign_key'] |= parsed['has_foreign_key']
                results['sql']['syntax_issues'].extend(parsed['syntax_issues'])
            if ext in DB_EXTENSIONS:
                if item.get('size', 0) <= MAX_DB_BYTES:
                    try:
                        data = archive.read(path)
                    except (KeyError, RuntimeError, OSError):
                        data = b''
                    results['databases'].append(inspect_sqlite_bytes(data, path))
                else:
                    results['databases'].append(
                        {'path': path, 'error': 'Database exceeds the inspection limit.', 'tables': []}
                    )
            if ext in DOC_EXTENSIONS:
                results['structure']['documentation_files'] += 1
            if ext in TEXT_EXTENSIONS and ext not in DOC_EXTENSIONS:
                results['structure']['code_files'] += 1
            if basename.startswith('readme') and results['readme'] is None:
                results['readme'] = {
                    'path': path,
                    'excerpt': _read(archive, path, item)[:MAX_EXCERPT],
                }
            if ext in DOC_EXTENSIONS and not basename.startswith('readme'):
                results['docs'].append(
                    {
                        'path': path,
                        'size': item.get('size', 0),
                        'excerpt': _read(archive, path, item, 20_000)[:1200]
                        if ext in ('.md', '.txt', '.rst')
                        else '',
                    }
                )
            if basename in (
                'manage.py', 'app.py', 'main.py', 'index.js', 'index.ts',
                'package.json', 'composer.json', 'requirements.txt',
                'pyproject.toml', 'pom.xml', 'build.gradle', 'dockerfile',
                'docker-compose.yml', 'docker-compose.yaml', '.env.example',
            ) or ext in ('.csproj', '.sln'):
                results['project_files'].append(
                    {'path': path, 'size': item.get('size', 0)}
                )
                if basename in ('manage.py', 'app.py', 'main.py', 'index.js', 'index.ts'):
                    results['structure']['entry_points'].append(path)
            if SECRET_FILENAMES.match(basename) and basename != '.env.example':
                results['secrets'].append(
                    {'path': path, 'kind': 'secret_file', 'line': 0}
                )

            if ext in TEXT_EXTENSIONS and item.get('size', 0) <= MAX_TEXT_BYTES:
                text = _read(archive, path, item)
                for kind, pattern in SECRET_PATTERNS:
                    match = pattern.search(text)
                    if match:
                        line = text[:match.start()].count('\n') + 1
                        results['secrets'].append(
                            {'path': path, 'kind': kind, 'line': line}
                        )
                        break
                for key, pattern, severity, message in SUSPICIOUS_PATTERNS:
                    match = pattern.search(text)
                    if match:
                        line = text[:match.start()].count('\n') + 1
                        results['suspicious'].append(
                            {
                                'path': path,
                                'kind': key,
                                'severity': severity,
                                'line': line,
                                'message': message,
                                'evidence': match.group(0)[:200],
                            }
                        )

        results['structure']['directories'] = sorted(directories)[:80]
        results['structure']['extensions'] = dict(
            sorted(extensions.items(), key=lambda pair: (-pair[1], pair[0]))[:20]
        )
        results['structure']['top_level'] = sorted(top_level)[:40]
        results['erd'] = _diagram_summary(paths, archive, entries, manifest)

    # De-duplicate by (path, kind, line).
    seen = set()
    deduped = []
    for item in results['secrets']:
        key = (item['path'], item['kind'], item['line'])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    results['secrets'] = deduped[:50]
    results['tests'] = sorted(set(results['tests']))[:100]
    return results


def artifact_overview(artifacts):
    """Compact text used in feedback and AI prompts."""
    structure = artifacts.get('structure', {})
    sql_info = artifacts.get('sql', {})
    return {
        'files': sum(structure.get('extensions', {}).values()),
        'code_files': structure.get('code_files', 0),
        'documentation_files': structure.get('documentation_files', 0),
        'has_readme': bool(artifacts.get('readme')),
        'sql_tables': sql_info.get('table_count', 0),
        'sql_primary_keys': bool(sql_info.get('has_primary_key')),
        'sql_foreign_keys': bool(sql_info.get('has_foreign_key')),
        'databases': len(artifacts.get('databases', [])),
        'has_erd': bool(artifacts.get('erd', {}).get('has_erd')),
        'tests': len(artifacts.get('tests', [])),
        'secrets': len(artifacts.get('secrets', [])),
        'suspicious': len(artifacts.get('suspicious', [])),
    }


def to_json(value):
    return json.loads(json.dumps(value, default=str))
