"""Turn instructor guidelines into an explicit, checkable comparison.

The assessment pipeline used to score projects mostly from generic file
checks.  This module parses the assignment's free-text guidelines (and the
structured requirement fields) into small, named requirements, then compares
each one with the saved project files.

The comparison is deliberately conservative:

* explicit files and folders are checked against the saved manifest;
* known features (login, CRUD, search, ERD, tests, ...) are looked for in
  source, SQL, database schemas, ERDs and documentation;
* a feature that is only mentioned in documentation is reported as "partly
  met", never as fully met;
* unknown wording becomes a "needs teacher review" item instead of a guessed
  pass or fail.

Nothing here executes student code, runs tests, or connects to a database.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from fnmatch import fnmatch

CHECK_PASS = 'pass'
CHECK_WARN = 'warn'
CHECK_FAIL = 'fail'
CHECK_SKIPPED = 'skipped'

MAX_REQUIREMENTS = 40
MAX_EVIDENCE_PATHS = 8
MAX_TERMS = 6

STATUS_VALUES = {
    CHECK_PASS: Decimal('1.0'),
    CHECK_WARN: Decimal('0.5'),
    CHECK_FAIL: Decimal('0'),
}

# Words that carry no checkable meaning on their own.  Keeping this list
# generous prevents feedback like "the guideline asks for word 'must'".
STOPWORDS = {
    'about', 'above', 'after', 'again', 'against', 'all', 'also', 'and',
    'any', 'are', 'because', 'been', 'before', 'being', 'below', 'between',
    'both', 'build', 'built', 'can', 'could', 'create', 'created', 'creates',
    'demo', 'describe', 'described', 'describes', 'design', 'develop',
    'developed', 'display', 'does', 'doing', 'each', 'ensure', 'example',
    'examples', 'expected', 'file', 'files', 'final', 'following', 'from',
    'full', 'give', 'have', 'having', 'implement', 'implemented', 'include',
    'included', 'includes', 'including', 'into', 'its', 'just', 'like',
    'made', 'make', 'makes', 'minimum', 'more', 'most', 'must', 'need',
    'needs', 'only', 'other', 'over', 'please', 'provide', 'provided',
    'project', 'projects', 'require', 'required', 'requires', 'should',
    'show', 'shown', 'some', 'such', 'support', 'supported', 'sure', 'system',
    'systems', 'than', 'that', 'their', 'them', 'then', 'there', 'these',
    'they', 'this', 'those', 'through', 'under', 'use', 'used', 'uses',
    'using', 'very', 'want', 'well', 'were', 'what', 'when', 'where', 'which',
    'while', 'will', 'with', 'within', 'without', 'work', 'working', 'would',
    'your', 'you', 'student', 'students', 'teacher', 'teachers', 'class',
    'course', 'assignment', 'submission', 'submitted', 'submit', 'save',
    'saved', 'version', 'versions', 'code', 'source', 'program', 'app',
}

REQUIREMENT_MARKERS = (
    'must', 'should', 'shall', 'required', 'require', 'requires', 'need',
    'needs', 'include', 'includes', 'including', 'implement', 'create',
    'build', 'develop', 'add', 'provide', 'use', 'using', 'ensure', 'support',
    'allow', 'expected', 'at least', 'minimum', 'complete', 'demonstrate',
    'contain', 'has to', 'have to', 'follow', 'design', 'document',
)

MANDATORY_MARKERS = (
    'must', 'required', 'require', 'requires', 'shall', 'has to', 'have to',
    'mandatory', 'minimum', 'at least',
)

DOCUMENT_EXTENSIONS = (
    '.md', '.txt', '.rst', '.pdf', '.doc', '.docx',
)

FILENAME_RE = re.compile(
    r'\b([A-Za-z0-9_][A-Za-z0-9_./\\-]*\.'
    r'(?:py|js|jsx|ts|tsx|java|php|rb|go|cs|c|cpp|h|hpp|rs|kt|swift|sql|'
    r'sqlite|sqlite3|db|html|css|scss|vue|dart|json|md|txt|rst|pdf|doc|docx|'
    r'drawio|mmd|yml|yaml|xml|csv|xlsx|pptx|zip))\b',
    re.IGNORECASE,
)

DIRECTORY_RE = re.compile(
    r'\b(?:in|inside|under|within|into)\s+(?:the\s+)?["\']?'
    r'([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)["\']?\s+'
    r'(?:folder|directory)',
    re.IGNORECASE,
)

# Known features.  ``evidence`` says where proof should live:
#   code -> source files
#   data -> SQL files, SQLite databases, or ERDs
#   docs -> README / documentation files
#   any  -> anywhere in the saved version
FEATURE_RULES = (
    {
        'key': 'login',
        'label': 'Login / authentication',
        'category': 'security',
        'evidence': 'code',
        'terms': ('login', 'log in', 'sign in', 'signin', 'authentication',
                  'authenticate'),
        'next_step': 'Add a working login or authentication feature.',
    },
    {
        'key': 'registration',
        'label': 'User registration',
        'category': 'security',
        'evidence': 'code',
        'terms': ('register', 'registration', 'sign up', 'signup',
                  'create account'),
        'next_step': 'Add a registration / sign-up flow for new users.',
    },
    {
        'key': 'authorization',
        'label': 'Roles and permissions',
        'category': 'security',
        'evidence': 'code',
        'terms': ('role', 'roles', 'permission', 'permissions',
                  'role-based', 'user role', 'access control'),
        'next_step': 'Add user roles or permissions and enforce them in the code.',
    },
    {
        'key': 'password_security',
        'label': 'Secure passwords',
        'category': 'security',
        'evidence': 'code',
        'terms': ('password hash', 'hashed password', 'hash password',
                  'bcrypt', 'argon2', 'pbkdf2'),
        'next_step': 'Hash passwords with a dedicated password hashing function.',
    },
    {
        'key': 'crud',
        'label': 'Create, read, update, delete (CRUD)',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('crud', 'create read update delete',
                  'add edit delete', 'add, edit and delete'),
        'next_step': 'Add CRUD actions for the main records in the system.',
    },
    {
        'key': 'search',
        'label': 'Search / filtering',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('search', 'filter', 'filtering', 'find records'),
        'next_step': 'Add a search or filter feature for the main records.',
    },
    {
        'key': 'validation',
        'label': 'Input validation',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('validation', 'validate', 'input validation',
                  'form validation'),
        'next_step': 'Validate user input before saving it.',
    },
    {
        'key': 'database',
        'label': 'Database / schema',
        'category': 'database',
        'evidence': 'data',
        'terms': ('database', 'schema', 'sql', 'table', 'tables', 'mysql',
                  'postgres', 'postgresql', 'sqlite', 'mongodb', 'oracle',
                  'sql server'),
        'next_step': 'Include the database schema (for example schema.sql).',
    },
    {
        'key': 'erd',
        'label': 'ERD / database diagram',
        'category': 'database',
        'evidence': 'data',
        'terms': ('erd', 'entity relationship', 'er diagram',
                  'database diagram', 'schema diagram'),
        'next_step': 'Add an ERD that shows the tables and their relationships.',
    },
    {
        'key': 'api',
        'label': 'API / endpoints',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('api', 'rest', 'restful', 'endpoint', 'endpoints'),
        'next_step': 'Add the API endpoints described in the guidelines.',
    },
    {
        'key': 'dashboard',
        'label': 'Dashboard / admin panel',
        'category': 'design',
        'evidence': 'code',
        'terms': ('dashboard', 'admin panel', 'admin dashboard'),
        'next_step': 'Add the dashboard or admin panel described in the guidelines.',
    },
    {
        'key': 'reports',
        'label': 'Reports / export',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('report', 'reports', 'export', 'print', 'csv', 'excel',
                  'pdf report'),
        'next_step': 'Add the report or export feature described in the guidelines.',
    },
    {
        'key': 'file_upload',
        'label': 'File uploads',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('upload', 'uploads', 'attachment', 'image upload',
                  'file upload'),
        'next_step': 'Add the file upload feature described in the guidelines.',
    },
    {
        'key': 'tests',
        'label': 'Automated tests',
        'category': 'testing',
        'evidence': 'tests',
        'terms': ('unit test', 'unit tests', 'pytest', 'unittest', 'test case',
                  'test cases', 'automated test', 'automated tests', 'tests',
                  'tested', 'testing'),
        'next_step': 'Add test files for the main features.',
    },
    {
        'key': 'documentation',
        'label': 'Documentation / README',
        'category': 'documentation',
        'evidence': 'docs',
        'terms': ('readme', 'documentation', 'user manual', 'manual', 'docs'),
        'next_step': 'Add or extend the README/documentation.',
    },
    {
        'key': 'diagrams',
        'label': 'Design diagrams',
        'category': 'design',
        'evidence': 'data',
        'terms': ('flowchart', 'use case diagram', 'use-case diagram',
                  'class diagram', 'uml', 'gantt', 'diagram'),
        'next_step': 'Add the diagram(s) described in the guidelines.',
    },
    {
        'key': 'security',
        'label': 'Security practices',
        'category': 'security',
        'evidence': 'code',
        'terms': ('sql injection', 'csrf', 'xss', 'secure coding',
                  'security', 'sanitize', 'sanitise'),
        'next_step': 'Apply the security practices described in the guidelines.',
    },
    {
        'key': 'pagination',
        'label': 'Pagination',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('pagination', 'paginate', 'paging'),
        'next_step': 'Add pagination to long lists.',
    },
    {
        'key': 'notifications',
        'label': 'Notifications',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('notification', 'notifications', 'email alert', 'alerts'),
        'next_step': 'Add the notification feature described in the guidelines.',
    },
    {
        'key': 'charts',
        'label': 'Charts / analytics',
        'category': 'design',
        'evidence': 'code',
        'terms': ('chart', 'charts', 'graph', 'analytics', 'statistics'),
        'next_step': 'Add the charts or analytics described in the guidelines.',
    },
    {
        'key': 'payment',
        'label': 'Payment / checkout',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('payment', 'checkout', 'billing', 'invoice'),
        'next_step': 'Add the payment/checkout feature described in the guidelines.',
    },
    {
        'key': 'inventory',
        'label': 'Inventory / stock',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('inventory', 'stock', 'product', 'products'),
        'next_step': 'Add the inventory/stock feature described in the guidelines.',
    },
    {
        'key': 'library',
        'label': 'Library / borrowing',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('library', 'borrow', 'borrowing', 'book', 'books'),
        'next_step': 'Add the library/borrowing features described in the guidelines.',
    },
    {
        'key': 'attendance',
        'label': 'Attendance',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('attendance', 'present', 'absent', 'time in', 'time out'),
        'next_step': 'Add the attendance feature described in the guidelines.',
    },
    {
        'key': 'enrollment',
        'label': 'Enrollment / registration records',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('enrollment', 'enrolment', 'enroll', 'enrol', 'registrar'),
        'next_step': 'Add the enrollment feature described in the guidelines.',
    },
    {
        'key': 'messaging',
        'label': 'Messaging / chat',
        'category': 'implementation',
        'evidence': 'code',
        'terms': ('chat', 'message', 'messaging', 'inbox'),
        'next_step': 'Add the messaging feature described in the guidelines.',
    },
)

TECHNOLOGY_RULES = (
    {'label': 'Python', 'category': 'implementation',
     'terms': ('python',)},
    {'label': 'Django', 'category': 'implementation',
     'terms': ('django',)},
    {'label': 'Flask', 'category': 'implementation',
     'terms': ('flask',)},
    {'label': 'PHP', 'category': 'implementation',
     'terms': ('php',)},
    {'label': 'Laravel', 'category': 'implementation',
     'terms': ('laravel',)},
    {'label': 'JavaScript', 'category': 'implementation',
     'terms': ('javascript', 'js')},
    {'label': 'TypeScript', 'category': 'implementation',
     'terms': ('typescript', 'ts')},
    {'label': 'React', 'category': 'implementation',
     'terms': ('react',)},
    {'label': 'Vue', 'category': 'implementation',
     'terms': ('vue', 'vuejs')},
    {'label': 'Angular', 'category': 'implementation',
     'terms': ('angular',)},
    {'label': 'Node.js', 'category': 'implementation',
     'terms': ('node', 'nodejs', 'node.js')},
    {'label': 'Express', 'category': 'implementation',
     'terms': ('express',)},
    {'label': 'Java', 'category': 'implementation',
     'terms': ('java',)},
    {'label': 'Spring', 'category': 'implementation',
     'terms': ('spring',)},
    {'label': 'C# / .NET', 'category': 'implementation',
     'terms': ('c#', 'csharp', '.net', 'dotnet')},
    {'label': 'Ruby on Rails', 'category': 'implementation',
     'terms': ('ruby', 'rails')},
    {'label': 'MySQL', 'category': 'database',
     'terms': ('mysql',)},
    {'label': 'PostgreSQL', 'category': 'database',
     'terms': ('postgres', 'postgresql')},
    {'label': 'SQLite', 'category': 'database',
     'terms': ('sqlite',)},
    {'label': 'MongoDB', 'category': 'database',
     'terms': ('mongodb', 'mongo')},
    {'label': 'Firebase', 'category': 'database',
     'terms': ('firebase',)},
    {'label': 'Bootstrap', 'category': 'design',
     'terms': ('bootstrap',)},
    {'label': 'Tailwind CSS', 'category': 'design',
     'terms': ('tailwind',)},
    {'label': 'Docker', 'category': 'implementation',
     'terms': ('docker',)},
    {'label': 'Git', 'category': 'implementation',
     'terms': ('git', 'github', 'gitlab')},
    {'label': 'HTML/CSS', 'category': 'design',
     'terms': ('html', 'css')},
)


# ---------------------------------------------------------------------------
# Requirement extraction
# ---------------------------------------------------------------------------

def _clean(value):
    if not isinstance(value, str):
        return ''
    return re.sub(r'\s+', ' ', value.replace('\r\n', '\n').replace('\r', '\n')).strip()


def _shorten(value, limit=110):
    text = _clean(value)
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + '…'


def _chunks(text):
    """Split free text into short, checkable requirement-sized chunks."""
    text = _clean(text)
    if not text:
        return []
    chunks = []
    for raw_line in re.split(r'[\n;]+', text):
        line = raw_line.strip()
        line = re.sub(r'^(?:[-*•]+|\d+[.)])\s*', '', line)
        if not line:
            continue
        if len(line) <= 220:
            chunks.append(line)
        else:
            chunks.extend(
                part.strip()
                for part in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', line)
                if part.strip()
            )
    return [chunk for chunk in chunks if 3 <= len(chunk) <= 300]


def _term_in_text(term, text):
    term = term.strip().lower()
    if not term:
        return False
    text = text.lower()
    if ' ' in term or len(term) >= 4:
        return term in text
    return re.search(r'(?<![a-z0-9])' + re.escape(term) + r'(?![a-z0-9])', text) is not None


def _is_requirement_chunk(chunk):
    lower = chunk.lower()
    words = lower.split()
    if len(words) < 2:
        return False
    if chunk.endswith(':') and len(words) <= 5:
        return False
    if any(marker in lower for marker in REQUIREMENT_MARKERS):
        return True
    if FILENAME_RE.search(chunk) or DIRECTORY_RE.search(chunk):
        return True
    return any(
        _term_in_text(term, lower)
        for rule in FEATURE_RULES
        for term in rule['terms']
    )


def _is_mandatory(chunk):
    lower = chunk.lower()
    return any(marker in lower for marker in MANDATORY_MARKERS)


def _significant_terms(text):
    lower = re.sub(r'[\\/]', ' ', text.lower())
    tokens = re.findall(r'[a-z][a-z0-9+#._-]{2,}', lower)
    terms = []
    for token in tokens:
        token = token.strip('._-')
        if len(token) < 4:
            continue
        if token in STOPWORDS or token.isdigit():
            continue
        if token in terms:
            continue
        terms.append(token)
        if len(terms) >= MAX_TERMS:
            break
    return terms


def _infer_category(text):
    lower = text.lower()
    if any(word in lower for word in (
        'readme', 'documentation', 'manual', 'report', 'write-up', 'writeup',
    )):
        return 'documentation'
    if any(word in lower for word in (
        'database', 'schema', 'sql', 'table', 'erd', 'entity', 'normal',
    )):
        return 'database'
    if any(word in lower for word in ('test', 'pytest', 'unittest')):
        return 'testing'
    if any(word in lower for word in (
        'login', 'auth', 'password', 'security', 'permission', 'role',
    )):
        return 'security'
    if any(word in lower for word in (
        'design', 'ui', 'interface', 'page', 'dashboard', 'chart', 'diagram',
    )):
        return 'design'
    return 'implementation'


def _match_feature_rules(chunk):
    matched = []
    lower = chunk.lower()
    for rule in FEATURE_RULES:
        if any(_term_in_text(term, lower) for term in rule['terms']):
            matched.append(rule)
    return matched


def _match_technologies(chunk):
    matched = []
    lower = chunk.lower()
    for rule in TECHNOLOGY_RULES:
        if any(_term_in_text(term, lower) for term in rule['terms']):
            matched.append(rule)
    return matched


def extract_requirements(assignment):
    """Return the assignment's guidelines as explicit requirement records."""
    requirements = []
    seen = set()

    def add(kind, label, text, *, target='', terms=(), mandatory=False,
            category='', source='guidelines', evidence='any', next_step=''):
        identity = (
            kind,
            (target or label or text).strip().lower(),
            tuple(sorted({term.lower() for term in terms})),
        )
        if identity in seen:
            return
        seen.add(identity)
        requirements.append(
            {
                'id': f'req-{len(requirements) + 1}',
                'kind': kind,
                'label': _shorten(label, 160),
                'text': _shorten(text, 300),
                'target': target,
                'terms': list(terms),
                'mandatory': bool(mandatory),
                'category': category or _infer_category(f'{label} {text}'),
                'source': source,
                'evidence': evidence,
                'next_step': next_step,
            }
        )

    for value in getattr(assignment, 'required_files_list', []):
        add(
            'file',
            f'Required file: {value}',
            f'The assignment requires the file "{value}".',
            target=value,
            mandatory=True,
            category='implementation',
            source='required_files',
            evidence='file',
        )

    for value in getattr(assignment, 'required_directories_list', []):
        add(
            'directory',
            f'Required folder: {value}',
            f'The assignment requires the folder "{value}".',
            target=value,
            mandatory=True,
            category='implementation',
            source='required_directories',
            evidence='directory',
        )

    documentation = (getattr(assignment, 'documentation_requirements', '') or '').strip()
    for chunk in _chunks(documentation):
        terms = _significant_terms(chunk)
        add(
            'documentation',
            f'Documentation: {_shorten(chunk, 80)}',
            chunk,
            terms=terms,
            mandatory=_is_mandatory(chunk),
            category='documentation',
            source='documentation_requirements',
            evidence='docs',
            next_step='Add or extend the README/documentation described in the assignment.',
        )

    sources = (
        ('description', getattr(assignment, 'description', '') or ''),
        ('expected_outcomes', getattr(assignment, 'expected_outcomes', '') or ''),
        ('guidelines', getattr(assignment, 'guidelines', '') or ''),
    )
    for source, text in sources:
        for chunk in _chunks(text):
            if not _is_requirement_chunk(chunk):
                continue
            mandatory = _is_mandatory(chunk)
            found_specific = False

            for filename in FILENAME_RE.findall(chunk):
                filename = filename.replace('\\', '/').lstrip('./')
                add(
                    'file',
                    f'File mentioned: {filename}',
                    chunk,
                    target=filename,
                    mandatory=mandatory,
                    category='implementation',
                    source=source,
                    evidence='file',
                )
                found_specific = True

            for directory in DIRECTORY_RE.findall(chunk):
                directory = directory.replace('\\', '/').strip('./')
                if not directory or '.' in directory.rsplit('/', 1)[-1]:
                    continue
                add(
                    'directory',
                    f'Folder mentioned: {directory}',
                    chunk,
                    target=directory,
                    mandatory=mandatory,
                    category='implementation',
                    source=source,
                    evidence='directory',
                )
                found_specific = True

            for rule in _match_feature_rules(chunk):
                add(
                    'feature',
                    rule['label'],
                    chunk,
                    terms=rule['terms'],
                    mandatory=mandatory,
                    category=rule['category'],
                    source=source,
                    evidence=rule['evidence'],
                    next_step=rule['next_step'],
                )
                found_specific = True

            for rule in _match_technologies(chunk):
                add(
                    'technology',
                    f'Technology: {rule["label"]}',
                    chunk,
                    terms=rule['terms'],
                    mandatory=mandatory,
                    category=rule['category'],
                    source=source,
                    evidence='code',
                    next_step=f'Use {rule["label"]} in the project as the guidelines ask.',
                )
                found_specific = True

            if found_specific:
                continue

            terms = _significant_terms(chunk)
            if not terms:
                continue
            add(
                'keyword',
                _shorten(chunk, 110),
                chunk,
                terms=terms,
                mandatory=mandatory,
                category=_infer_category(chunk),
                source=source,
                evidence='any',
                next_step='Make the requested item clearly visible in the saved files.',
            )

            if len(requirements) >= MAX_REQUIREMENTS:
                break
        if len(requirements) >= MAX_REQUIREMENTS:
            break

    return requirements[:MAX_REQUIREMENTS]


