# Tool-Bypass Fix — Hermes v0.14.0 (Alagad CT 5000 / tenant agents)

**Status:** validated on clone 5001 (deterministic proof); deployed to CT 5000 2026-06-01.
**Applies to:** Hermes Agent v0.14.0 (2026.5.16) as bundled in the tenant LXC `~/.hermes/hermes-agent/`.
**⚠️ This is a LOCAL patch to upstream Hermes (not a repo we control). It MUST be re-applied after any Hermes upgrade** — line numbers will shift, so re-derive from the anchor context described below, not the raw line numbers.

## Root cause (reconciled, byte-verified)
The agent's own post-tool narration turn — a bare `assistant: "Sent reply to Rob Leonardo."` (no tool_calls) emitted after every successful `mcp_beeper_send_message` — **persists in the per-peer session and accumulates**. On a weak model (gemma4-26b) the dominant in-context pattern becomes "an assistant turn = emit bare text," which it then imitates **without** the preceding tool call → the agent stops actually sending → customer silence. Gateway-hygiene **compression concentrates** the accumulated narration (it is the concentrator, NOT the cause and NOT a cure). The bridge's `transcript.inject` prose blob is a secondary "respond=prose" signal.

The fix removes the **necessary precondition**: the narration turn never persists, so it cannot accumulate, so there is nothing to concentrate, so the flip cannot occur — regardless of trigger. Bonus: the persisted history becomes pure `[user -> assistant(tool_call) -> tool_result]` triples, so every assistant turn the model sees *calls the tool* (reinforces tool-calling).

## The 4 edits

### Edit 1 — flag the narration turn at generation (`agent/conversation_loop.py`, ~line 3935)
At the single normal-success append point of the no-tool-call final-response branch (`messages.append(final_msg)`), flag `final_msg` with `_post_send_narration_drop = True` **only when the four-condition gate holds**:
1. `finish_reason == "stop"`
2. `not final_msg.get("tool_calls")` (bare assistant turn)
3. (branch guarantees role=assistant)
4. the immediately-preceding message (`messages[-1]`) is a **successful** `mcp_beeper_send_message` tool result (success via `agent.display._detect_tool_failure`; fail-safe = KEEP the turn if undetermined).

### Edit 2 — drop it before persist (`run_agent.py`, `_persist_session` ~1240 + new method ~1296)
New method `_drop_post_send_narration(messages)` pops a trailing message carrying `_post_send_narration_drop` (and role=assistant, no tool_calls). Called as a **separate statement** right after `_drop_trailing_empty_response_scaffolding` and before flush. **Must NOT be merged into the scaffolding-drop** — that function's Pass 2 would rewind the tool_call + tool result (the send record we must keep).

### Edit 3 — fresh-tool-tail carve-out (`gateway/run.py`, `_has_fresh_tool_tail` ~16996)
Dropping the narration leaves the model-facing `agent_history` tail on a tool result. Hermes' auto-continue treats a fresh tool-result tail as an interrupted turn and prepends a `[System note: ...interrupted... summarize what was accomplished...]` to the next user message — within a **1-hour** freshness window (so it hits most real follow-ups), and its "summarize" instruction ironically re-nudges narration. Carve-out: a trailing **successful** `mcp_beeper_send_message` tool result is an intentional clean ending, NOT an interruption. Marker = the tool result's `tool_name` (round-trips natively through state.db `hermes_state.py:1947` — no DB migration). Genuine mid-task interruptions (other tools, or a FAILED send) still recover normally.

### Edit 4 — silence the log-only warning (`agent/conversation_loop.py`, ~line 4128)
Add `and _last_tool_name != "mcp_beeper_send_message"` to the `if _last_msg_role == "tool" and not interrupted:` condition guarding the "Turn ended with pending tool result (agent may appear stuck)" warning. Cosmetic (log-only), same terminal-send case.

## Fold-ins (config, applied at deploy — not part of these diffs)
- `/etc/alagad/bridge.yaml`: `transcript.inject: false` (removes the standing prose-blob "respond=prose" signal the code fix cannot touch; also kills HTML-leak + token bloat).
- `~/.hermes/config.yaml`: `session_reset.idle_minutes: 1440` (24h; bounds accumulation density without fragmenting same-day conversations).

## Proof (clone 5001, back-to-back = strictest within-hour timing)
| Metric | Fix OFF | Drop-only | Full fix |
|---|---|---|---|
| Persisted post-send narration | 18 | 0 | 0 |
| Interrupted-notes | n/a | every turn >=2 | 0 |
| Sends (tool_call+result) intact | 20 | 19 | 24 |
| Continuity | - | - | preserved (recalled a fact across the accumulated session) |

## Verification md5 of the patched files (Hermes v0.14.0 baseline)
- `agent/conversation_loop.py` -> `6c9206fce45d725fc919ebbd049905d4`
- `run_agent.py` -> `2ea4dbf95bec68c812b2d10db9f27a1c`
- `gateway/run.py` -> `2b54d182a6220cebd9675ad5cc439175`
(These hold only for the exact v0.14.0 baseline; after a Hermes upgrade, re-derive the edits from the anchors above.)

## Bake (Session C)
This patch + the 2 fold-ins must bake into CT 9000's `hermes-agent` so all tenant clones inherit it. Until baked, every tenant agent has this bug; no tenant should run sustained customer conversations until baked.
