"""HTTP client for the Alagad GWS proxy (Google Calendar / Contacts / Sheets).

The proxy exposes per-workspace, bearer-authed REST endpoints under
``$GWS_PROXY_URL/api/gws/*``. Identity rides ENTIRELY in the bearer
(``$GWS_PROXY_TOKEN`` — a per-workspace Fernet blob the proxy decrypts to recover
{ws, tenant}). The agent NEVER sends a workspace id; there is no such parameter on
any endpoint. So a prompt-injected agent processing untrusted inbound DMs can only
ever touch ITS OWN tenant's Google — it cannot name another workspace. Do not add a
workspace argument to any tool.

No Hermes imports here, so this stays trivially unit-testable. Raw proxy/Google
error bodies (which carry the account email + GCP project id) are NEVER surfaced —
only the clean messages below reach the agent.
"""

from __future__ import annotations

import os
from typing import Any

ENV_URL = "GWS_PROXY_URL"
ENV_TOKEN = "GWS_PROXY_TOKEN"
DEFAULT_TIMEOUT_S = 30.0

# Proxy error code (from its JSON {"error","action"}) -> message the model relays.
_ERROR_MESSAGES = {
    "not_connected": (
        "the Google account isn't connected yet — connect it from the portal, then try again"
    ),
    "auth_expired": (
        "the Google connection has expired and needs reconnecting "
        "(reconnect in the portal or contact the operator)"
    ),
    "scope_insufficient": (
        "the Google connection is missing a needed permission — "
        "reconnect and leave every box checked"
    ),
    "unknown_workspace": (
        "this workspace isn't recognized by the calendar service — contact the operator"
    ),
    "temporarily_unavailable": (
        "the calendar service is briefly unavailable — try again in a moment"
    ),
    "not_found": "that item wasn't found",
    "bad_request": "the request to the calendar service was invalid",
    "unauthorized": "the calendar service rejected this agent's credentials — contact the operator",
}


class GwsError(Exception):
    """Typed failure carrying a user-facing message + the upstream status/action."""

    def __init__(self, message: str, status: int | None = None, action: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.action = action


def gws_available() -> bool:
    """Cheap, network-free gate: both env vars present. A tenant without GWS wired
    simply doesn't see the tools (no error)."""
    return bool(os.getenv(ENV_URL, "").strip() and os.getenv(ENV_TOKEN, "").strip())


def _base_url() -> str:
    url = os.getenv(ENV_URL, "").strip().rstrip("/")
    if not url:
        raise GwsError(f"{ENV_URL} is not set")
    return url


def _token() -> str:
    tok = os.getenv(ENV_TOKEN, "").strip()
    if not tok:
        raise GwsError(f"{ENV_TOKEN} is not set")
    return tok


async def gws_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Call the proxy; return parsed JSON on success, else raise GwsError (clean msg)."""
    import httpx

    base = _base_url()
    headers = {"Authorization": f"Bearer {_token()}"}
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.request(
                method, f"{base}{path}", headers=headers, params=params, json=json
            )
    except httpx.TimeoutException as exc:
        raise GwsError(
            "the calendar service timed out — try again in a moment", status=504, action="retry"
        ) from exc
    except httpx.HTTPError as exc:  # connection refused, DNS, etc.
        raise GwsError("couldn't reach the calendar service", status=None, action="retry") from exc

    if 200 <= resp.status_code < 300:
        try:
            return resp.json()
        except ValueError:
            return {}

    code: str | None = None
    action: str | None = None
    need: str | None = None
    try:
        body = resp.json()
        if isinstance(body, dict):
            code = body.get("error")
            action = body.get("action")
            need = body.get("need")
    except ValueError:
        pass

    msg = _ERROR_MESSAGES.get(code or "") or (
        f"the calendar service returned an error (HTTP {resp.status_code})"
    )
    if code == "scope_insufficient" and need:
        msg = f"{msg} (missing scope: {need})"
    raise GwsError(msg, status=resp.status_code, action=action)
