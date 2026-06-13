# gws — Google Workspace tools (Calendar / Contacts / Sheets)

Hermes plugin giving the tenant agent **its own** connected Google Calendar, Contacts,
and Sheets, through the Alagad **GWS proxy** (CT 9470, `http://192.168.8.247:8800`).
**No Gmail, no Drive.**

This is a single-file plugin (`__init__.py`) — a faithful record of what is deployed and
proven on the CT 5000 pilot.

## Tools (10)

| Tool | Proxy endpoint | Notes |
|---|---|---|
| `calendar_upcoming` | `GET /api/gws/calendar/upcoming` | the user's own calendar |
| `calendar_slots` | `GET /api/gws/calendar/slots` | free slots via events.list (not freeBusy) |
| `calendar_book` | `POST /api/gws/calendar/book` | create event |
| `calendar_cancel` | `DELETE /api/gws/calendar/cancel` | needs `event_id` |
| `contacts_add` | `POST /api/gws/contacts/add` | |
| `contacts_search` | `GET /api/gws/contacts/search` | |
| `sheets_read` | `GET /api/gws/sheets/read` | by sheet ID/link |
| `sheets_append` | `POST /api/gws/sheets/append` | append one row |
| `sheets_update` | `POST /api/gws/sheets/update` | **explicit bounded range only** |
| `sheets_clear` | `POST /api/gws/sheets/clear` | **explicit bounded range only** |

## Config (per tenant)

```
GWS_PROXY_URL=http://192.168.8.247:8800
GWS_PROXY_TOKEN=<per-workspace Fernet bearer, minted by the proxy>
```
Enable: add `gws` to `plugins.enabled` and to `tools.messaging.enabled` in `config.yaml`.

## Security

Identity is carried entirely by `GWS_PROXY_TOKEN` (the proxy decrypts it to `{ws, tenant}`).
**No tool takes a workspace id** — a prompt-injected agent can only reach its own tenant's
Google. Sheets write ops require an explicit bounded range (e.g. `Sheet1!A2:D2`); the proxy
rejects whole-sheet / unbounded targets so the agent can't blank a sheet. Raw Google/proxy
error bodies are never surfaced.
