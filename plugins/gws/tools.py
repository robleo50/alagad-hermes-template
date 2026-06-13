"""GWS tools — Google Calendar / Contacts / Sheets via the Alagad GWS proxy.

Schemas use the bare ``{"name","description","parameters"}`` form the registry
expects (matching ``WEB_ANSWER_SCHEMA`` / ``WEB_SEARCH_SCHEMA``), NOT the OpenAI
``{"type":"function",...}`` wrapper. Descriptions are written for gemma4-26b:
each says WHEN to use the tool and what each param is, so the model picks the
right tool and fills params correctly. Every handler returns a readable string
and never raises into the agent loop.

NOTE: no tool takes a workspace id — identity is in the bearer (see client.py).
"""

from __future__ import annotations

from typing import Any

from .client import gws_request


def _guard(label: str):
    """Wrap a handler so any failure becomes a clean ``<label>: ...`` string."""
    from .client import GwsError

    def deco(fn):
        async def wrapped(args: dict[str, Any], **_kw: Any) -> str:
            try:
                return await fn(args, **_kw)
            except GwsError as exc:
                return f"{label}: {exc.message}"
            except Exception as exc:  # noqa: BLE001 — never crash the loop
                return f"{label}: unexpected failure ({exc})"

        return wrapped

    return deco


# ---------------------------------------------------------------------------
# Calendar (the appointment-setting loop)
# ---------------------------------------------------------------------------

CALENDAR_UPCOMING_SCHEMA = {
    "name": "calendar_upcoming",
    "description": (
        "List upcoming events on the user's own Google Calendar. Use this when the "
        "user asks what's on their calendar / schedule / agenda, whether they're free, "
        "or to look up an event before changing it. Returns each event's title, start "
        "and end time, and an event_id (needed to cancel)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "How many days ahead to list (default 7, max 60).",
            }
        },
        "required": [],
    },
}

CALENDAR_SLOTS_SCHEMA = {
    "name": "calendar_slots",
    "description": (
        "Find FREE time slots on the user's Google Calendar for a specific date. Use "
        "this when scheduling a meeting and you need to offer open times. Returns a list "
        "of available start/end times of the requested length."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "The date to check, as YYYY-MM-DD."},
            "duration_min": {
                "type": "integer",
                "description": "Length of the slot in minutes (default 30).",
            },
            "tz": {
                "type": "string",
                "description": "Optional IANA timezone (e.g. America/New_York). Defaults to the agent's configured timezone.",
            },
        },
        "required": ["date"],
    },
}

CALENDAR_BOOK_SCHEMA = {
    "name": "calendar_book",
    "description": (
        "Create (book) an event on the user's Google Calendar. Use this only once a "
        "specific time is agreed. Provide ISO-8601 start and end datetimes (include the "
        "timezone offset, e.g. 2026-06-14T14:00:00-04:00, OR pass a plain local time and "
        "set tz). Optionally invite one attendee by email."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "start": {"type": "string", "description": "Event start, ISO-8601 datetime."},
            "end": {"type": "string", "description": "Event end, ISO-8601 datetime."},
            "summary": {"type": "string", "description": "Event title."},
            "attendee_email": {
                "type": "string",
                "description": "Optional: email of one person to invite.",
            },
            "description": {"type": "string", "description": "Optional event notes/agenda."},
            "tz": {
                "type": "string",
                "description": "Optional IANA timezone, used when start/end have no offset.",
            },
        },
        "required": ["start", "end", "summary"],
    },
}

CALENDAR_CANCEL_SCHEMA = {
    "name": "calendar_cancel",
    "description": (
        "Cancel (delete) an event on the user's Google Calendar. You need the event_id, "
        "which comes from calendar_upcoming — call that first if you don't have it."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "The event_id to cancel."}
        },
        "required": ["event_id"],
    },
}


