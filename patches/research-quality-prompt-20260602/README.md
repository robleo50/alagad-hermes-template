# research-quality-prompt-20260602 (Sessions R + S)

Operator-tier `agent.system_prompt` revision (+ a secondary `web_answer` tool-
description tweak) that makes the agent produce thorough, well-sourced, cited
answers for research/list requests — and, critically, actually **use** the
`web_answer` synthesis tool for them instead of raw `web_search`.

This is prompt/config only. No agent code changed. It is part of the **CT 9000
golden-image bake set** (the operator-tier formatting prompt that ships to every
tenant clone).

## The problem

A "list every company, date, and layoff count, with sources" request produced a
hedged, aggregate-only reply that opened with a refusal and punted the customer
to Layoffs.fyi. Three root causes, all in the prompt + tool selection:

1. **The formatting rule forbade lists.** It said to give lists "conversationally
   ('first… then… finally…'), not as bulleted/numbered structures" and to "keep
   it concise — these are customer DMs, not articles." The agent refused to
   enumerate even when explicitly asked.
2. **"ONE message" read as "one SHORT message."** Combined with "concise," the
   model capped itself ("I can't list every single one…") and punted.
3. **Wrong tool for research.** The agent reached for raw `web_search` (snippet
   headlines → aggregate-only) instead of `web_answer` (Perplexica multi-source
   synthesis → structured, cited detail). The `web_answer` description even said
   "use web_search for links," steering list queries to the wrong tool. And a
   formatting rule that said to fold citations into the sentence "not bracketed
   [1][2]" was suppressing the citations `web_answer` already returns.

## The fix, in two passes

### Session R — allow lists + citations, length-matches-request (soft steer)

- Rewrote the formatting rule to ALLOW plain-text lists (own-line items with a
  plain `- ` or `1. ` prefix — just no markdown), while keeping the no-HTML/no-
  Markdown constraint the channels require.
- Added a "Length and depth — match the request" section: stay concise for
  chitchat, but give a THOROUGH, COMPLETE answer when the customer explicitly
  asks for a list / breakdown / research / sources. Clarified that "one message"
  does NOT mean "short message."
- Added a research/citations section telling the agent to use `web_answer` and to
  surface a plain-text "Sources: Outlet (domain)" line instead of hiding citations.
- De-misdirected the `web_answer` tool description (see
  `web_answer_description.patch`) so it no longer says "use web_search for links."

**Result: the soft steer did NOT take.** Post-restart telemetry showed **0
`web_answer` calls vs 3 `web_search` calls** on research queries. gemma4-26b's
reflex to grab the fast tool beat a steer that was buried in prose.

### Session S — directive tool selection + plain-text citation relay

Replaced the soft "## Research-grade answers and citations" section with three
directive sections:

- **## Choosing a tool for factual questions (IMPORTANT)** — `web_answer` is the
  explicit DEFAULT for ANY real-world/factual question (current events, news,
  lists, breakdowns, comparisons, prices, specs, research). `web_search` is ONLY
  for when the customer wants raw links to click or a single trivial lookup.
  RULE OF THUMB: "if the customer is asking you to TELL THEM something factual,
  use web_answer; if they're asking you to FIND THEM LINKS, use web_search."
- **## Presenting a web_answer result (plain text + citations)** — `web_answer`
  returns Markdown + `[1][2]` citations, which the channels do not render. The
  agent MUST relay the content in its own plain text (no `##`, `**`, `*bullets`,
  `[1][2]`) and end research replies with a `Sources: Outlet (domain.com)` line.
  (output-sanitize also strips markdown on egress, and reduces URLs to bare
  domains on Facebook — the `Outlet (domain)` style stays meaningful after that.)
- **## Completeness and honest limits** — lead with the substantial sourced
  answer; never open with a refusal. When data isn't exhaustively available,
  give the major items first, THEN point to a live tracker as a COMPLEMENT to a
  real answer, never as a substitute.

### Why not just disable web_search?

We can't cleanly. Hermes `disabled_toolsets` operates at whole-toolset
granularity, and `web_search`, `web_answer`, and `web_extract` all live in the
shared `web` toolset — so there's no config-only way to remove just `web_search`.
The lever is therefore DIRECTIVE PROMPT WORDING, not tool removal. A code-level
option (split/rename `web_search`, or gate it behind an explicit "links" intent)
remains a flagged future possibility, but was NOT needed: the directive prompt
worked.

## Verification (live, CT 5000, 2026-06-02)

Proven by the state.db tool-selection metric, not just answer appearance:

- **6/6 research turns chose `web_answer`** (zero `web_search`) after the Session S
  restart — a complete reversal of Session R's 0/3.
- Each turn emitted exactly **one** `mcp_beeper_send_message` (send-cap intact).
- The layoffs stress query returned a complete plain-text list with company,
  date, and headcount per item, ending with
  `Sources: TrueUp (trueup.io), SkillSyncer (skillsyncer.com), …` — no `[1][2]`,
  no markdown, and it led with the list instead of refusing.

## Files

- `agent.system_prompt.yaml` — production-verbatim copy of the live
  `config.yaml` `agent.system_prompt` block (the canonical artifact to bake).
- `web_answer_description.patch` — the Session-R `plugins/web-answer/tools.py`
  description de-misdirection.

## Rollback / provenance on CT 5000

- Snapshots: `pre-research-prompt-20260602` (before R),
  `pre-webanswer-steer-20260602` (before S).
- Backups: `config.yaml.bak-pre-research-20260602`,
  `config.yaml.bak-pre-webanswer-steer-20260602`,
  `plugins/web-answer/tools.py.bak-pre-research-20260602`.
- config.yaml md5: `b2e04ce8…` (pre-R) → `893eadaa…` (post-R) → `369ec684…` (post-S).

## Preserved guardrails (do not weaken when baking)

The plain-text/no-markdown constraint, the send-cap (`mcp_beeper_send_message: 3`),
the Facebook bare-domain URL reducer, Fix-A (tool-bypass), and the 128k context
settings are all untouched by this patch.