# ---------------------------------------------------------------------------
# Evidence matching
# ---------------------------------------------------------------------------

def _manifest_paths(artifacts):
    structure = artifacts.get('structure', {})
    paths = []
    for value in structure.get('paths', []) or []:
        if isinstance(value, str):
            paths.append(value)
    # Older snapshots only store the top level; include every known path so
    # comparisons stay useful when the manifest-derived list is absent.
    for source in (
        [artifacts.get('readme') or {}],
        artifacts.get('docs', []),
        artifacts.get('tests', []),
        artifacts.get('text', []),
        artifacts.get('sql', {}).get('files', []),
        artifacts.get('databases', []),
        artifacts.get('project_files', []),
        artifacts.get('suspicious', []),
        artifacts.get('secrets', []),
    ):
        for item in source:
            if isinstance(item, dict) and item.get('path'):
                paths.append(item['path'])
            elif isinstance(item, str):
                paths.append(item)
    return list(dict.fromkeys(path for path in paths if path))


def _build_corpus(artifacts):
    """Return searchable evidence sources with a kind for weighting."""
    sources = []

    readme = artifacts.get('readme') or {}
    if readme.get('excerpt'):
        sources.append(
            {
                'kind': 'readme',
                'path': readme.get('path', 'README'),
                'text': readme.get('excerpt', ''),
            }
        )
    for item in artifacts.get('docs', []):
        if not isinstance(item, dict):
            continue
        text = item.get('excerpt') or ''
        sources.append(
            {
                'kind': 'doc',
                'path': item.get('path', ''),
                'text': f'{item.get("path", "")} {text}',
            }
        )
    for item in artifacts.get('text', []):
        if not isinstance(item, dict):
            continue
        sources.append(
            {
                'kind': 'code',
                'path': item.get('path', ''),
                'text': f'{item.get("path", "")} {item.get("text", "")}',
            }
        )
    for item in artifacts.get('sql', {}).get('files', []):
        if not isinstance(item, dict):
            continue
        parts = [item.get('path', '')]
        for table in item.get('tables', []) or []:
            parts.append(str(table.get('name') or ''))
            for column in table.get('columns', []) or []:
                parts.append(str(column.get('name') or ''))
        sources.append(
            {'kind': 'sql', 'path': item.get('path', ''), 'text': ' '.join(parts)}
        )
    for item in artifacts.get('databases', []):
        if not isinstance(item, dict):
            continue
        parts = [item.get('path', '')]
        for table in item.get('tables', []) or []:
            parts.append(str(table.get('name') or ''))
            for column in table.get('columns', []) or []:
                parts.append(str(column.get('name') or ''))
        sources.append(
            {'kind': 'database', 'path': item.get('path', ''), 'text': ' '.join(parts)}
        )
    erd = artifacts.get('erd', {})
    for item in erd.get('drawio', []) or []:
        if not isinstance(item, dict):
            continue
        sources.append(
            {
                'kind': 'erd',
                'path': item.get('path', ''),
                'text': ' '.join([item.get('path', '')] + [str(label) for label in item.get('labels', []) or []]),
            }
        )
    for item in erd.get('mermaid', []) or []:
        if not isinstance(item, dict):
            continue
        sources.append(
            {
                'kind': 'erd',
                'path': item.get('path', ''),
                'text': ' '.join([item.get('path', '')] + [str(name) for name in item.get('entities', []) or []]),
            }
        )
    for path in erd.get('images', []) or []:
        sources.append({'kind': 'image', 'path': str(path), 'text': str(path)})
    for path in artifacts.get('tests', []) or []:
        sources.append({'kind': 'test', 'path': str(path), 'text': str(path)})

    paths = _manifest_paths(artifacts)
    if paths:
        sources.append({'kind': 'path', 'path': '', 'text': ' '.join(paths)})
    return sources