@_guard("calendar_upcoming error")
async def _h_upcoming(args: dict[str, Any], **_kw: Any) -> str:
    days = args.get("days") or 7
    data = await gws_request("GET", "/api/gws/calendar/upcoming", params={"days": days})
    events = data.get("events") or []
    if not events:
        return f"No events on the calendar in the next {days} days."
    lines = [f"Upcoming events (next {days} days):"]
    for e in events:
        title = e.get("summary") or "(no title)"
        start = e.get("start") or "?"
        end = e.get("end") or "?"
        lines.append(f"- {title}: {start} -> {end}  (event_id: {e.get('event_id')})")
    return "\n".join(lines)


@_guard("calendar_slots error")
async def _h_slots(args: dict[str, Any], **_kw: Any) -> str:
    date = (args.get("date") or "").strip()
    if not date:
        return "calendar_slots error: 'date' (YYYY-MM-DD) is required."
    params: dict[str, Any] = {"date": date, "duration_min": args.get("duration_min") or 30}
    if args.get("tz"):
        params["tz"] = args["tz"]
    data = await gws_request("GET", "/api/gws/calendar/slots", params=params)
    slots = data.get("slots") or []
    if not slots:
        return f"No free {params['duration_min']}-minute slots on {date}."
    lines = [f"Free {params['duration_min']}-min slots on {date}:"]
    for s in slots:
        lines.append(f"- {s.get('start')} -> {s.get('end')}")
    return "\n".join(lines)


@_guard("calendar_book error")
async def _h_book(args: dict[str, Any], **_kw: Any) -> str:
    for req in ("start", "end", "summary"):
        if not (args.get(req) or "").strip():
            return f"calendar_book error: '{req}' is required."
    body = {"start": args["start"], "end": args["end"], "summary": args["summary"]}
    for opt in ("attendee_email", "description", "tz"):
        if args.get(opt):
            body[opt] = args[opt]
    data = await gws_request("POST", "/api/gws/calendar/book", json=body)
    return (
        f"Booked '{args['summary']}' from {data.get('start')} to {data.get('end')}. "
        f"(event_id: {data.get('event_id')})"
    )


@_guard("calendar_cancel error")
async def _h_cancel(args: dict[str, Any], **_kw: Any) -> str:
    event_id = (args.get("event_id") or "").strip()
    if not event_id:
        return "calendar_cancel error: 'event_id' is required (get it from calendar_upcoming)."
    await gws_request("DELETE", "/api/gws/calendar/cancel", json={"event_id": event_id})
    return f"Cancelled the event (event_id: {event_id})."


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

CONTACTS_ADD_SCHEMA = {
    "name": "contacts_add",
    "description": (
        "Add a new contact to the user's Google Contacts. Use when the user wants to save "
        "someone's details. Provide at least a name; email and phone are optional."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Contact's full name."},
            "email": {"type": "string", "description": "Optional email address."},
            "phone": {"type": "string", "description": "Optional phone number."},
        },
        "required": ["name"],
    },
}

CONTACTS_SEARCH_SCHEMA = {
    "name": "contacts_search",
    "description": (
        "Search the user's Google Contacts by name or email. Use to look someone up "
        "before booking with them or to retrieve their email/phone."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "q": {"type": "string", "description": "Search text (name or email)."}
        },
        "required": ["q"],
    },
}


@_guard("contacts_add error")
async def _h_contacts_add(args: dict[str, Any], **_kw: Any) -> str:
    name = (args.get("name") or "").strip()
    if not name:
        return "contacts_add error: 'name' is required."
    body = {"name": name}
    for opt in ("email", "phone"):
        if args.get(opt):
            body[opt] = args[opt]
    await gws_request("POST", "/api/gws/contacts/add", json=body)
    return f"Added contact '{name}'."


