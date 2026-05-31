"""Alagad ``web_answer`` plugin — bundled, auto-loaded (``kind: backend``).

Registers a single tool, ``web_answer``, into the existing ``web`` toolset. The
tool calls the per-tenant Alagad Answer adapter (Perplexica-backed synthesis) at
``$ALAGAD_ANSWER_URL``. The tool gates on that env var via ``requires_env`` and
``check_fn``, so a tenant without answer wired simply doesn't see it (no error).

Registration mirrors ``plugins/spotify/__init__.py``; relative imports keep the
package self-contained under a hyphenated directory name (cf.
``plugins/disk-cleanup``), matching the alagad-hermes-template repo path
``plugins/web-answer/``.
"""

from __future__ import annotations

from .tools import WEB_ANSWER_SCHEMA, _answer_available, _handle_web_answer


def register(ctx) -> None:
    """Register the web_answer tool. Called once by the plugin loader."""
    ctx.register_tool(
        name="web_answer",
        toolset="web",
        schema=WEB_ANSWER_SCHEMA,
        handler=_handle_web_answer,
        check_fn=_answer_available,
        requires_env=["ALAGAD_ANSWER_URL"],
        is_async=True,
        emoji="\U0001f4ac",
    )
