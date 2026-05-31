"""Tests for output-sanitize. Run: ``python test_format.py``  (or pytest).

The MUTATION-PROPAGATION test is the durable canary: it asserts the
``pre_tool_call`` hook mutates ``args["text"]`` in place. If a future Hermes
copies tool args before invoking hooks, this test FAILS — signalling that the
arg-rewrite side-channel broke and the upstream "rewrite" hook-action fallback
is needed. Re-run after every Hermes upgrade.
"""

import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from format import format_for_channel  # noqa: E402


def test_unit_sanitize():
    cases = [
        "## Heading\n\n**Bold** then:\n- one\n- two\n\n| A | B |\n|---|---|\n| 1 | 2 |",
        "<p>HTML <strong>bold</strong></p>",
        "Plain text, nothing to change.",
        "Check [the docs](https://example.com) please.",
        "Mixed **md** and <em>html</em>.",
    ]
    for inp in cases:
        out = format_for_channel(inp)
        assert "<" not in out and ">" not in out, f"HTML leaked: {out!r}"
        assert "**" not in out, f"bold leaked: {out!r}"
        assert not any(ln.lstrip().startswith("#") for ln in out.splitlines()), f"header leaked: {out!r}"
        assert "|--" not in out and "--|" not in out, f"table separator leaked: {out!r}"
    assert format_for_channel("Plain text, nothing to change.") == "Plain text, nothing to change."
    assert "example.com" in format_for_channel("Check [the docs](https://example.com) please.")


def _load_hook_callback():
    spec = importlib.util.spec_from_file_location("_outsan_init", os.path.join(_HERE, "__init__.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    captured = {}

    class FakeCtx:
        def register_hook(self, name, cb):
            captured[name] = cb

    mod.register(FakeCtx())
    assert "pre_tool_call" in captured, "plugin did not register a pre_tool_call hook"
    return captured["pre_tool_call"]


def test_mutation_propagation():
    """THE CANARY: the hook must mutate args['text'] in place for the target tool."""
    cb = _load_hook_callback()

    args = {"chatID": "x", "text": "## Hi\n**bold** message", "other": "untouched"}
    ret = cb(tool_name="mcp_beeper_send_message", args=args)
    assert ret is None, "hook must not return a block directive"
    assert "**" not in args["text"], f"mutation did not strip bold: {args['text']!r}"
    assert not args["text"].lstrip().startswith("#"), f"mutation did not strip header: {args['text']!r}"
    assert args["other"] == "untouched", "hook touched an unrelated arg"
    assert args["chatID"] == "x", "hook touched chatID"

    # Non-target (read-only) tool must be left alone.
    a2 = {"text": "**keep this**"}
    cb(tool_name="mcp_beeper_list_messages", args=a2)
    assert a2["text"] == "**keep this**", "hook wrongly mutated a non-send tool"

    # Malformed/missing text must be tolerated (no exception, no crash).
    cb(tool_name="mcp_beeper_send_message", args={"chatID": "x"})
    cb(tool_name="mcp_beeper_send_message", args={"text": None})
    cb(tool_name="mcp_beeper_send_message", args=None)


if __name__ == "__main__":
    test_unit_sanitize()
    print("UNIT: PASS")
    test_mutation_propagation()
    print("MUTATION PROPAGATION: PASS")
    print("ALL TESTS PASS")
