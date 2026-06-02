# Alagad Golden Template (CT 9000) — Stack & Provisioning Reference

**Container:** CT 9000 `alagad-template` (Proxmox LXC on NEST)
**Status:** Baked + validated + stopped — the production golden template. Every paying tenant is cloned from this.
**Baked:** Session C / "Session U" bake, 2026-06-02 (clone-validated)
**Last verified:** 2026-06-02 (byte-level against the live stopped template)
**Owner:** Rob (PAL Tech LLC) — infrastructure in Carmel, Indiana
**Do not modify CT 9000 directly.** Iterate via a clone, then re-bake through the documented process.

---

## 1. What this is

CT 9000 is the **golden LXC template** for the Alagad service — a single Hermes AI agent stack that `spin-workspace.py` clones to provision each paying tenant (Philippine SMEs, flat ₱2,999/mo, unlimited inference). The template carries the complete agent stack with **placeholder secrets**; per-tenant credentials are minted and injected at first boot. One bake = every future tenant inherits the same proven configuration.

**Product model context:** single product = LXC + Hermes agent + (per-tenant, post-spin) Beeper Desktop. Tenant inference is `gemma4-26b` only, via the shared LiteLLM proxy. The pitch is flat-rate unlimited inference — never privacy/data-residency.

---

## 2. Base stack

| Layer | Value |
|---|---|
| Virtualization | Proxmox LXC (unprivileged), `features: nesting=1,keyctl=1` |
| Host | NEST (192.168.8.222), Proxmox |
| Storage | `vmpool2:basevol-9000-disk-0` (ZFS basevol), 8 GB rootfs |
| OS | Ubuntu 24.04 LTS |
| Python | 3.12.3 |
| Agent runtime | Hermes Agent **v0.14.0** (build `v2026.5.16-1095-gbb4703c76`) |
| In-LXC user | `alagad` (Hermes runs as this user; everything under `~/.hermes`) |
| Default resource spec (template) | 2 cores / 2048 MB / 512 MB swap / 8 GB disk |
| Tenant provisioning spec (paid) | 4 cores / 8 GB / 100 GB (set by the platform UI / spin-workspace at clone time) |

**Note on resources:** the template's 2c/2G is the base image footprint; paying tenants are provisioned at 4c/8G/100G. Per-tenant memory budget assumes ~1.25 GB warm for the agent + Beeper Desktop (added post-spin). Host tenant ceilings (planning): NEST 128 GB ≈ 90 tenants, R730 128 GB ≈ 90, APO 384 GB ≈ 270.

---

## 3. Agent runtime layout

```
/home/alagad/.hermes/
├── config.yaml                       # agent config (model, compression, guardrails, system_prompt)
├── .env                              # secrets (PLACEHOLDERS in template)
├── state.db                          # conversation state (SQLite, WAL)
└── hermes-agent/
    ├── agent/                        # core loop: conversation_loop.py, run_agent.py,
    │                                 #   tool_guardrails.py, tool_dispatch_helpers.py, ...
    ├── gateway/run.py                # messaging gateway (webhook 127.0.0.1:8644)
    └── plugins/                      # output-sanitize, web-answer, send-terminal-signal, web, ...

/opt/alagad-bridge/                   # inbound DM bridge (systemd: alagad-bridge.service)
/usr/local/bin/alagad-firstboot       # per-tenant injection hook (runs on clone first boot)
/etc/systemd/system/hermes-gateway.service.d/answer.conf   # web_answer env drop-in
/etc/nftables.d/alagad-tenant.nft     # tenant firewall v3
```

Messaging model: per-tenant **Beeper Desktop** (headless Electron) is installed **post-spin**, not baked — the template carries the bridge + gateway wiring but not Beeper itself or any messaging credentials.

---

## 4. Baked-in fixes & configuration (the bake set)

Everything below is present and verified in the template as of the 2026-06-02 bake. Each item was developed and proven on the live customer agent (CT 5000) before baking.

### 4.1 Tool-bypass fix ("Fix-A") — core agent files
Prevents the agent's post-send bare-text narration from accumulating and flipping the model into a tool-bypass (bare-text) mode. Drop-pre-persist + `_has_fresh_tool_tail` carve-out + warning silence, across `agent/conversation_loop.py`, `run_agent.py`, `gateway/run.py`. Patch of record: `patches/toolbypass-fix-v0.14.0/`.
**Fold-ins:** `bridge.yaml transcript.inject:false`; `config.yaml session_reset.idle_minutes:1440`.