def _find_term_evidence(terms, sources):
    matched_terms = []
    matched_sources = {}
    for term in terms:
        for source in sources:
            if _term_in_text(term, source['text']):
                matched_terms.append(term)
                matched_sources.setdefault(source['kind'], []).append(source['path'])
                break
    return matched_terms, {
        kind: list(dict.fromkeys(path for path in paths if path))[:MAX_EVIDENCE_PATHS]
        for kind, paths in matched_sources.items()
    }


def _paths_for(matched_sources, kinds):
    paths = []
    for kind in kinds:
        paths.extend(matched_sources.get(kind, []))
    return list(dict.fromkeys(paths))[:MAX_EVIDENCE_PATHS]


def _format_paths(paths, limit=4):
    paths = [path for path in paths if path][:limit]
    if not paths:
        return ''
    return ', '.join(paths)


def _match_file(target, paths):
    target = target.replace('\\', '/').strip().lower().lstrip('./')
    if not target:
        return ''
    if any(char in target for char in '*?['):
        for path in paths:
            lower = path.lower()
            if (
                fnmatch(lower, target)
                or fnmatch(lower, f'*/{target}')
                or fnmatch(lower.rsplit('/', 1)[-1], target)
            ):
                return path
        return ''
    for path in paths:
        lower = path.lower()
        if (
            lower == target
            or lower.endswith('/' + target)
            or lower.rsplit('/', 1)[-1] == target
        ):
            return path
    return ''


