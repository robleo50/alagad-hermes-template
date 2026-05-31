"""HTTP client for the Alagad Answer adapter (Perplexica-backed synthesis).

The adapter exposes a per-tenant, tokened endpoint::

    POST {ALAGAD_ANSWER_URL}/answer
    body: {"query": str, "focus_mode": str?}
    200:  {"answer", "sources", "focus_mode", "cached", "fetch_ms", "source_count"}

``ALAGAD_ANSWER_URL`` carries the token in the path
(``http://192.168.8.242:8700/t/<token>``), exactly mirroring how
``SEARXNG_URL`` / ``TAVILY_BASE_URL`` are configured for the search/extract
tools. This module deliberately holds no Hermes imports so it stays trivially
unit-testable.
"""

from __future__ import annotations

import os
from typing import Any, Dict

ENV_URL = "ALAGAD_ANSWER_URL"

# Perplexica synthesis typically 20-40s; 150s headroom stays above the adapter
# perplexica_timeout_s=120s so a slow-but-successful synthesis is not cut off as
# a client-side timeout.
DEFAULT_TIMEOUT_S = 150.0

# Adapter error contract -> clean, user-facing tool messages. Keeps stack
# traces out of the agent's tool result.
_STATUS_MESSAGES = {
    400: "the answer service rejected the request (missing query or disallowed focus mode)",
    401: "answer service authentication failed (token invalid or revoked)",
    429: "answer service rate or quota limit reached - try again later",
    451: "this question was blocked by the answer service safety filter",
    502: "answer synthesis backend error",
    503: "answer service unavailable (budget cap reached or synthesis backend down)",
    504: "answer service timed out",
}


class AnswerError(Exception):
    """Typed failure carrying a user-facing message and the upstream status."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def answer_base_url() -> str:
    """Return the configured adapter base URL (no trailing slash).

    Raises :class:`AnswerError` when ``ALAGAD_ANSWER_URL`` is unset — the tool
    handler turns this into a clean message; the registry ``check_fn`` /
    ``requires_env`` gate normally prevents reaching here when unset.
    """
    url = os.getenv(ENV_URL, "").strip().rstrip("/")
    if not url:
        raise AnswerError(f"{ENV_URL} is not set", status=None)
    return url


def _extract_detail(resp: Any) -> str:
    """Best-effort pull of the adapter's ``detail.message`` for context."""
    try:
        body = resp.json()
    except Exception:
        return ""
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, dict):
        return detail.get("message") or detail.get("error") or ""
    if isinstance(detail, str):
        return detail
    return ""


async def request_answer(
    query: str,
    focus_mode: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> Dict[str, Any]:
    """POST a question to the answer adapter and return the parsed 200 body.

    Network failures and non-200 responses are mapped to :class:`AnswerError`
    with a clean message; the caller never sees an httpx exception.
    """
    import httpx

    base = answer_base_url()
    payload: Dict[str, Any] = {"query": query}
    if focus_mode:
        payload["focus_mode"] = focus_mode

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(f"{base}/answer", json=payload)
    except httpx.TimeoutException:
        raise AnswerError("answer service timed out (synthesis took too long)", status=504)
    except httpx.HTTPError as exc:  # connection refused, DNS, etc.
        raise AnswerError(f"could not reach answer service: {exc}", status=None)

    if resp.status_code == 200:
        return resp.json()

    msg = _STATUS_MESSAGES.get(resp.status_code, f"answer service error (HTTP {resp.status_code})")
    detail = _extract_detail(resp)
    if detail:
        msg = f"{msg}: {detail}"
    raise AnswerError(msg, status=resp.status_code)
