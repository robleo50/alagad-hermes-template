"""Alagad ``gws`` plugin — Google Calendar/Contacts/Sheets tools via the GWS proxy.

Registers 8 tools into the ``gws`` toolset; each calls the per-workspace Alagad GWS
proxy at ``$GWS_PROXY_URL`` with the per-workspace bearer ``$GWS_PROXY_TOKEN``. Gated
on both env vars (``check_fn`` + ``requires_env``), so a tenant without GWS wired
simply doesn't see the tools (no error). Mirrors ``plugins/web-answer/__init__.py``.

SECURITY: no tool exposes a workspace id — identity is the bearer (see client.py).
"""

from __future__ import annotations

from .client import ENV_TOKEN, ENV_URL, gws_available
from .tools import TOOLS


def register(ctx) -> None:
    """Register all GWS tools. Called once by the plugin loader."""
    for name, schema, handler in TOOLS:
        ctx.register_tool(
            name=name,
            toolset="gws",
            schema=schema,
            handler=handler,
            check_fn=gws_available,
            requires_env=[ENV_URL, ENV_TOKEN],
            is_async=True,
            emoji="\U0001f4c5",  # 📅
        )
