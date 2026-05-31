"""Deterministic outbound text sanitizer for DM channels.

Strips Markdown (and any residual HTML) to plain text suitable for the chat
platforms Beeper bridges to (Instagram / Facebook Messenger / WhatsApp / SMS),
none of which render Markdown or HTML — customers would otherwise see literal
``**``, ``##``, ``|---|`` etc. Defense-in-depth with the Session F operator-tier
prompt policy (the prompt suppresses most; this guarantees the residual is clean).

Pure-stdlib regex. ``html2text`` is used opportunistically for HTML->text if it
happens to be installed, else a regex tag-strip handles the (rare, post-Session-F)
HTML residual — so there is NO hard dependency.
"""

from __future__ import annotations

import re

# Tool names whose ``text`` arg is outbound, customer-facing prose to sanitize.
# Confirmed from 382 real calls in state.db: the agent sends via
# ``mcp_beeper_send_message`` (Hermes names MCP tools ``mcp_<server>_<tool>``),
# arg key ``text`` (call args: {"chatID": "...", "text": "..."}).
# ``mcp_beeper_list_messages`` is read-only -> excluded. Edit-type Beeper tools
# were not observed in history and the live MCP tools/list would not enumerate;
# if such a text-bearing tool is added later, append its name here (single
# source of truth for what gets sanitized).
TEXT_SEND_TOOLS = {"mcp_beeper_send_message"}


def format_for_channel(message: str) -> str:
    """Strip HTML + Markdown to plain text for DM channels.

    Default plain (safest for Beeper-bridged Instagram/FB/WhatsApp/SMS). Returns
    the input unchanged if it's empty or not a string.
    """
    if not message or not isinstance(message, str):
        return message

    # HTML -> plain (residual; the Session F prompt already suppresses most).
    if re.search(r"<[a-z][a-z0-9]*\b[^>]*>", message, re.IGNORECASE):
        try:
            import html2text  # optional — not a hard dependency

            h = html2text.HTML2Text()
            h.body_width = 0
            h.ignore_links = False
            h.ignore_images = True
            message = h.handle(message).strip()
        except ImportError:
            message = re.sub(r"<[^>]+>", "", message)

    # Markdown -> plain.
    message = re.sub(r"\*\*([^*]+)\*\*", r"\1", message)                 # **bold**
    message = re.sub(r"__([^_]+)__", r"\1", message)                     # __bold__
    message = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", message)      # *italic*
    message = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"\1", message)          # _italic_
    message = re.sub(r"^\s{0,3}#{1,6}\s+", "", message, flags=re.MULTILINE)  # ## headers
    message = re.sub(r"^\s*[-*+]\s+", "• ", message, flags=re.MULTILINE)  # bullets -> •
    message = re.sub(r"```[a-z]*\n?", "", message)                      # ``` code fences
    message = re.sub(r"`([^`]+)`", r"\1", message)                      # `inline code`
    message = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", message)    # [text](url)
    message = _flatten_markdown_tables(message)
    message = re.sub(r"\n{3,}", "\n\n", message)                        # collapse blank runs

    return message.strip()


def _flatten_markdown_tables(text: str) -> str:
    """Convert markdown tables to readable plain-text lines (best-effort).

    Drops ``|---|---|`` separator rows; turns ``| a | b |`` into ``a — b``. The
    bar is 'not a wall of pipe characters', not perfect table rendering.
    """
    out = []
    for line in text.split("\n"):
        stripped = line.strip()
        if re.match(r"^\|?[\s:|-]+\|?$", stripped) and "-" in stripped:
            continue  # separator row
        if stripped.startswith("|") or ("|" in stripped and stripped.count("|") >= 2):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            out.append(" — ".join(c for c in cells if c))
        else:
            out.append(line)
    return "\n".join(out)