### 4.2 Send-cap guardrail (per-turn message cap)
Stops the "reworded-duplicate storm" (agent sending the same answer many times in one turn). The native `ToolCallGuardrailController` is extended with a per-tool total cap; on reaching it, a `block` cleanly ends the turn with a **suppressed (empty) halt string** so no guardrail text reaches the customer.
- `config.yaml` (top-level): `tool_loop_guardrails: per_tool_total_halt_after: { mcp_beeper_send_message: 3 }`
- `agent/tool_guardrails.py` (per-turn total counter), `run_agent.py` (`_toolguard_controlled_halt_response` returns `""` for `same_tool_total_halt`).

### 4.3 Context window + bloat clamps
- `model.context_length: 128000` (raised from 64k; the shared vLLM/LiteLLM ceilings are already at 128k fleet-wide — the template carries only the Hermes-side value).
- `model.max_tokens: 2048` (caps per-reply output; prevents runaway 50k-char generations).
- `compression.threshold: 0.50`, `compression.protect_last_n: 12`.
- Tool-result clamp: `_TOOL_RESULT_MAX_CHARS = 32000` in `agent/tool_dispatch_helpers.py` — truncates oversized tool results (e.g. large web_extract output) before they enter context. Fail-open.

### 4.4 Output sanitizer + Facebook URL handling
`plugins/output-sanitize`: strips Markdown/HTML to plain text on every outbound message (DM channels render neither). **Facebook-only** URL reduction: on the `local-facebook` channel, URLs are reduced to their bare registrable domain (`https://x.com/path` → `x.com`) because Facebook Messenger silently drops outbound messages with clickable links from automated-pattern accounts; bare domains deliver. Instagram keeps clickable links. Channel-scoped, fail-open. Patch of record: `patches/fb-url-bare-domain-v0.14.0/`.

### 4.5 Web answer (search) + per-tenant answer path
`plugins/web-answer` registers the `web_answer` tool (gated on `ALAGAD_ANSWER_URL`). Synthesized, cited answers from the shared Perplexica/SearXNG/gemma4-26b RAG stack via the multi-tenant answer adapter (CT 9302). **New this bake:** `answer.conf` systemd drop-in (placeholder URL; firstboot mints the per-tenant `antk_` token). See `docs/alagad-search-implementation.md` for the full search architecture.

### 4.6 Research-quality system prompt
`agent.system_prompt` (Sessions R/S): plain-text-only formatting (no HTML/Markdown — channels render raw markup); length matches the request (concise for chitchat, thorough for lists/research); **directive tool selection** — `web_answer` is the default for any factual/research/list question, `web_search` only for raw links; citations relayed as plain-text "Sources: Outlet (domain.com)" (never `[1][2]`); lead with a sourced answer rather than refusing, point to trackers as a complement. Patch of record: `patches/research-quality-prompt-20260602/`.

### 4.7 Tenant firewall v3
`/etc/nftables.d/alagad-tenant.nft` — allows tenant egress to the answer adapter (`192.168.8.242:8700`) among the standard tenant rules.

### 4.8 Send-terminal-signal plugin
`plugins/send-terminal-signal` — complements the send-cap by giving the send tool a clearer terminal/"delivered" state, reducing the model's tendency to re-send.

---

## 5. Secrets & per-tenant injection contract

**The template carries NO live secrets.** Verified placeholders:
| Secret | Template state | Filled at first boot by |
|---|---|---|
| LiteLLM API key | `.env`: `LITELLM_KEY_PLACEHOLDER` | firstboot mints per-tenant key |
| Answer adapter token | `ALAGAD_ANSWER_URL` placeholder | firstboot mints fresh `antk_` token (per-tenant) |
| Webhook secret | `config.yaml`: `__WEBHOOK_SECRET__` | (inert — see §7) |
| Beeper token (`bdapi_`) | ABSENT | set up post-spin (Beeper Desktop install) |
| Facebook login / chat room | ABSENT | set up post-spin |

**Injection mechanism:** `/usr/local/bin/alagad-firstboot` runs on a clone's first boot. It detects a tenant hostname (`t-<tenant>-<workspace>` pattern), calls the platform API for the per-tenant config (`workspace_id`/`workspace_slug`), mints/injects the per-tenant credentials, and exits. If it boots in template-mode (hostname doesn't match a tenant pattern) it exits 0 without injecting — so the template itself never self-provisions.

**This is the core safety property:** a tenant can never inherit another tenant's (or Richard's) identity, because identity secrets are minted per-clone at boot, not baked.

---

## 6. Provisioning & bake operations

