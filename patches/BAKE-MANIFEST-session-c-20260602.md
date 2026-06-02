# CT 9000 Golden Template — Session C Bake Manifest (2026-06-02)

**Status:** BAKE COMPLETE & clone-validated. CT 9000 (`alagad-template`) is the
new golden template for paying-tenant provisioning via `spin-workspace.py`.

CT 9000 was a full bake-cycle behind (last baked `@post-capability-bake-20260530`,
i.e. before Fix-A and all Session P/Q/R/S work). This bake brings it to parity
with the proven-live reference **CT 5000**.

## Rollback mechanism (READ FIRST — basevol, NOT `pct snapshot`)
CT 9000 rootfs is a ZFS **basevol**: `vmpool2/basevol-9000-disk-0`. `pct snapshot`
is UNAVAILABLE on basevols. Use ZFS directly:
- **Pre-bake rollback point:** `vmpool2/basevol-9000-disk-0@pre-session-c-bake-20260602`
- **Post-bake checkpoint:** `vmpool2/basevol-9000-disk-0@post-session-c-bake-20260602`
- **Roll back:** `pct stop 9000; zfs rollback vmpool2/basevol-9000-disk-0@pre-session-c-bake-20260602`
  (destroys `@post-session-c-bake`; never touches `@__base__`, so the CT 9100
  linked clone that depends on `@__base__` stays safe).

## ⭐ Re-templatize finding (resolved this session)
Prior notes warned a separate "re-templatize" step might be required for clones
to inherit edits. **Empirically DISPROVEN this session:** a clone spun via
`spin-workspace.py` (FeatherPanel, `FP_TEMPLATE_ID=1`) **inherited the full live
bake-set** (Fix-A md5s, 128k context, plugins, prompt — all matched). FP/spin
clones from the **current basevol state**, so **no re-templatize is needed**.
The bake propagates to new tenants directly.

## Bake set (per-item source + verification)
Core `.py` files were copied from CT 5000 (same Hermes v0.14.0 base) and
md5-verified byte-identical. Config settings applied surgically (placeholders
preserved). Plugins copied from CT 5000 (tree-checksum match).

| # | Item | Source | Verify |
|---|---|---|---|
| 1 | Fix-A `agent/conversation_loop.py` | CT 5000 | md5 `2863f011417a3a2bb9456f5db33ae14a` |
| 1 | Fix-A `run_agent.py` | CT 5000 | md5 `67ad6a12cb6ecea3e98c9f9a88cfff17` |
| 1 | Fix-A `gateway/run.py` | CT 5000 | md5 `2b54d182a6220cebd9675ad5cc439175` |
| 1 | fold-in `bridge.yaml transcript.inject:false` | spec | confirmed |
| 1 | fold-in `config.yaml session_reset.idle_minutes:1440` | CT 5000 | confirmed |
| 2 | send-cap `agent/tool_guardrails.py` | CT 5000 | md5 `d249646766e6d8932fa6f6e7b234e3ce` |
| 2 | send-cap `config tool_loop_guardrails: mcp_beeper_send_message:3` | CT 5000 | confirmed |
| 2 | send-cap empty-halt guard (in `run_agent.py`) | CT 5000 | `same_tool_total_halt -> return ""` |
| 2 | `send-terminal-signal` plugin (Session O/P root-cause reducer) | CT 5000 | tree-md5 `6e9e3329…` |
| 3 | `model.context_length:128000` (+ custom_providers gemma) | CT 5000 | confirmed |
| 3 | `model.max_tokens:2048` | CT 5000 | confirmed |
| 3 | `compression.protect_last_n:12` | CT 5000 | confirmed |
| 3 | tool-result clamp `agent/tool_dispatch_helpers.py` (`_TOOL_RESULT_MAX_CHARS=32000`) | CT 5000 | md5 `8d639b55d84a44cda57aa2f7f9d3d379` |
| 4 | `output-sanitize` plugin (+FB URL→bare-domain reducer `_domain_only_urls`/`local-facebook`) | CT 5000 | tree-md5 `0a0fd960…` |
| 5 | `web-answer` plugin | CT 5000 | tree-md5 `e2286615…` |
| 5 | `answer.conf` gateway drop-in (NEW this bake) | created | `ALAGAD_ANSWER_URL=http://192.168.8.242:8700/t/ANSWER_TOKEN_PLACEHOLDER` |
| 6 | research-quality `agent.system_prompt` (Sessions F/R/S) | CT 5000 | len 4313, 2 marker phrases |
| 7 | tenant-fw v3 — `define ANSWER=192.168.8.242` + `tcp dport 8700 accept` | CT 5000 | `nft -c` OK |
| 8 | secrets = PLACEHOLDER only | — | `__WEBHOOK_SECRET__`, `LITELLM_KEY_PLACEHOLDER`; no `bdapi_`/`antk_`/FB-login |

`_config_version: 25` pin KEPT (template-specific; CT 5000 has none — stops
Hermes migrate-on-load from mangling `model.provider`/`key_env` on clone boot).
All copied files chowned `alagad:alagad`, `__pycache__` cleared, `py_compile` OK.

## Placeholder-secret + firstboot injection contract
The template ships PLACEHOLDERS; per-tenant values are minted/injected at clone
time by `spin-workspace.py` (+ `alagad-firstboot`):
- LiteLLM key: `/key/generate` → replaces `LITELLM_KEY_PLACEHOLDER` in `.env`.
- search/fetch/answer tokens: minted (CT 9300/9301/9302) → injected into the
  `searxng.conf`/`tavily.conf`/`answer.conf` gateway drop-ins (`*_TOKEN_PLACEHOLDER`).
  Answer token table `search.tenant_answer_token` (issuer NOT idempotent;
  spin pre-checks). `answer.conf` being baked is what unblocks per-tenant answer.
- Beeper `bdapi_` / FB login: set up POST-spin (bridge install), not baked.

## Clone-validate result (the proof)
Threw a disposable clone `bake-validate-20260602` (CT 5001) via `spin-workspace.py`,
validated, then destroyed (+ all tokens revoked). Confirmed:
- Full bake-set inherited (all md5s/settings/plugins matched CT 5000).
- Per-tenant secrets injected: fresh LiteLLM key, fresh `antk_` answer token
  (DB-confirmed, 1 row), search+fetch tokens — none are Richard's; no `bdapi_`/FB-login.
- Gateway healthy: single instance, port 8644 listening, all 3 drop-ins loaded
  (the 06:21:20 "exit 1" was the expected `gateway run --replace` handoff during
  firstboot token-injection restart, recovered cleanly).

## Standing follow-up (not fixed — documented)
The template ships the webhook `secret: "__WEBHOOK_SECRET__"` INERT (loopback
127.0.0.1:8644; the bridge sends no auth — `auth_token`/`auth_header` empty).
firstboot does not mint a per-tenant webhook secret. If real loopback auth is
ever wanted, firstboot must mint+inject BOTH the Hermes `secret:` and the bridge
`auth_token`.
