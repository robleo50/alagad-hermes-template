"""Alagad ``output-sanitize`` plugin — bundled, auto-loaded (``kind: backend``).

Registers a ``pre_tool_call`` hook that rewrites the outbound ``text`` arg of the
Beeper send tool (``mcp_beeper_send_message``) to plain text BEFORE the call
executes. On the Facebook channel (detected from ``args["chatID"]``), it also
reduces URLs to bare domains because Facebook Messenger silently drops outbound
messages containing clickable links from automated-pattern accounts (proven by
controlled send test: bare domain delivers; scheme, www, OR a path => dropped).
Instagram keeps clickable links (it delivers them fine).

Mechanism note (guarded by test_format.py): ``invoke_hook`` passes the tool
``args`` dict BY REFERENCE (no copy), so mutating ``args["text"]`` propagates to
the executed call. Returns ``None`` (rewrite-only, never blocks). FAILS OPEN:
any error -> original text sends unchanged. Formatting must never cost delivery.
"""

from __future__ import annotations

try:  # package context (loaded by the Hermes plugin loader)
    from .format import TEXT_SEND_TOOLS, format_for_channel
except ImportError:  # standalone import (tests with the plugin dir on sys.path)
    from format import TEXT_SEND_TOOLS, format_for_channel


def _pre_tool_call(tool_name=None, args=None, **kwargs):
    """Rewrite outbound message text for text-sending Beeper tools.

    Passes chatID so the formatter can apply channel-specific rules (Facebook
    URL->bare-domain). Returns ``None`` (rewrite-only; never blocks). Guarded so
    a malformed arg can never drop or break a customer reply.
    """
    try:
        if tool_name in TEXT_SEND_TOOLS and isinstance(args, dict):
            txt = args.get("text")
            if isinstance(txt, str) and txt:
                chat_id = args.get("chatID") or args.get("chatId") or args.get("chat_id")
                args["text"] = format_for_channel(txt, chat_id)
    except Exception:
        # Fail open: never block/break a customer reply over formatting.
        pass
    return None


def register(ctx) -> None:
    """Register the outbound sanitization hook. Called once by the plugin loader."""
    ctx.register_hook("pre_tool_call", _pre_tool_call)
