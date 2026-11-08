"""Read-only syntax highlighting for the saved-version file viewer.

This module never runs student code.  It only escapes text and wraps simple
lexical tokens in spans so the browser can render a readable code panel.
"""

from __future__ import annotations

import html
import posixpath
import re

MAX_HIGHLIGHT_LINES = 5000

LANGUAGE_BY_EXTENSION = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.jsx': 'JavaScript',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript',
    '.java': 'Java',
    '.php': 'PHP',
    '.rb': 'Ruby',
    '.go': 'Go',
    '.cs': 'C#',
    '.c': 'C',
    '.h': 'C',
    '.cpp': 'C++',
    '.hpp': 'C++',
    '.rs': 'Rust',
    '.kt': 'Kotlin',
    '.swift': 'Swift',
    '.dart': 'Dart',
    '.sql': 'SQL',
    '.html': 'HTML',
    '.htm': 'HTML',
    '.css': 'CSS',
    '.scss': 'SCSS',
    '.vue': 'Vue',
    '.sh': 'Shell',
    '.ps1': 'PowerShell',
    '.md': 'Markdown',
    '.rst': 'reStructuredText',
    '.txt': 'Text',
    '.json': 'JSON',
    '.yml': 'YAML',
    '.yaml': 'YAML',
    '.toml': 'TOML',
    '.ini': 'INI',
    '.cfg': 'Config',
    '.env': 'Env',
    '.xml': 'XML',
    '.svg': 'SVG',
    '.csv': 'CSV',
    '.mmd': 'Mermaid',
    '.mermaid': 'Mermaid',
    '.drawio': 'draw.io',
}

LANGUAGE_BY_FILENAME = {
    'dockerfile': 'Dockerfile',
    'makefile': 'Makefile',
    'procfile': 'Procfile',
}

_KEYWORDS = frozenset(
    """
    and as assert async await break case catch class const continue def default
    delete do elif else end enum except export extends false finally for from
    function global go if implements import in instanceof interface is lambda
    let new none not null of or package pass private protected public raise
    return select self static super switch this throw true try type typeof var
    void while with yield
    insert into update create table primary key foreign references join left
    right inner outer group by order having limit offset values set alter drop
    index view distinct on union all when then begin commit rollback
    """.split()
)