**Provision a tenant (clone from template):**
```
python3 /root/scripts/spin-workspace.py <workspace-name>
```
Clones CT 9000 via FeatherPanel → tenant LXC boots → `alagad-firstboot` injects per-tenant secrets → gateway starts. (Beeper Desktop + messaging credentials are configured post-spin.)

**Rollback / re-bake mechanism (IMPORTANT — basevol):**
CT 9000's rootfs is a ZFS **basevol**, so `pct snapshot` does **NOT** work on it. Use dataset-level ZFS snapshots:
```
# snapshot before a bake:
zfs snapshot vmpool2/basevol-9000-disk-0@pre-<change>-<date>
# roll back:
pct stop 9000
zfs rollback vmpool2/basevol-9000-disk-0@pre-<change>-<date>
```
`zfs rollback` destroys snapshots newer than the target, and must not be rolled back past `@__base__` or any snapshot a tenant linked-clone depends on (CT 9100 depends on `@__base__`). Current bake snapshots: `@pre-session-c-bake-20260602`, `@post-session-c-bake-20260602`.

**Bake validation:** a bake is only "complete" after a throwaway clone spun via the normal `spin-workspace.py` path boots healthy with its own per-tenant secrets and the full bake set. Logs/md5 alone are not sufficient — the clone-validate is the gate.

**Bake manifest of record:** `patches/BAKE-MANIFEST-session-c-20260602.md`.

---

## 7. Known follow-ups (documented, not blocking)

- **Webhook secret is an inert placeholder.** Clones boot with `__WEBHOOK_SECRET__`; this is functionally inert today (the webhook is loopback-only at 127.0.0.1:8644 and the bridge sends no auth, so the gateway doesn't enforce it). **If real loopback webhook auth is ever enabled, firstboot must mint+inject a per-tenant value into BOTH the gateway config and the bridge `auth_token`** — otherwise all tenants would share the placeholder string.
- **Stale config comment.** `config.yaml` near line 111 still reads "64000 tokens with 50% compression threshold"; the actual value is `128000`. Cosmetic; fix on next edit.
- **mem0 memory layer is OFF** (`memory.provider: ""`). Deferred by operator decision. It is the durable answer to "compression loses customer facts over long conversations" (even at 128k, long threads lose middle-context recall). Recommended as a future enhancement; not baked.

---

## 8. Shared infrastructure the template depends on (NOT baked per-tenant)

These are shared services every tenant uses; they live outside the template and must be healthy for tenants to function:

| Service | Address | Role |
|---|---|---|
| LiteLLM proxy | 192.168.8.136:4000 (node2, Windows/Docker) | Routes `gemma4-26b` across the GPU fleet; 128k `max_input_tokens` |
| Embeddings | 192.168.8.136:11434 | nomic-embed-text (Perplexica reranking) |
| Answer adapter | 192.168.8.242:8700 (CT 9302) | Multi-tenant search/answer policy + billing layer |
| Perplexica | 192.168.8.243:3000 (CT 9303) | RAG synthesis (v1.10.2 pinned) |
| Platform/firstboot API | (platform UI) | Serves per-tenant config to `alagad-firstboot` |
| FeatherPanel | CT 9200, 192.168.8.246:4831 | Clone/provisioning orchestration |
| GPU inference fleet | FORGE/.233, TITAN/.230, HYDRA/.231, SCOUT | gemma4-26b backends (128k max_model_len) |

SCOUT (32 GB) is the KV-cache-starved bottleneck backend; re-measure tenant concurrency at 128k against SCOUT before scaling tenant count.

---

## 9. Patches of record (in this repo)

- `patches/toolbypass-fix-v0.14.0/` — Fix-A (tool-bypass)
- `patches/fb-url-bare-domain-v0.14.0/` — Facebook outbound URL reduction
- `patches/research-quality-prompt-20260602/` — research-quality system prompt + web_answer steer
- `patches/BAKE-MANIFEST-session-c-20260602.md` — the bake manifest

The send-cap guardrail (4.2) and context-window/clamp (4.3) changes touch core Hermes files (`tool_guardrails.py`, `run_agent.py`, `tool_dispatch_helpers.py`, `conversation_loop.py`) — **these must be re-applied after any Hermes version upgrade**, as an upgrade would overwrite them.

---

*Verified byte-level against the live stopped CT 9000 template, 2026-06-02. Secrets redacted/confirmed-placeholder. Companion docs: `docs/alagad-search-implementation.md`, `patches/BAKE-MANIFEST-session-c-20260602.md`.*
