"""Deterministic outbound text sanitizer for DM channels.

Strips Markdown/HTML to plain text. Additionally, on the Facebook channel,
reduces URLs to their BARE DOMAIN (no scheme, no www, no path/query) because
Facebook Messenger silently drops outbound messages containing anything it
classifies as a clickable link from automated-pattern accounts. Proven by
controlled send tests judged on the recipient's screen:
  - https://miralefleur.com/collections/bouquet  (full URL)      -> DROPPED
  - miralefleur.com/collections/bouquet          (bare + path)   -> DROPPED
  - miralefleur.com                              (bare domain)   -> DELIVERED
Instagram delivers full https:// links fine, so this reduction is
FACEBOOK-ONLY (gated on the chatID channel marker). Fails safe: with no
chatID, URLs are left untouched.
"""

from __future__ import annotations

import re

TEXT_SEND_TOOLS = {"mcp_beeper_send_message"}

# Channel substring in the Beeper chatID that identifies the destination network.
_FACEBOOK_CHANNEL_MARKER = "local-facebook"

# A URL or bare-domain token. Captures scheme?, optional www., the domain, and
# any trailing path/query/fragment (which we DROP for Facebook).
_URL_RE = re.compile(
    r"\b(?:https?://)?(?:www\.)?"          # optional scheme + www (dropped)
    r"((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,})"  # group 1: domain
    r"(?:/[^\s]*)?",                        # optional path/query (dropped)
    re.IGNORECASE,
)


def _domain_only_urls(message: str) -> str:
    """Reduce every URL / domain-with-path token to its bare registrable domain.

    'https://miralefleur.com/collections/bouquet?x=1' -> 'miralefleur.com'
    'www.example.com/page'                            -> 'example.com'
    'miralefleur.com'                                 -> 'miralefleur.com' (unchanged)
    Plain prose with periods (e.g. 'Thanks. Bye.') is NOT matched because the
    domain pattern requires a valid TLD-like suffix with no surrounding space.
    """
    if not message:
        return message
    return _URL_RE.sub(lambda m: m.group(1), message)


def format_for_channel(message: str, chat_id: str | None = None) -> str:
    """Strip HTML + Markdown to plain text. If chat_id indicates the Facebook
    channel, also reduce URLs to bare domains (Facebook-only; IG keeps links).
    Returns input unchanged if empty / not a string.
    """
    if not message or not isinstance(message, str):
        return message

    # HTML -> plain.
    if re.search(r"<[a-z][a-z0-9]*\b[^>]*>", message, re.IGNORECASE):
        try:
            import html2text
            h = html2text.HTML2Text()
            h.body_width = 0
            h.ignore_links = False
            h.ignore_images = True
            message = h.handle(message).strip()
        except ImportError:
            message = re.sub(r"<[^>]+>", "", message)

    # Markdown -> plain.
    message = re.sub(r"\*\*([^*]+)\*\*", r"\1", message)
    message = re.sub(r"__([^_]+)__", r"\1", message)
    message = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", message)
    message = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"\1", message)
    message = re.sub(r"^\s{0,3}#{1,6}\s+", "", message, flags=re.MULTILINE)
    message = re.sub(r"^\s*[-*+]\s+", "• ", message, flags=re.MULTILINE)
    message = re.sub(r"```[a-z]*\n?", "", message)
    message = re.sub(r"`([^`]+)`", r"\1", message)
    message = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", message)
    message = _flatten_markdown_tables(message)
    message = re.sub(r"\n{3,}", "\n\n", message)

    # Facebook-only: reduce URLs to bare domains to avoid Messenger's link drop.
    if chat_id and _FACEBOOK_CHANNEL_MARKER in chat_id:
        message = _domain_only_urls(message)

    return message.strip()


def _flatten_markdown_tables(text: str) -> str:
    out = []
    for line in text.split("\n"):
        stripped = line.strip()
        if re.match(r"^\|?[\s:|-]+\|?$", stripped) and "-" in stripped:
            continue
        if stripped.startswith("|") or ("|" in stripped and stripped.count("|") >= 2):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            out.append(" — ".join(c for c in cells if c))
        else:
            out.append(line)
    return "\n".join(out)