def _match_directory(target, paths):
    target = target.replace('\\', '/').strip().lower().strip('/')
    if not target:
        return ''
    for path in paths:
        lower = path.lower()
        if lower == target or lower.startswith(target + '/'):
            return path
    return ''


def _evidence_status(rule_evidence, matched_sources, matched_terms):
    if not matched_terms:
        return CHECK_FAIL
    if rule_evidence == 'code':
        if matched_sources.get('code'):
            return CHECK_PASS
        if matched_sources.get('sql') or matched_sources.get('database'):
            return CHECK_PASS
        return CHECK_WARN
    if rule_evidence == 'data':
        if (
            matched_sources.get('sql')
            or matched_sources.get('database')
            or matched_sources.get('erd')
            or matched_sources.get('image')
            or matched_sources.get('test')
        ):
            return CHECK_PASS
        if matched_sources.get('code'):
            return CHECK_PASS
        return CHECK_WARN
    if rule_evidence == 'docs':
        if matched_sources.get('readme') or matched_sources.get('doc'):
            return CHECK_PASS
        return CHECK_WARN
    if rule_evidence == 'tests':
        if matched_sources.get('test'):
            return CHECK_PASS
        if matched_sources.get('code'):
            # A test-like function can live in a source file; report it as
            # partly met and let the teacher confirm.
            return CHECK_WARN
        return CHECK_WARN
    return CHECK_PASS


