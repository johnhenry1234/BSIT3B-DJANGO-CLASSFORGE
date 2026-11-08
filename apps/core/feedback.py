"""Small helpers for making assessment feedback readable.

Feedback can arrive as either a plain string or a structured object from an
LLM.  These helpers keep the student-facing text consistent and safe to render:

* whitespace and accidental list markers are cleaned up
* empty or non-text values are ignored
* the same section names are used everywhere
* the output is plain text (no raw HTML or Markdown is trusted)
"""

from __future__ import annotations

import re

MAX_ITEMS = 6
MAX_ITEM_LENGTH = 700
MAX_TEXT_LENGTH = 15_000

_SECTION_DEFINITIONS = (
    ('overview', 'Overview', 'text'),
    ('strengths', 'What you did well', 'list'),
    ('improvements', 'What to improve', 'list'),
    ('next_steps', 'Next steps', 'numbered'),
)

_STRENGTH_KEYS = ('strengths', 'what_you_did_well', 'what_went_well')
_IMPROVEMENT_KEYS = (
    'improvements',
    'needs_improvement',
    'areas_to_improve',
    'what_to_improve',
)
_NEXT_STEP_KEYS = ('next_steps', 'nextSteps', 'suggested_next_steps')


def clean_text(value, *, limit=MAX_TEXT_LENGTH):
    """Return normalised plain text, or an empty string for invalid values."""
    if not isinstance(value, str):
        return ''
    text = value.replace('\r\n', '\n').replace('\r', '\n').strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text[:limit].strip()


def clean_inline(value, *, limit=MAX_ITEM_LENGTH):
    """Return one readable line without a leading bullet or list number."""
    text = clean_text(value, limit=limit)
    if not text:
        return ''
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^(?:[-*•]+|\d+[.)])\s*', '', text)
    return text[:limit].strip()


def clean_items(value, *, limit=MAX_ITEMS):
    """Return a de-duplicated list of short, readable feedback items."""
    if isinstance(value, str):
        lines = [line for line in value.splitlines() if line.strip()]
        values = lines if len(lines) > 1 else [value]
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        return []

    items = []
    for item in values:
        if isinstance(item, dict):
            item = item.get('text') or item.get('message') or ''
        text = clean_inline(item)
        if text and text not in items:
            items.append(text)
        if len(items) >= limit:
            break
    return items


def _first_value(mapping, keys):
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def normalise_sections(value):
    """Return a consistent feedback-section mapping from an LLM payload."""
    if not isinstance(value, dict):
        return {}

    overview = clean_text(
        value.get('overview') or value.get('summary') or '',
        limit=2_000,
    )
    strengths = clean_items(_first_value(value, _STRENGTH_KEYS))
    improvements = clean_items(_first_value(value, _IMPROVEMENT_KEYS))
    next_steps = clean_items(_first_value(value, _NEXT_STEP_KEYS))

    if not any((overview, strengths, improvements, next_steps)):
        return {}

    return {
        'overview': overview,
        'strengths': strengths,
        'improvements': improvements,
        'next_steps': next_steps,
    }


def format_sections(value):
    """Render a feedback mapping as readable plain text."""
    sections = normalise_sections(value)
    if not sections:
        return ''

    parts = []
    for key, title, kind in _SECTION_DEFINITIONS:
        content = sections.get(key)
        if not content:
            continue

        if kind == 'text':
            parts.append(f'{title}\n{content}')
            continue

        if kind == 'numbered':
            lines = [
                f'{index}. {item}'
                for index, item in enumerate(content, start=1)
            ]
        else:
            lines = [f'- {item}' for item in content]
        parts.append(f'{title}\n' + '\n'.join(lines))

    return '\n\n'.join(parts)


def feedback_text(value):
    """Return a readable feedback string from either supported input shape."""
    if isinstance(value, dict):
        return format_sections(value)
    return clean_text(value)
