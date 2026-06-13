"""Alagad gws plugin — Google Calendar / Contacts / Sheets via the GWS proxy.

Registers 10 tools into the 'gws' toolset; each calls the per-workspace Alagad GWS
proxy at $GWS_PROXY_URL with Bearer $GWS_PROXY_TOKEN. No tool takes a workspace id
— identity is the bearer (the proxy decrypts it to {ws, tenant}). Env-gated, so a
tenant without GWS wired never sees the tools. Handlers never raise into the agent
loop; proxy errors become clean messages. No Gmail, no Drive.

Tool descriptions set expectations honestly: calendar/contacts act on the user's OWN
connected account; Sheets is addressed by ID/link (no Drive name-search) and write
ops target an explicit bounded range only (never a whole sheet).
"""
from __future__ import annotations

import os
from typing import Any

ENV_URL = "GWS_PROXY_URL"
ENV_TOKEN = "GWS_PROXY_TOKEN"

_ERR = {
    "not_connected": "the Google account isn't connected yet — connect it in the portal",
    "auth_expired": "the Google connection expired and needs reconnecting",
    "scope_insufficient": "the Google connection is missing a needed permission — reconnect and allow all",
    "unknown_workspace": "this workspace isn't recognized — contact the operator",
    "temporarily_unavailable": "the service is briefly unavailable — try again shortly",
    "not_found": "that item wasn't found (check the sheet ID / event id)",
    "bad_request": "the request was invalid (for sheets, give an explicit range like Sheet1!A2:D2)",
    "unauthorized": "the service rejected the agent's credentials — contact the operator",
}


def _available() -> bool:
    return bool(os.getenv(ENV_URL, "").strip() and os.getenv(ENV_TOKEN, "").strip())


