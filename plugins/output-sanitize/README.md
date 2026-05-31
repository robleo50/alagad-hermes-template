# output-sanitize plugin

A Hermes `pre_tool_call` hook that rewrites the outbound `text` of the Beeper
send tool (`mcp_beeper_send_message`) to **plain text** before the call executes,
so customers on Beeper-bridged DM channels (Instagram / Facebook Messenger /
WhatsApp / SMS) never see raw Markdown or HTML.

Defense-in-depth with the operator-tier formatting prompt (`config.yaml`
`agent.system_prompt`, "Session F"): the prompt tells the model not to emit
HTML/Markdown (kills HTML, leaves a Markdown residual on gemma4-26b); this hook
deterministically strips whatever slips through.

## Why a hook (not the bridge, not the prompt alone)

On the Alagad tenant architecture the agent sends its own replies via the Beeper
Desktop MCP (`mcp_beeper_send_message`) — the `alagad-bridge` is inbound-only
(`reply_mode: fire_and_forget`), so there is no Alagad code on the outbound text
path except this hook. Prompt guidance has an adherence ceiling on a 26B model;
a deterministic regex pass does not.

## Files

- `plugin.yaml` — manifest (`kind: backend` auto-load; `hooks: [pre_tool_call]`).
- `format.py` — `format_for_channel()` (HTML+Markdown → plain) + `TEXT_SEND_TOOLS`.
- `__init__.py` — `register(ctx)` → `ctx.register_hook("pre_tool_call", …)`; the hook
  mutates `args["text"]` in place for tools in `TEXT_SEND_TOOLS`, returns `None`.
- `test_format.py` — unit cases + the **mutation-propagation canary**.

## Mechanism + the canary (read before upgrading Hermes)

`invoke_hook` passes the tool `args` dict to callbacks **by reference** (no copy),
and `model_tools` executes the tool with that same dict, so mutating
`args["text"]` propagates. This is an arg-rewrite via the args dict; the hook's
*documented* contract is block/observe, so the callback returns `None` (never
blocks). **If a future Hermes copies args before the hook, the rewrite silently
stops — fails open (Markdown returns, no crash).** `test_format.py`'s
`test_mutation_propagation` is the canary: **re-run it after every Hermes
upgrade.** If it ever fails, the fallback is an upstream "rewrite" hook action
(a small Hermes patch), NOT a tool-override.

## Scope

Targets `mcp_beeper_send_message` (confirmed from 382 real calls; arg `text`).
`mcp_beeper_list_messages` is read-only (excluded). Edit-type Beeper tools were
not observed in history; if one is added, append its name to `TEXT_SEND_TOOLS`.
No `html2text` dependency (regex-only; `format.py` uses html2text opportunistically
if it is present).

## Tests

`python test_format.py` (or pytest). Validated 2026-05-31 on a throwaway CT 9000
clone (Hermes 0.14.0): unit pass, mutation-propagation pass, plugin auto-loads +
hook registers. Deployed to the live CT 5000 the same day.
