# Alagad Search — Implementation Documentation

**Component:** `web_answer` / Alagad Answer Layer
**Status:** Live (Phase 1), single customer (Richard Dayton, CT 5000)
**Last verified:** 2026-06-01 (byte-level, against live infrastructure)
**Owner:** Rob (PAL Tech LLC) — infra in Carmel, Indiana

---

## 1. What it is (the one-paragraph version)

Alagad Search gives each tenant's Hermes agent a single tool, **`web_answer`**, that takes a natural-language question and returns a synthesized, cited answer drawn from a live web search. The agent does not see raw search results or scrape pages itself; it asks one question and gets back one finished answer plus a list of source URLs. Behind that tool sits a self-hosted RAG pipeline — **SearXNG** (metasearch) → **Perplexica** (retrieval + synthesis orchestration) → **gemma4-26b** (the synthesis LLM, on owned GPU hardware via LiteLLM) — fronted by a **multi-tenant answer adapter** that adds per-tenant tokens, quotas, rate limits, an aggregate cost budget, a safety filter, caching, and an audit log. Everything runs on owned infrastructure; there is no third-party search/answer API in the path.

---

## 2. Why it exists (design rationale)

**Why a single `web_answer` tool instead of raw search + scrape tools.**
Hermes ships with `web_search` (SearXNG) and `web_extract` (page fetch) primitives. Giving a small tenant model those primitives means the model has to drive multi-step retrieval, decide what to fetch, read long pages, and synthesize — burning context and tokens, and producing inconsistent quality on gemma4-26b. A single buffer-and-return `web_answer` tool collapses that into one call: the heavy RAG orchestration happens in Perplexica (purpose-built for it), and the agent receives a clean, cited paragraph it can relay to the customer. This is faster, cheaper in agent tokens, and far more reliable for the SMB use case (e.g. "what time does that mall open", "what are the visa requirements").

**Why self-hosted (SearXNG + Perplexica + local LLM) instead of a hosted answer API.**
The flat-rate `₱2,999/mo unlimited` business model cannot absorb per-query metered API costs. Owned-infra synthesis makes inference effectively free at the margin (the GPUs are already paid for), which is what makes "unlimited" viable. The adapter still tracks an *estimated* aggregate budget as a guardrail, but there is no real per-call vendor bill.

**Why a separate multi-tenant adapter instead of pointing the agent straight at Perplexica.**
Perplexica is single-tenant and has no concept of tenants, tokens, quotas, billing, or abuse controls. The adapter (CT 9302) is the layer that makes one shared Perplexica safe to expose to many paying tenants: per-tenant tokens, per-tenant monthly quotas, per-tenant rate limits, an aggregate spend cap, a query safety filter, a shared cache, and a per-call audit trail. It is the policy/billing/safety boundary; Perplexica is just the synthesis engine.

**Why gemma4-26b for synthesis.**
Synthesis is a *grounded* task — the source snippets are supplied in the prompt, so the model's job is faithful extraction and clear organization, not deep reasoning or broad world-knowledge. gemma4-26b handles this reliably (verified on multi-source and conflicting-source synthesis tests: correct extraction, clear structure, balanced handling of source disagreement, no hallucination). It is the same model the tenant agent already runs, so no extra model needs to be hosted. A larger/different model (e.g. Qwen3-30B-A3B) was considered but is **not** hosted anywhere and buys little on grounded synthesis specifically; gemma4-26b was tested first and found sufficient.

---

## 3. How it works (end-to-end flow)

```
Customer (Messenger/IG DM)
      │
      ▼
Hermes agent (CT 5000)  ── decides it needs a web answer
      │  calls tool: web_answer(query, focus_mode?)
      ▼
web-answer plugin (in-agent)
      │  POST {ALAGAD_ANSWER_URL}/answer   (token is IN the URL path)
      │  → http://192.168.8.242:8700/t/<token>/answer
      ▼
Alagad Answer Adapter (CT 9302, FastAPI/uvicorn :8700)
      │  1. resolve token → tenant   (sha256 hash lookup, Postgres)
      │  2. focus-mode allow-list check
      │  3. monthly per-tenant quota check (soft/hard)
      │  4. aggregate USD budget check (soft/hard)
      │  5. per-tenant rate limit (Redis sliding window)
      │  6. safety filter on the query (regex rules)
      │  7. cache lookup (Redis, keyed by query+focus_mode)
      │       └─ HIT → return cached answer (~9 ms)
      │  8. MISS → call Perplexica
      ▼
Perplexica (CT 9303, Docker :3000)  POST /api/search  (stream:false)
      │  a. SearXNG metasearch → candidate URLs + snippets
      │  b. embed + rerank snippets (nomic-embed-text)
      │  c. synthesis prompt → LLM
      ▼
LiteLLM proxy (192.168.8.136:4000)  → model "gemma4-26b"
      │  routes to a healthy local GPU backend (weighted)
      ▼
gemma4-26b on owned GPU fleet  → synthesized cited answer
      │
      ▼ (answer + sources bubble back up)
Adapter: trim sources, audit-log (billable), record spend, cache result
      │
      ▼
web-answer plugin → returns answer to agent
      │
      ▼
Agent relays the answer to the customer (output-sanitize plugin applies;
on Facebook, URLs in the answer are reduced to bare domains — see §9)
```

