# gws — Google Workspace tools (Calendar / Contacts / Sheets)

Hermes plugin that gives the tenant agent **its own** Google Calendar, Contacts, and
Sheets, through the Alagad **GWS proxy** (CT 9470, `http://192.168.8.247:8800`). **No Gmail.**

## Tools

| Tool | Proxy endpoint | When the model uses it |
|---|---|---|
| `calendar_upcoming` | `GET /api/gws/calendar/upcoming` | "what's on my calendar", look up an event |
| `calendar_slots` | `GET /api/gws/calendar/slots` | find free times to offer |
| `calendar_book` | `POST /api/gws/calendar/book` | create a confirmed event |
| `calendar_cancel` | `DELETE /api/gws/calendar/cancel` | delete an event (needs `event_id`) |
| `contacts_add` | `POST /api/gws/contacts/add` | save a contact |
| `contacts_search` | `GET /api/gws/contacts/search` | look someone up |
| `sheets_append` | `POST /api/gws/sheets/append` | log a row |
| `sheets_read` | `GET /api/gws/sheets/read` | read a range |

## Config (per tenant)

Two env vars (baked into the tenant's Hermes environment):

```
GWS_PROXY_URL=http://192.168.8.247:8800
GWS_PROXY_TOKEN=<per-workspace Fernet bearer, minted by the proxy>
```

Enable in `config.yaml`:

```yaml
plugins:
  enabled: [gws]        # plus whatever else
tools:
  messaging:
    enabled: [..., gws] # the 'gws' toolset must be enabled
```

## Security

Identity is carried **entirely** by `GWS_PROXY_TOKEN` — the proxy decrypts it to
recover `{ws, tenant}`. **No tool takes a workspace id**, so a prompt-injected agent
processing untrusted inbound messages can only ever reach its own tenant's Google.
Raw proxy/Google error bodies (which carry the account email + GCP project id) are
never surfaced — handlers return clean messages and never raise into the agent loop.