def _status_message(requirement, status, matched_terms, matched_paths):
    label = requirement.get('label') or requirement.get('text') or 'requirement'
    found = _format_paths(matched_paths)
    if status == CHECK_PASS:
        if found:
            return f'Met. Evidence found in {found}.'
        return f'Met. Evidence for "{label}" was found in the saved files.'
    if status == CHECK_WARN:
        if matched_terms:
            if found:
                return (
                    f'Partly met. "{label}" is mentioned in {found}, but the '
                    'expected source or data evidence was not found.'
                )
            return (
                f'Partly met. "{label}" was mentioned, but the expected '
                'source or data evidence was not found.'
            )
        return (
            f'Could not confirm "{label}" from the saved files. The teacher '
            'should check this manually.'
        )
    return (
        f'Not met. The guideline asks for "{label}", but no matching file '
        'or content was found.'
    )


def evaluate_requirements(requirements, artifacts):
    """Compare each requirement with the saved artifacts."""
    paths = _manifest_paths(artifacts)
    sources = _build_corpus(artifacts)
    items = []

    for requirement in requirements:
        kind = requirement['kind']
        status = CHECK_SKIPPED
        matched_terms = []
        matched_paths = []

        if kind == 'file':
            path = _match_file(requirement.get('target', ''), paths)
            if path:
                status = CHECK_PASS
                matched_paths = [path]
            else:
                status = CHECK_FAIL if requirement['mandatory'] else CHECK_WARN
        elif kind == 'directory':
            path = _match_directory(requirement.get('target', ''), paths)
            if path:
                status = CHECK_PASS
                matched_paths = [path]
            else:
                status = CHECK_FAIL if requirement['mandatory'] else CHECK_WARN
        elif kind == 'documentation':
            docs = [
                source for source in sources
                if source['kind'] in ('readme', 'doc')
            ]
            if docs:
                terms = requirement.get('terms') or []
                if terms:
                    matched_terms, matched_sources = _find_term_evidence(terms, docs)
                    if matched_terms:
                        status = CHECK_PASS
                        matched_paths = _paths_for(matched_sources, ('readme', 'doc'))
                    else:
                        status = CHECK_WARN
                        matched_paths = [source['path'] for source in docs][:MAX_EVIDENCE_PATHS]
                else:
                    status = CHECK_PASS
                    matched_paths = [source['path'] for source in docs][:MAX_EVIDENCE_PATHS]
            else:
                status = CHECK_FAIL if requirement['mandatory'] else CHECK_WARN
        else:
            terms = requirement.get('terms') or []
            if not terms:
                status = CHECK_SKIPPED
            else:
                matched_terms, matched_sources = _find_term_evidence(terms, sources)
                status = _evidence_status(
                    requirement.get('evidence', 'any'),
                    matched_sources,
                    matched_terms,
                )
                matched_paths = _paths_for(
                    matched_sources,
                    ('code', 'sql', 'database', 'erd', 'image', 'readme', 'doc', 'test'),
                )
                if status == CHECK_FAIL and not requirement['mandatory']:
                    status = CHECK_WARN
                if not matched_terms:
                    status = CHECK_WARN if not requirement['mandatory'] else CHECK_FAIL

        item = {
            **requirement,
            'status': status,
            'status_label': {
                CHECK_PASS: 'Met',
                CHECK_WARN: 'Partly met',
                CHECK_FAIL: 'Not met',
                CHECK_SKIPPED: 'Needs review',
            }.get(status, 'Needs review'),
            'message': _status_message(
                requirement, status, matched_terms, matched_paths
            ),
            'evidence': _format_paths(matched_paths, limit=6),
            'matched_terms': sorted(set(matched_terms))[:MAX_TERMS],
        }
        items.append(item)

    return _summarise(items)