### Step detail

1. **Agent decides.** The `web_answer` tool is registered into Hermes' existing `web` toolset. It only appears if `ALAGAD_ANSWER_URL` is set for the tenant (`requires_env` + `check_fn` gate) — a tenant without search wired simply doesn't see the tool, no error.
2. **Tenant-side call.** The plugin POSTs `{"query": ...}` (optionally `focus_mode`) to the adapter. The **token is carried in the URL path**, exactly mirroring how `SEARXNG_URL` / `TAVILY_BASE_URL` are configured in Hermes. Client timeout is **150 s** (above the adapter's 120 s Perplexica timeout, so a slow-but-successful synthesis is not cut off client-side).
3. **Adapter policy pipeline** (in strict order — cheap checks before expensive work): token resolution → focus-mode allow-list → monthly quota → aggregate budget → rate limit → safety filter → cache. Only on a cache miss does it call Perplexica.
4. **Perplexica RAG.** SearXNG returns candidate results; Perplexica embeds/reranks with nomic-embed-text, builds a synthesis prompt with the top snippets, and calls the chat model. `stream:false` — the adapter buffers the complete answer (v1 deliberately does not stream through the audit/quota layer).
5. **Synthesis.** LiteLLM routes `gemma4-26b` to a healthy local GPU backend (weighted round-robin across the fleet). The model produces a cited answer (`[1]`, `[15]`, …) referencing the sources.
6. **Shape + record.** Adapter trims sources to the token's `max_sources_per_query` (default 5), writes a billable audit-log row, increments aggregate spend, caches the shaped result, and returns it.
7. **Relay.** The agent sends the answer to the customer. The output-sanitize plugin runs on the way out (strips markdown/HTML; on Facebook reduces URLs to bare domains — §9).

---

## 4. Where it runs (infrastructure map)

| Component | Location | Address | Notes |
|---|---|---|---|
| Hermes agent + `web-answer` plugin | CT 5000 | 192.168.8.200 | Tenant agent; plugin in `plugins/web-answer/` |
| **Answer adapter** | CT 9302 | 192.168.8.242:8700 | FastAPI/uvicorn, systemd `alagad-answer`, 1 worker |
| Adapter Redis | CT 9302 | localhost:6379 | Rate-limit + cache |
| **Perplexica** | CT 9303 | 192.168.8.243:3000 | Docker `perplexica-app-1`, v1.10.2 pinned |
| Bundled SearXNG | CT 9303 | `searxng:8080` (compose-internal) | Docker `perplexica-searxng-1` |
| **LiteLLM proxy** | host | 192.168.8.136:4000 | Routes `gemma4-26b` to GPU fleet |
| Embeddings (nomic-embed-text) | host | 192.168.8.136:11434 | Ollama; used by Perplexica reranking |
| Audit/token/budget DB | DB-SERVER1 | 192.168.8.172:5432, db `alagad`, schema `search` | PostgreSQL 17.6 |

**Process/runtime facts:**
- Adapter: `uvicorn alagad_answer.main:app --host 0.0.0.0 --port 8700 --workers 1`, `PYTHONPATH=/opt/alagad-answer/src`, `Restart=on-failure`. Memory footprint ~70 MB.
- Perplexica is **vanilla upstream v1.10.2, pinned, not forked.** The *only* supported customization surface is `config.toml` at `/opt/perplexica/config.toml` (bind-mounted into the container).

---

## 5. Model & retrieval configuration (exact, live)

**Perplexica `config.toml` (CT 9303):**
- `[GENERAL] SIMILARITY_MEASURE = "cosine"`, `KEEP_ALIVE = "5m"`
- Synthesis model → `[MODELS.CUSTOM_OPENAI]`: `API_URL = http://192.168.8.136:4000/v1`, `MODEL_NAME = "gemma4-26b"`, key = LiteLLM master key.
- Embeddings → `[MODELS.OLLAMA] API_URL = http://192.168.8.136:11434` (LAN IP, not `host.docker.internal`, because `.136` is a separate host), model `nomic-embed-text`.
- All hosted-vendor model keys (OpenAI/Groq/Anthropic/Gemini/DeepSeek) intentionally blank.
- `[API_ENDPOINTS] SEARXNG = http://searxng:8080` (compose-internal service name).

**Adapter model wiring (`config.py` / `.env`, CT 9302):**
- `chat_model_provider = "custom_openai"`, `chat_model_name = "gemma4-26b"`
- `embedding_model_provider = "ollama"`, `embedding_model_name = "nomic-embed-text:latest"`
- `default_focus_mode = "webSearch"`, `default_optimization_mode = "balanced"`
- `backend_name = "perplexica-1.10.2"` (recorded in every audit row)

**Note on the synthesis-model roadmap.** `config.toml` references a future `alagad-synthesis-primary` alias → Qwen3-30B-A3B on R9700. This is **not deployed** (Qwen3-30B is not hosted anywhere) and is a *post-template fleet-utilization* idea, not a quality fix. Phase 1 ships gemma4-26b, which was validated as sufficient. `gpt-oss-120b` is explicitly out of plan — owned-infra synthesis is the architectural choice.

---

## 6. The adapter API contract

### Tenant endpoint
```
POST /t/{token}/answer
Content-Type: application/json
Body:   { "query": "<question>", "focus_mode": "<optional, default webSearch>" }

200 OK:
{
  "answer":       "<synthesized cited text>",
  "sources":      [ { ...source objects... } ],   // trimmed to max_sources
  "focus_mode":   "webSearch",
  "cached":       false,
  "fetch_ms":     34596,
  "source_count": 5
}
```

### Error contract (status → meaning, surfaced to agent as clean messages)
| Status | error_category | Meaning |
|---|---|---|
| 400 | missing query / focus_mode_not_allowed | Bad request or focus mode not permitted for the token |
| 401 | (invalid token) | Token invalid or revoked |
| 429 | quota_exhausted / rate_limited | Monthly hard quota hit, or per-tenant rate limit |
| 451 | (safety category) | Query blocked by the safety filter |
| 502 | upstream_error / empty_answer / bad_upstream_json | Perplexica/synthesis backend error |
| 503 | budget_exhausted / backend_unavailable | Aggregate USD cap hit, or Perplexica unreachable |
| 504 | upstream_timeout | Synthesis exceeded the adapter timeout |

The in-agent plugin maps each status to a plain-English tool message (no stack traces reach the agent), e.g. 429 → "answer service rate or quota limit reached - try again later".

### Admin endpoints (bearer `ANSWER_ADMIN_TOKEN`)
- `GET /admin/budget` → month-to-date USD, soft/hard caps, exceeded flags.
- `GET /admin/tenant/{tenant_id}/quota` → tenant month-to-date count vs soft/hard.
- `GET /health` → `{redis, db, perplexica}` booleans; `status: ok|degraded`.

---

## 7. Multi-tenant controls (the policy layer)

All defaults live in `config.py`; per-token overrides live in the DB row.

**Tokens** (`search.tenant_answer_token`):
- Format `antk_` + 32 url-safe random bytes. **Only the SHA-256 hash is stored**; the raw token lives only in the tenant's `ALAGAD_ANSWER_URL`. Resolution is hash-lookup; `revoked_at` non-null = dead. `last_used_at` updated each call.
- Per-token knobs: `rate_max` (default 1), `rate_window_s` (default 10), `monthly_quota_soft` (1000), `monthly_quota_hard` (1500), `max_sources_per_query` (5), `focus_modes_allowed` (null = all).

**Quota** — monthly per-tenant call count (from the audit log), checked *before* doing work. Soft = warn; hard = 429 `quota_exhausted`. Defaults 1000/1500 (3× empirical headroom).

**Rate limit** — Redis sliding window, per tenant. Default 1 call / 10 s.

**Aggregate budget** (`search.budget_tracking`) — month-to-date estimated USD across all tenants. `estimated_cost_per_call = $0.005` (Perplexica exposes no real per-call cost; this is a guardrail estimate, not a vendor bill). Soft = $150 warn; hard = $300 → 503 `budget_exhausted`.

**Safety filter** — regex pattern rules (lifted from CT 9300/9301) applied to the query; a block returns 451 and is audited with the category.

**Cache** — Redis, keyed by `(query, focus_mode)`, TTL 300 s. Cache hits cost $0, are audited with `cached:true`, and return in ~9 ms.

**Audit log** (`search.tenant_answer_log`) — one row per call: tenant, query, focus_mode, source_count, latency_ms, cached, status_code, error_category, estimated_cost_usd, backend_used, requested_at. This is the billing/quota source of truth and the observability surface.

---

## 8. Performance (live-measured 2026-06-01)

| Path | Latency | Notes |
|---|---|---|
| Cold synthesis (cache miss, full RAG) | **~35 s** | SearXNG + rerank + gemma4-26b synthesis. `fetch_ms: 34596` on a 5-source, ~2000-char answer. Inherent to RAG, not a fault. |
| Cache hit | **~9 ms** | `fetch_ms: 9`; ~3800× faster. TTL 300 s. |
| Bare model call (synthesis only, no retrieval) | 0.1–0.4 s | gemma4-26b on the fleet directly. |

The cold-path cost is dominated by retrieval + multi-source synthesis, which is expected for a RAG answer. The cache absorbs repeated/popular queries. The 150 s client timeout and 120 s adapter timeout give comfortable headroom over the ~35 s typical.

**Reliability note (lesson learned):** a single slow GPU backend can stall synthesis. A May-2026 incident (HYDRA/.231 dual-PSU power-sync fault left one R9700 un-enumerated → CPU fallback → multi-minute stalls) was root-caused and fixed by consolidating both GPUs onto one PSU. LiteLLM health-check hardening (real tiny generation per chat model rather than a metadata-only probe) is a pending improvement to auto-eject a backend hung *on generation*.

---

## 9. Interaction with message delivery (Facebook URL handling)

Synthesized answers frequently contain source URLs. Facebook Messenger **silently drops outbound messages from the agent's account that contain clickable links** (proven by controlled send tests; documented Meta anti-spam behavior for automated-pattern accounts). Instagram is unaffected. Therefore the **output-sanitize** plugin, on the Facebook channel only (chatID contains `local-facebook`), reduces every URL in the outbound text to its **bare registrable domain** (`https://x.com/path` → `x.com`). This is channel-scoped (IG keeps clickable links) and fails open (never blocks a send). See the `fb-url-bare-domain` patch in this repo. This matters for search because answers are the main source of outbound links.

---

## 10. When it was built / timeline

- **2026-05-31** — Answer adapter (CT 9302) built and deployed: FastAPI service, `search` DB schema (token/log/budget tables via Alembic), Redis, safety filter, full policy pipeline. `web-answer` plugin added to CT 5000; `ALAGAD_ANSWER_URL` wired with the tenant token; tenant firewall opened for `.242` egress.
- **2026-05-31** — Perplexica (CT 9303) standardized on vanilla v1.10.2, `config.toml` pointed at gemma4-26b synthesis + nomic embeddings via LiteLLM.
- **2026-06-01** — End-to-end verified live (this document): real tenant-path call returned a 5-source cited answer in ~35 s; cache hit in ~9 ms; gemma4-26b synthesis quality validated on multi-source and conflicting-source tests. Judged **sufficient for Phase 1 / template bake**.

---

## 11. Operational quick-reference

**Restart adapter:** `pct exec 9302 -- systemctl restart alagad-answer`
**Adapter health:** `curl -s http://192.168.8.242:8700/health`
**Perplexica health:** `pct exec 9303 -- docker ps` (expect `perplexica-app-1`, `perplexica-searxng-1` healthy)
**Mint a tenant token:**
```
cd /opt/alagad-answer
PYTHONPATH=src venv/bin/python3 -c "from alagad_answer.tokens import issue_answer_token; print(issue_answer_token('<tenant-id>', ttl_seconds=...))"
```
**Check tenant quota:** `GET /admin/tenant/{tenant_id}/quota` (bearer admin token)
**Check budget:** `GET /admin/budget` (bearer admin token)
**Audit/billing query (read-only):** Postgres `search.tenant_answer_log` on `192.168.8.172` db `alagad`.

**Key config files:**
- Adapter: `/opt/alagad-answer/.env`, `/opt/alagad-answer/src/alagad_answer/config.py`
- Perplexica: `/opt/perplexica/config.toml` (the *only* supported customization point; do not modify Perplexica source)
- Tenant plugin: CT 5000 `plugins/web-answer/`, env `ALAGAD_ANSWER_URL` in `/home/alagad/.hermes/.env`

---

## 12. Template-bake checklist (search-specific)

When baking CT 9000:
1. Include the `web-answer` plugin (gated on `ALAGAD_ANSWER_URL`; absent env = tool hidden, safe).
2. **Do NOT bake a tenant token.** `ALAGAD_ANSWER_URL` must be a placeholder; `spin-workspace.py` mints a fresh per-tenant token and writes the real URL at provision time. (A baked token = every tenant shares one identity — correctness + billing failure.)
3. Tenant firewall must allow egress to `192.168.8.242:8700`.
4. Adapter (9302), Perplexica (9303), LiteLLM (.136), embeddings (.136:11434) are shared infra — not per-tenant, not baked into the tenant image.
5. Output-sanitize plugin (incl. the Facebook bare-domain URL reducer) ships in the bake so search answers' links deliver on Facebook.

---

*Verified byte-level against live infrastructure 2026-06-01. Secrets (tokens, DB passwords, admin token) intentionally omitted/redacted in this document.*