@_guard("contacts_search error")
async def _h_contacts_search(args: dict[str, Any], **_kw: Any) -> str:
    q = (args.get("q") or "").strip()
    if not q:
        return "contacts_search error: 'q' is required."
    data = await gws_request("GET", "/api/gws/contacts/search", params={"q": q})
    results = data.get("results") or []
    if not results:
        return f"No contacts matched '{q}'."
    lines = [f"Contacts matching '{q}':"]
    for r in results:
        emails = ", ".join(r.get("emails") or []) or "-"
        phones = ", ".join(r.get("phones") or []) or "-"
        lines.append(f"- {r.get('name') or '(no name)'} | email: {emails} | phone: {phones}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sheets
# ---------------------------------------------------------------------------

SHEETS_APPEND_SCHEMA = {
    "name": "sheets_append",
    "description": (
        "Append one row to a Google Sheet. Use to log/record a row of data. Provide the "
        "spreadsheet_id, an A1 range naming the sheet/table (e.g. 'Sheet1!A1'), and values "
        "as a list of cell values for the single new row."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "spreadsheet_id": {"type": "string", "description": "The Google Sheet's id."},
            "range": {"type": "string", "description": "A1 range, e.g. 'Sheet1!A1'."},
            "values": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Cell values for the one row to append, left to right.",
            },
        },
        "required": ["spreadsheet_id", "range", "values"],
    },
}

SHEETS_READ_SCHEMA = {
    "name": "sheets_read",
    "description": (
        "Read values from a range of a Google Sheet. Provide the spreadsheet_id and an A1 "
        "range (e.g. 'Sheet1!A1:C10'). Returns the rows in that range."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "spreadsheet_id": {"type": "string", "description": "The Google Sheet's id."},
            "range": {"type": "string", "description": "A1 range, e.g. 'Sheet1!A1:C10'."},
        },
        "required": ["spreadsheet_id", "range"],
    },
}


@_guard("sheets_append error")
async def _h_sheets_append(args: dict[str, Any], **_kw: Any) -> str:
    sid = (args.get("spreadsheet_id") or "").strip()
    rng = (args.get("range") or "").strip()
    values = args.get("values")
    if not sid or not rng or values is None:
        return "sheets_append error: 'spreadsheet_id', 'range', and 'values' are required."
    if not isinstance(values, list):
        return "sheets_append error: 'values' must be a list of cell values."
    data = await gws_request(
        "POST",
        "/api/gws/sheets/append",
        json={"spreadsheet_id": sid, "range": rng, "values": [values]},
    )
    return f"Appended a row. Updated range: {data.get('updated_range')}."


@_guard("sheets_read error")
async def _h_sheets_read(args: dict[str, Any], **_kw: Any) -> str:
    sid = (args.get("spreadsheet_id") or "").strip()
    rng = (args.get("range") or "").strip()
    if not sid or not rng:
        return "sheets_read error: 'spreadsheet_id' and 'range' are required."
    data = await gws_request(
        "GET", "/api/gws/sheets/read", params={"spreadsheet_id": sid, "range": rng}
    )
    rows = data.get("values") or []
    if not rows:
        return f"No values in {rng}."
    lines = [f"Values in {data.get('range') or rng}:"]
    for row in rows:
        lines.append("  " + " | ".join(str(c) for c in row))
    return "\n".join(lines)


# (name, schema, handler) — consumed by __init__.register()
TOOLS = [
    ("calendar_upcoming", CALENDAR_UPCOMING_SCHEMA, _h_upcoming),
    ("calendar_slots", CALENDAR_SLOTS_SCHEMA, _h_slots),
    ("calendar_book", CALENDAR_BOOK_SCHEMA, _h_book),
    ("calendar_cancel", CALENDAR_CANCEL_SCHEMA, _h_cancel),
    ("contacts_add", CONTACTS_ADD_SCHEMA, _h_contacts_add),
    ("contacts_search", CONTACTS_SEARCH_SCHEMA, _h_contacts_search),
    ("sheets_append", SHEETS_APPEND_SCHEMA, _h_sheets_append),
    ("sheets_read", SHEETS_READ_SCHEMA, _h_sheets_read),
]