def _summarise(items):
    counts = {
        CHECK_PASS: 0,
        CHECK_WARN: 0,
        CHECK_FAIL: 0,
        CHECK_SKIPPED: 0,
    }
    weighted_points = Decimal('0')
    weighted_total = Decimal('0')
    category_points = {}
    category_totals = {}

    for item in items:
        status = item['status']
        counts[status] = counts.get(status, 0) + 1
        weight = Decimal('1.0') if item.get('mandatory') else Decimal('0.75')
        value = STATUS_VALUES.get(status)
        if value is None:
            continue
        category = item.get('category') or 'implementation'
        category_points[category] = category_points.get(category, Decimal('0')) + weight * value
        category_totals[category] = category_totals.get(category, Decimal('0')) + weight
        weighted_points += weight * value
        weighted_total += weight

    coverage = (
        (weighted_points / weighted_total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if weighted_total
        else None
    )
    categories = {
        category: (
            (category_points[category] / category_totals[category]).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        )
        for category in category_totals
        if category_totals[category]
    }

    mandatory_items = [item for item in items if item.get('mandatory')]
    met_mandatory = sum(
        1 for item in mandatory_items if item['status'] == CHECK_PASS
    )
    missing = counts.get(CHECK_FAIL, 0) + counts.get(CHECK_WARN, 0)
    if not items:
        summary = 'No explicit guideline requirements were configured for this assignment.'
    elif counts.get(CHECK_FAIL, 0):
        summary = (
            f'{counts[CHECK_FAIL]} guideline requirement(s) were not found and '
            f'{counts[CHECK_WARN]} need review.'
        )
    elif counts.get(CHECK_WARN, 0):
        summary = (
            f'{counts[CHECK_WARN]} guideline requirement(s) need review; '
            f'{counts[CHECK_PASS]} were clearly met.'
        )
    else:
        summary = f'All {counts[CHECK_PASS]} checkable guideline requirement(s) were met.'

    return {
        'items': items,
        'counts': counts,
        'coverage': coverage,
        'categories': categories,
        'total': len(items),
        'mandatory_total': len(mandatory_items),
        'mandatory_met': met_mandatory,
        'needs_attention': missing,
        'summary': summary,
    }


def criterion_categories(criterion):
    """Return the evidence categories that a rubric criterion relates to."""
    text = ' '.join(
        str(criterion.get(key) or '')
        for key in (
            'name', 'description', 'expected_evidence',
            'scoring_guidance', 'ai_instructions',
        )
    ).lower()
    categories = set()
    if any(word in text for word in (
        'doc', 'readme', 'report', 'write', 'manual', 'documentation',
    )):
        categories.add('documentation')
    if any(word in text for word in (
        'database', 'schema', 'sql', 'table', 'erd', 'entity', 'normal',
    )):
        categories.add('database')
    if any(word in text for word in ('test', 'validation', 'quality', 'pytest')):
        categories.add('testing')
    if any(word in text for word in (
        'security', 'login', 'auth', 'password', 'permission', 'role',
    )):
        categories.add('security')
    if any(word in text for word in (
        'design', 'ui', 'interface', 'page', 'dashboard', 'chart', 'diagram',
    )):
        categories.add('design')
    if any(word in text for word in (
        'code', 'implement', 'function', 'program', 'feature', 'working',
        'crud', 'api',
    )):
        categories.add('implementation')
    return categories or {'implementation'}


def category_coverage(report, categories):
    """Return a 0..1 coverage value for the given categories, or ``None``."""
    if not report:
        return None
    categories = {category for category in categories if category}
    if not categories:
        return None
    values = [
        report.get('categories', {}).get(category)
        for category in categories
    ]
    values = [Decimal(str(value)) for value in values if value is not None]
    if not values:
        return None
    return (sum(values, Decimal('0')) / Decimal(len(values))).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )


