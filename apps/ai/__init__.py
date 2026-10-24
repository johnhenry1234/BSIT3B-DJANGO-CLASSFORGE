"""AI-assisted evaluation app for ClassForge.

AI output is *always* a draft.  An ``AIEvaluation`` is an independent record
linked to one submission version; it never modifies a ``Grade`` unless an
instructor explicitly applies it, and applying it never publishes a grade.
"""

default_app_config = 'apps.ai.apps.AiConfig'
