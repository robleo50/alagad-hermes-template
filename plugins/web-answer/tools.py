"""``web_answer`` tool — synthesized, cited web answers via the Alagad Answer adapter.

Structure mirrors ``plugins/spotify/tools.py`` (bare-form schema + handler +
availability check). The HTTP-to-an-external-tokened-service shape mirrors
``plugins/web/tavily/provider.py``. Schemas use the bare
``{"name", "description", "parameters"}`` form the registry expects (matching
``WEB_SEARCH_SCHEMA`` in ``tools/web_tools.py``), NOT the OpenAI
``{"type": "function", ...}`` wrapper.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from .client import ENV_URL, AnswerError, request_answer

# Perplexica focus modes accepted by the adapter. Omitting focus_mode lets the
# adapter apply its own default (webSearch). Kept in the schema enum so the
# model can pick deliberately.
FOCUS_MODES = [
    "webSearch",
    "academicSearch",
    "writingAssistant",
    "wolframAlphaSearch",
    "youtubeSearch",
    "redditSearch",
]

WEB_ANSWER_SCHEMA: Dict[str, Any] = {
    "name": "web_answer",
    "description": (
        "Get a synthesized, cited answer to a factual question by searching the "
        "live web and summarizing across multiple sources. Use this when the user "
        "needs current real-world facts (product specs, prices, recent events, "
        "\"what is X\", \"how does Y compare to Z\") and wants a direct answer rather "
        "than a list of links (use web_search for links) or the contents of one "
        "specific URL (use web_extract). Returns a written answer followed by the "
        "sources it cites. Synthesis can take 20-40 seconds."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The question to answer, in natural language.",
            },
            "focus_mode": {
                "type": "string",
                "enum": FOCUS_MODES,
                "description": (
                    "Optional search focus. Defaults to webSearch (general web). "
                    "Use academicSearch for scholarly/research topics, "
                    "wolframAlphaSearch for math/computation, youtubeSearch for "
                    "video, redditSearch for community discussion, writingAssistant "
                    "for composition help."
                ),
            },
        },
        "required": ["query"],
    },
}


def _answer_available() -> bool:
    """Cheap, network-free availability gate — the tool dispatches only when the
    per-tenant answer URL is configured. Mirrors spotify's _check_*_available."""
    return bool(os.getenv(ENV_URL, "").strip())


def _format(result: Dict[str, Any]) -> str:
    """Render the adapter's JSON into a readable answer + numbered source list.

    Perplexica sources are ``{"pageContent": str, "metadata": {"title", "url"}}``;
    we also tolerate flat ``{"url", "title"}`` for forward-compatibility.
    """
    answer = (result.get("answer") or "").strip() or "(no answer returned)"
    sources: List[Dict[str, Any]] = result.get("sources") or []
    lines = [answer]

    if sources:
        lines.append("")
        lines.append("Sources:")
        for i, src in enumerate(sources, 1):
            url = ""
            title = ""
            if isinstance(src, dict):
                meta = src.get("metadata")
                if isinstance(meta, dict):
                    url = meta.get("url") or meta.get("sourceURL") or ""
                    title = meta.get("title") or ""
                url = url or src.get("url") or ""
                title = title or src.get("title") or url
            entry = f"  [{i}] {title} - {url}" if url else f"  [{i}] {title}"
            lines.append(entry.rstrip(" -"))

    if result.get("cached"):
        lines.append("")
        lines.append("(cached result)")
    return "\n".join(lines)


async def _handle_web_answer(args: Dict[str, Any], **_kw: Any) -> str:
    """Tool handler. Returns a formatted answer string, or a clean error message.

    Never raises into the agent loop — every failure path becomes a readable
    ``web_answer error: ...`` string.
    """
    query = (args.get("query") or "").strip()
    if not query:
        return "web_answer error: 'query' is required."
    focus_mode = args.get("focus_mode") or None
    try:
        result = await request_answer(query, focus_mode=focus_mode)
    except AnswerError as exc:
        return f"web_answer error: {exc.message}"
    except Exception as exc:  # noqa: BLE001 - defensive: never crash the loop
        return f"web_answer error: unexpected failure ({exc})"
    return _format(result)