def related_items(report, categories):
    if not report:
        return []
    categories = set(categories)
    return [
        item for item in report.get('items', [])
        if item.get('category') in categories
    ]


def requirement_check(item):
    """Return a check-shaped dict for the assessment report."""
    return {
        'key': f'guideline:{item["id"]}',
        'label': f'Guideline: {item["label"]}',
        'status': item['status'],
        'message': item['message'],
        'evidence': (item.get('text') or item.get('evidence') or '')[:2000],
    }


def to_json(report):
    """Return a JSON-safe copy of the comparison report."""
    if not report:
        return {
            'items': [],
            'counts': {CHECK_PASS: 0, CHECK_WARN: 0, CHECK_FAIL: 0, CHECK_SKIPPED: 0},
            'coverage': None,
            'categories': {},
            'total': 0,
            'mandatory_total': 0,
            'mandatory_met': 0,
            'needs_attention': 0,
            'summary': '',
        }
    return {
        'items': [
            {
                key: (str(value) if isinstance(value, Decimal) else value)
                for key, value in item.items()
            }
            for item in report.get('items', [])
        ],
        'counts': dict(report.get('counts', {})),
        'coverage': (
            str(report.get('coverage'))
            if isinstance(report.get('coverage'), Decimal)
            else report.get('coverage')
        ),
        'categories': {
            key: str(value)
            for key, value in (report.get('categories') or {}).items()
        },
        'total': report.get('total', 0),
        'mandatory_total': report.get('mandatory_total', 0),
        'mandatory_met': report.get('mandatory_met', 0),
        'needs_attention': report.get('needs_attention', 0),
        'summary': report.get('summary', ''),
    }


def comparison_rows(report):
    """Compact rows for the review/feedback tables."""
    rows = []
    for item in (report or {}).get('items', []):
        rows.append(
            {
                'requirement': item.get('text') or item.get('label') or '',
                'label': item.get('label') or '',
                'status': item.get('status'),
                'status_label': item.get('status_label'),
                'found': item.get('evidence') or item.get('message') or '',
                'message': item.get('message') or '',
                'kind': item.get('kind'),
            }
        )
    return rows
