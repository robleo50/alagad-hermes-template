# web-answer plugin

Registers one Hermes tool — **`web_answer`** — that returns a synthesized,
cited answer to a factual question. It is the client side of the Alagad
**Answer** middleware (Perplexica-backed synthesis behind a multi-tenant,
per-tenant-tokened adapter on CT 9302, `192.168.8.242:8700`).

This completes the web-capability trio for tenant agents:

| Tool | Backend | Returns |
|---|---|---|
| `web_search` | CT 9300 search (SearXNG→Brave) | a list of result links |
| `web_extract` | CT 9301 fetch (Scrapling, Tavily-compatible) | the contents of given URLs |
| **`web_answer`** | **CT 9302 answer (Perplexica)** | **a written, cited answer synthesized across sources** |

## Files

- `plugin.yaml` — manifest (`kind: backend`, `provides_tools: [web_answer]`); auto-loads, no opt-in.
- `__init__.py` — `register(ctx)` → `ctx.register_tool("web_answer", toolset="web", …, is_async=True, requires_env=["ALAGAD_ANSWER_URL"])`.
- `tools.py` — `WEB_ANSWER_SCHEMA` (bare `{name, description, parameters}` form) + async handler + availability gate + answer/source formatting.
- `client.py` — async httpx client; `POST {ALAGAD_ANSWER_URL}/answer`; maps the adapter's 401/429/451/503/timeout responses to clean tool-error strings.

Mirrors the bundled `plugins/spotify` (tool-registering plugin) and
`plugins/web/tavily` (HTTP-to-an-external-tokened-service). Built against
Hermes 0.14.0.

## Configuration

The tool gates on a single env var — the per-tenant tokened adapter base:

```
ALAGAD_ANSWER_URL=http://192.168.8.242:8700/t/<answer-token>
```

(Same shape as `SEARXNG_URL` / `TAVILY_BASE_URL`.) The handler POSTs to
`{ALAGAD_ANSWER_URL}/answer`. Mint a per-tenant token on CT 9302:

```
cd /opt/alagad-answer && PYTHONPATH=src venv/bin/python scripts/issue_answer_token.py <tenant-alias>
```

The raw `antk_…` token is printed once (indented line); only its SHA-256 hash
is persisted server-side.

### Where the env var goes, per tenant type

- **CT 9000 clones (systemd-gateway):** a `hermes-gateway.service.d/answer.conf`
  drop-in (`Environment="ALAGAD_ANSWER_URL=…"`) — same mechanism as
  `searxng.conf` / `tavily.conf`. `spin-workspace.py` substitutes
  `ANSWER_TOKEN_PLACEHOLDER` once `answer.conf` is baked into CT 9000.
- **CT 5000 (legacy, manual-launch):** `~/.hermes/.env`, then a manual gateway
  restart. CT 5000 does not use the drop-in pattern.

### Network prerequisite (tenant egress firewall)

Tenant CTs run an egress allowlist (`/etc/nftables.d/alagad-tenant.nft`,
`alagad-tenant-fw.service`) baked into CT 9000. It must allow the answer
adapter, or `web_answer` cannot connect from isolated-bridge tenants:

```
define ANSWER = 192.168.8.242
ip daddr $ANSWER tcp dport 8700 accept   # web answer middleware (CT 9302)
```

This is **tenant-fw v3** (2026-05-31); bake into CT 9000 alongside the
`answer.conf` drop-in. Legacy CT 5000 has no egress firewall, so it reaches
.242 without this.

## Focus modes

`web_answer` accepts an optional `focus_mode` (passed through to Perplexica):
`webSearch` (default), `academicSearch`, `writingAssistant`,
`wolframAlphaSearch`, `youtubeSearch`, `redditSearch`.

## Validated

2026-05-31, on a throwaway CT 9000 clone (Hermes 0.14.0): cold-load with no
warnings; `web_answer` registered; an R9700-spec query returns an accurate
cited answer (RDNA 4 / 32GB GDDR6); `focus_mode` passthrough confirmed in the
audit log; 451 (safety) and 429 (rate-limit) surface as clean tool errors;
coexists with `web_search` / `web_extract`; the agent invokes it end-to-end
via the gateway. Backend: `perplexica-1.10.2` on CT 9303.