_C_FAMILY = {
    '.js', '.jsx', '.ts', '.tsx', '.java', '.php', '.go', '.cs', '.c', '.h',
    '.cpp', '.hpp', '.rs', '.kt', '.swift', '.dart', '.vue',
}
_HASH_FAMILY = {'.py', '.rb', '.sh', '.ps1', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.env'}
_SQL_EXTENSIONS = {'.sql'}
_JSON_EXTENSIONS = {'.json'}
_CSS_EXTENSIONS = {'.css', '.scss'}
_HTML_EXTENSIONS = {'.html', '.htm', '.xml', '.svg'}
_MARKDOWN_EXTENSIONS = {'.md', '.rst', '.mmd', '.mermaid'}

_TOKEN_CACHE = {}
_MARKDOWN_FENCE_RE = re.compile(r'^\s*(```|~~~)')
_MARKDOWN_HEADING_RE = re.compile(r'^(\s*)(#{1,6})(\s+)(.*)$')
_MARKDOWN_LIST_RE = re.compile(r'^(\s*)([-*+]|\d+\.)(\s+)(.*)$')
_MARKDOWN_INLINE_CODE_RE = re.compile(r'(`+)(.+?)\1')


def language_for_path(path):
    """Return a friendly language name for a manifest path."""
    name = posixpath.basename(str(path or '')).lower()
    if name in LANGUAGE_BY_FILENAME:
        return LANGUAGE_BY_FILENAME[name]
    extension = posixpath.splitext(name)[1].lower()
    return LANGUAGE_BY_EXTENSION.get(extension, 'Plain text')


def highlight_lines(text, path, max_lines=MAX_HIGHLIGHT_LINES):
    """Return ``(html_lines, truncated)`` for a text file.

    Every piece of source text is escaped before any markup is added.  The
    template may therefore mark these lines safe.
    """
    text = str(text or '').replace('\r\n', '\n').replace('\r', '\n')
    source_lines = text.split('\n')
    if len(source_lines) > 1 and source_lines[-1] == '':
        source_lines.pop()

    truncated = len(source_lines) > max_lines
    if truncated:
        source_lines = source_lines[:max_lines]
    text = '\n'.join(source_lines)

    language = language_for_path(path)
    if language == 'Markdown':
        return _highlight_markdown(text), truncated
    if language == 'Plain text' or language == 'Text':
        return [html.escape(line, quote=False) for line in source_lines], truncated

    syntax = _syntax_for(path)
    if syntax is None:
        return [html.escape(line, quote=False) for line in source_lines], truncated
    return _render_tokens(_tokenise(text, syntax)), truncated


def _syntax_for(path):
    extension = posixpath.splitext(str(path or ''))[1].lower()
    if extension == '.py':
        return {
            'line_comment': '#',
            'block_comment': None,
            'strings': ('"""', "'''", '"', "'"),
            'keywords': True,
            'tags': False,
        }
    if extension in _C_FAMILY:
        return {
            'line_comment': '//',
            'block_comment': ('/*', '*/'),
            'strings': ('"', "'", '`'),
            'keywords': True,
            'tags': extension == '.vue',
        }
    if extension in _SQL_EXTENSIONS:
        return {
            'line_comment': '--',
            'block_comment': ('/*', '*/'),
            'strings': ("'", '"', '`'),
            'keywords': True,
            'tags': False,
        }
    if extension in _HASH_FAMILY:
        return {
            'line_comment': '#',
            'block_comment': None,
            'strings': ('"', "'"),
            'keywords': True,
            'tags': False,
        }
    if extension in _HTML_EXTENSIONS:
        return {
            'line_comment': None,
            'block_comment': ('<!--', '-->'),
            'strings': (),
            'keywords': False,
            'tags': True,
        }
    if extension in _JSON_EXTENSIONS:
        return {
            'line_comment': None,
            'block_comment': None,
            'strings': ('"',),
            'keywords': True,
            'tags': False,
        }
    if extension in _CSS_EXTENSIONS:
        return {
            'line_comment': None,
            'block_comment': ('/*', '*/'),
            'strings': ('"', "'"),
            'keywords': False,
            'tags': False,
        }
    return None


def _token_pattern(syntax):
    cache_key = (
        syntax['line_comment'],
        syntax['block_comment'],
        syntax['strings'],
        syntax['keywords'],
        syntax['tags'],
    )
    cached = _TOKEN_CACHE.get(cache_key)
    if cached is not None:
        return cached

    parts = []
    comment_parts = []
    if syntax['block_comment']:
        opening, closing = syntax['block_comment']
        comment_parts.append(re.escape(opening) + r'.*?' + re.escape(closing))
    if syntax['line_comment']:
        comment_parts.append(re.escape(syntax['line_comment']) + r'[^\n]*')
    if comment_parts:
        parts.append('(?P<comment>' + '|'.join(comment_parts) + ')')

    string_parts = []
    for quote in syntax['strings']:
        if len(quote) == 3:
            string_parts.append(
                re.escape(quote) + r'.*?' + re.escape(quote)
            )
        else:
            escaped = re.escape(quote)
            string_parts.append(
                escaped + r'(?:\\.|[^' + escaped + r'\\])*' + escaped
            )
    if string_parts:
        parts.append('(?P<string>' + '|'.join(string_parts) + ')')

    if syntax['tags']:
        parts.append(r'(?P<tag></?[A-Za-z][A-Za-z0-9:.-]*)')

    parts.append(r'(?P<number>\b(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?)\b)')
    parts.append(r'(?P<word>[A-Za-z_][A-Za-z0-9_]*)')
    parts.append(r'(?P<operator>[+\-*/%=<>!&|^~]+)')
    pattern = re.compile('|'.join(parts), re.DOTALL)
    _TOKEN_CACHE[cache_key] = pattern
    return pattern


def _tokenise(text, syntax):
    pattern = _token_pattern(syntax)
    tokens = []
    position = 0
    for match in pattern.finditer(text):
        if match.start() > position:
            tokens.append(('plain', text[position:match.start()]))
        kind = match.lastgroup
        value = match.group()
        if kind == 'word':
            lowered = value.lower()
            if syntax['keywords'] and lowered in _KEYWORDS:
                kind = 'keyword'
            elif value[:1].isupper():
                kind = 'type'
            elif _next_non_space(text, match.end()) == '(':
                kind = 'function'
            else:
                kind = 'plain'
        tokens.append((kind, value))
        position = match.end()
    if position < len(text):
        tokens.append(('plain', text[position:]))
    return tokens


def _next_non_space(text, position):
    while position < len(text) and text[position] in ' \t':
        position += 1
    return text[position:position + 1]


def _render_tokens(tokens):
    parts = []
    for kind, value in tokens:
        chunks = value.split('\n')
        for index, chunk in enumerate(chunks):
            if index:
                parts.append('\n')
            if not chunk:
                continue
            escaped = html.escape(chunk, quote=False)
            if kind == 'plain':
                parts.append(escaped)
            else:
                parts.append(
                    f'<span class="cf-token cf-token--{kind}">{escaped}</span>'
                )
    lines = ''.join(parts).split('\n')
    if len(lines) > 1 and lines[-1] == '':
        lines.pop()
    return lines or ['']


def _highlight_markdown(text):
    lines = []
    in_fence = False
    for line in text.split('\n'):
        if _MARKDOWN_FENCE_RE.match(line):
            in_fence = not in_fence
            lines.append(
                '<span class="cf-token cf-token--comment">'
                f'{html.escape(line, quote=False)}</span>'
            )
            continue
        if in_fence:
            lines.append(
                '<span class="cf-token cf-token--string">'
                f'{html.escape(line, quote=False)}</span>'
            )
            continue

        heading = _MARKDOWN_HEADING_RE.match(line)
        if heading:
            lines.append(
                html.escape(heading.group(1), quote=False)
                + '<span class="cf-token cf-token--keyword">'
                + html.escape(heading.group(2), quote=False)
                + '</span>'
                + html.escape(heading.group(3), quote=False)
                + _markdown_inline(heading.group(4))
            )
            continue

        item = _MARKDOWN_LIST_RE.match(line)
        if item:
            lines.append(
                html.escape(item.group(1), quote=False)
                + '<span class="cf-token cf-token--keyword">'
                + html.escape(item.group(2), quote=False)
                + '</span>'
                + html.escape(item.group(3), quote=False)
                + _markdown_inline(item.group(4))
            )
            continue

        lines.append(_markdown_inline(line))
    return lines or ['']


def _markdown_inline(text):
    parts = []
    position = 0
    for match in _MARKDOWN_INLINE_CODE_RE.finditer(text):
        if match.start() > position:
            parts.append(html.escape(text[position:match.start()], quote=False))
        parts.append(
            '<span class="cf-token cf-token--string">'
            f'{html.escape(match.group(0), quote=False)}</span>'
        )
        position = match.end()
    if position < len(text):
        parts.append(html.escape(text[position:], quote=False))
    return ''.join(parts)