async def _call(method: str, path: str, *, params=None, json=None) -> Any:
    import httpx

    base = os.getenv(ENV_URL, "").strip().rstrip("/")
    token = os.getenv(ENV_TOKEN, "").strip()
    if not base or not token:
        return {"_err": "Google isn't configured for this agent"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.request(
                method, f"{base}{path}",
                headers={"Authorization": f"Bearer {token}"}, params=params, json=json,
            )
    except httpx.TimeoutException:
        return {"_err": "the service timed out — try again shortly"}
    except httpx.HTTPError:
        return {"_err": "couldn't reach the service"}
    if 200 <= r.status_code < 300:
        try:
            return r.json()
        except ValueError:
            return {}
    code = None
    try:
        b = r.json()
        code = b.get("error") if isinstance(b, dict) else None
    except ValueError:
        pass
    return {"_err": _ERR.get(code) or f"the service returned an error (HTTP {r.status_code})"}


# ---- Calendar (the user's OWN connected calendar) ----
async def _upcoming(args, **_):
    days = args.get("days") or 7
    d = await _call("GET", "/api/gws/calendar/upcoming", params={"days": days})
    if "_err" in d:
        return f"calendar_upcoming error: {d['_err']}"
    evs = d.get("events") or []
    if not evs:
        return f"No events on the calendar in the next {days} days."
    out = ["Upcoming events:"]
    for e in evs:
        out.append(
            f"- {e.get('summary') or '(no title)'}: {e.get('start')} -> {e.get('end')}"
            f"  (event_id: {e.get('event_id')})"
        )
    return "\n".join(out)


async def _slots(args, **_):
    date = (args.get("date") or "").strip()
    if not date:
        return "calendar_slots error: 'date' (YYYY-MM-DD) is required."
    p = {"date": date, "duration_min": args.get("duration_min") or 30}
    if args.get("tz"):
        p["tz"] = args["tz"]
    d = await _call("GET", "/api/gws/calendar/slots", params=p)
    if "_err" in d:
        return f"calendar_slots error: {d['_err']}"
    s = d.get("slots") or []
    if not s:
        return f"No free {p['duration_min']}-min slots on {date}."
    return f"Free {p['duration_min']}-min slots on {date}:\n" + "\n".join(
        f"- {x.get('start')} -> {x.get('end')}" for x in s
    )


async def _book(args, **_):
    for k in ("start", "end", "summary"):
        if not (args.get(k) or "").strip():
            return f"calendar_book error: '{k}' is required."
    body = {"start": args["start"], "end": args["end"], "summary": args["summary"]}
    for k in ("attendee_email", "description", "tz"):
        if args.get(k):
            body[k] = args[k]
    d = await _call("POST", "/api/gws/calendar/book", json=body)
    if "_err" in d:
        return f"calendar_book error: {d['_err']}"
    return (
        f"Booked '{args['summary']}' from {d.get('start')} to {d.get('end')}. "
        f"(event_id: {d.get('event_id')})"
    )


async def _cancel(args, **_):
    eid = (args.get("event_id") or "").strip()
    if not eid:
        return "calendar_cancel error: 'event_id' is required (get it from calendar_upcoming)."
    d = await _call("DELETE", "/api/gws/calendar/cancel", json={"event_id": eid})
    if "_err" in d:
        return f"calendar_cancel error: {d['_err']}"
    return f"Cancelled the event (event_id: {eid})."


# ---- Contacts (the user's OWN Google Contacts) ----
async def _contacts_add(args, **_):
    name = (args.get("name") or "").strip()
    if not name:
        return "contacts_add error: 'name' is required."
    body = {"name": name}
    for k in ("email", "phone"):
        if args.get(k):
            body[k] = args[k]
    d = await _call("POST", "/api/gws/contacts/add", json=body)
    if "_err" in d:
        return f"contacts_add error: {d['_err']}"
    return f"Added contact '{name}'."


async def _contacts_search(args, **_):
    q = (args.get("q") or "").strip()
    if not q:
        return "contacts_search error: 'q' is required."
    d = await _call("GET", "/api/gws/contacts/search", params={"q": q})
    if "_err" in d:
        return f"contacts_search error: {d['_err']}"
    res = d.get("results") or []
    if not res:
        return f"No contacts matched '{q}'."
    out = [f"Contacts matching '{q}':"]
    for r in res:
        emails = ", ".join(r.get("emails") or []) or "-"
        phones = ", ".join(r.get("phones") or []) or "-"
        out.append(f"- {r.get('name') or '(no name)'} | email: {emails} | phone: {phones}")
    return "\n".join(out)


# ---- Sheets (by ID/link only; write ops target an explicit bounded range) ----
async def _sheets_read(args, **_):
    sid = (args.get("spreadsheet_id") or "").strip()
    rng = (args.get("range") or "").strip()
    if not sid or not rng:
        return "sheets_read error: 'spreadsheet_id' and 'range' are required."
    d = await _call("GET", "/api/gws/sheets/read", params={"spreadsheet_id": sid, "range": rng})
    if "_err" in d:
        return f"sheets_read error: {d['_err']}"
    rows = d.get("values") or []
    if not rows:
        return f"No values in {rng}."
    out = [f"Values in {d.get('range') or rng}:"]
    for row in rows:
        out.append("  " + " | ".join(str(c) for c in row))
    return "\n".join(out)


async def _sheets_append(args, **_):
    sid = (args.get("spreadsheet_id") or "").strip()
    rng = (args.get("range") or "").strip()
    values = args.get("values")
    if not sid or not rng or values is None:
        return "sheets_append error: 'spreadsheet_id', 'range', and 'values' are required."
    if not isinstance(values, list):
        return "sheets_append error: 'values' must be a list of cell values."
    d = await _call(
        "POST", "/api/gws/sheets/append",
        json={"spreadsheet_id": sid, "range": rng, "values": [values]},
    )
    if "_err" in d:
        return f"sheets_append error: {d['_err']}"
    return f"Appended a row. Updated range: {d.get('updated_range')}."


async def _sheets_update(args, **_):
    sid = (args.get("spreadsheet_id") or "").strip()
    rng = (args.get("range") or "").strip()
    values = args.get("values")
    if not sid or not rng or values is None:
        return "sheets_update error: 'spreadsheet_id', 'range', and 'values' are required."
    if not isinstance(values, list):
        return "sheets_update error: 'values' must be a list of cell values."
    d = await _call(
        "POST", "/api/gws/sheets/update",
        json={"spreadsheet_id": sid, "range": rng, "values": [values]},
    )
    if "_err" in d:
        return f"sheets_update error: {d['_err']}"
    return f"Updated range {d.get('updated_range')} ({d.get('updated_cells')} cells)."


async def _sheets_clear(args, **_):
    sid = (args.get("spreadsheet_id") or "").strip()
    rng = (args.get("range") or "").strip()
    if not sid or not rng:
        return "sheets_clear error: 'spreadsheet_id' and 'range' are required."
    d = await _call("POST", "/api/gws/sheets/clear", json={"spreadsheet_id": sid, "range": rng})
    if "_err" in d:
        return f"sheets_clear error: {d['_err']}"
    return f"Cleared range {d.get('cleared_range')}."


def _schema(name, desc, props, required):
    return {
        "name": name,
        "description": desc,
        "parameters": {"type": "object", "properties": props, "required": required},
    }


_TOOLS = [
    ("calendar_upcoming", _schema(
        "calendar_upcoming",
        "List upcoming events on the user's OWN connected Google Calendar. Use when the user "
        "asks what's on their calendar/schedule/agenda, whether they're free, or to look up an "
        "event before changing it. Returns titles, start/end times, and event_id.",
        {"days": {"type": "integer", "description": "How many days ahead to list (default 7)."}},
        []), _upcoming),
    ("calendar_slots", _schema(
        "calendar_slots",
        "Find FREE time slots on the user's own Google Calendar for a date. Use when scheduling "
        "a meeting and you need to offer open times.",
        {"date": {"type": "string", "description": "Date as YYYY-MM-DD."},
         "duration_min": {"type": "integer", "description": "Slot length in minutes (default 30)."},
         "tz": {"type": "string", "description": "Optional IANA timezone."}},
        ["date"]), _slots),
    ("calendar_book", _schema(
        "calendar_book",
        "Create (book) an event on the user's own Google Calendar, once a specific time is agreed. "
        "Provide ISO-8601 start and end (include the timezone offset, e.g. "
        "2026-06-14T14:00:00-04:00) and a title.",
        {"start": {"type": "string", "description": "Event start, ISO-8601 datetime."},
         "end": {"type": "string", "description": "Event end, ISO-8601 datetime."},
         "summary": {"type": "string", "description": "Event title."},
         "attendee_email": {"type": "string", "description": "Optional: email of one invitee."},
         "description": {"type": "string", "description": "Optional notes/agenda."},
         "tz": {"type": "string", "description": "Optional IANA tz if start/end have no offset."}},
        ["start", "end", "summary"]), _book),
    ("calendar_cancel", _schema(
        "calendar_cancel",
        "Cancel (delete) an event on the user's own Google Calendar. Needs the event_id from "
        "calendar_upcoming — call that first if you don't have it.",
        {"event_id": {"type": "string", "description": "The event_id to cancel."}},
        ["event_id"]), _cancel),
    ("contacts_add", _schema(
        "contacts_add",
        "Add a new contact to the user's own Google Contacts. Provide at least a name; email "
        "and phone are optional.",
        {"name": {"type": "string", "description": "Contact's full name."},
         "email": {"type": "string", "description": "Optional email address."},
         "phone": {"type": "string", "description": "Optional phone number."}},
        ["name"]), _contacts_add),
    ("contacts_search", _schema(
        "contacts_search",
        "Search the user's own Google Contacts by name or email. Use to look someone up before "
        "booking with them or to retrieve their email/phone.",
        {"q": {"type": "string", "description": "Search text (name or email)."}},
        ["q"]), _contacts_search),
    ("sheets_read", _schema(
        "sheets_read",
        "Read values from a range of a Google Sheet. You work with a sheet by its ID/link (you "
        "CANNOT search Drive by name — ask the user for the sheet link if you don't have the ID). "
        "Provide the spreadsheet_id and an A1 range (e.g. 'Sheet1!A1:C10').",
        {"spreadsheet_id": {"type": "string", "description": "The Google Sheet's id (from its URL)."},
         "range": {"type": "string", "description": "A1 range, e.g. 'Sheet1!A1:C10'."}},
        ["spreadsheet_id", "range"]), _sheets_read),
    ("sheets_append", _schema(
        "sheets_append",
        "Append one new row to a Google Sheet (log/record data). Work with the sheet by its "
        "ID/link (no Drive name-search). Provide spreadsheet_id, an A1 range naming the sheet "
        "(e.g. 'Sheet1!A1'), and values as a list of cell values for the single new row.",
        {"spreadsheet_id": {"type": "string", "description": "The Google Sheet's id (from its URL)."},
         "range": {"type": "string", "description": "A1 range, e.g. 'Sheet1!A1'."},
         "values": {"type": "array", "items": {"type": "string"},
                    "description": "Cell values for the one row to append, left to right."}},
        ["spreadsheet_id", "range", "values"]), _sheets_append),
    ("sheets_update", _schema(
        "sheets_update",
        "Overwrite the values in a SPECIFIC range of a Google Sheet (e.g. correct an existing "
        "row). You MUST give an explicit bounded range like 'Sheet1!A2:D2' — you cannot target a "
        "whole sheet or an open range, and the service will reject it if you try. Work by sheet "
        "ID/link (no Drive name-search). Confirm the exact range with the user before writing.",
        {"spreadsheet_id": {"type": "string", "description": "The Google Sheet's id (from its URL)."},
         "range": {"type": "string", "description": "Explicit bounded A1 range, e.g. 'Sheet1!A2:D2'."},
         "values": {"type": "array", "items": {"type": "string"},
                    "description": "New cell values for that range, left to right."}},
        ["spreadsheet_id", "range", "values"]), _sheets_update),
    ("sheets_clear", _schema(
        "sheets_clear",
        "Clear (empty) the values in a SPECIFIC range of a Google Sheet. You MUST give an explicit "
        "bounded range like 'Sheet1!A2:D2' — you cannot clear a whole sheet or an open range, and "
        "the service will reject it if you try. Confirm the exact range with the user first.",
        {"spreadsheet_id": {"type": "string", "description": "The Google Sheet's id (from its URL)."},
         "range": {"type": "string", "description": "Explicit bounded A1 range to clear, e.g. 'Sheet1!A2:D2'."}},
        ["spreadsheet_id", "range"]), _sheets_clear),
]


def register(ctx) -> None:
    for name, schema, handler in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="gws",
            schema=schema,
            handler=handler,
            check_fn=_available,
            requires_env=[ENV_URL, ENV_TOKEN],
            is_async=True,
            emoji="\U0001f4c5",
        )
