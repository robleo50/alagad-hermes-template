"""Alagad ``output-sanitize`` plugin — bundled, auto-loaded (``kind: backend``).

Registers a ``pre_tool_call`` hook that rewrites the outbound ``text`` arg of the
Beeper send tool (``mcp_beeper_send_message``) to plain text BEFORE the call
executes, so customers on Beeper-bridged DM channels never see raw Markdown/HTML.

Mechanism note (the one fragile bit, guarded by test_format.py):
``invoke_hook`` passes the tool ``args`` dict to callbacks BY REFERENCE (no copy),
and ``model_tools`` executes the tool with that same dict, so mutating
``args["text"]`` in the callback propagates to the executed call. The hook's
DOCUMENTED return contract is block/observe ({"action":"block",...}); arg-rewrite
is an undocumented side-channel that works due to the no-copy implementation.
We return ``None`` (rewrite-only, never block). If a future Hermes copies args
before the hook, the mutation silently stops — FAILS OPEN (original text sends,
markdown returns, no crash). The mutation-propagation test in test_format.py is
the canary that detects this; the fallback is an upstream "rewrite" hook action.

Relative import for package context (gateway), absolute fallback for standalone
test import (cf. the hyphenated dir name, like plugins/disk-cleanup).
"""

from __future__ import annotations

try:  # package context (loaded by the Hermes plugin loader)
    from .format import TEXT_SEND_TOOLS, format_for_channel
except ImportError:  # standalone import (tests with the plugin dir on sys.path)
    from format import TEXT_SEND_TOOLS, format_for_channel


def _pre_tool_call(tool_name=None, args=None, **kwargs):
    """Rewrite outbound message text for text-sending Beeper tools.

    Returns ``None`` (rewrite-only; never blocks). Guarded so a malformed arg can
    never drop or break a customer reply — formatting must never cost delivery.
    """
    try:
        if tool_name in TEXT_SEND_TOOLS and isinstance(args, dict):
            txt = args.get("text")
            if isinstance(txt, str) and txt:
                args["text"] = format_for_channel(txt)
    except Exception:
        # Fail open: never block/break a customer reply over formatting.
        pass
    return None


def register(ctx) -> None:
    """Register the outbound sanitization hook. Called once by the plugin loader."""
    ctx.register_hook("pre_tool_call", _pre_tool_call)
