# Facebook URL → bare-domain patch (`output-sanitize`, Hermes v0.14.0)

Channel-aware patch to the bundled `output-sanitize` plugin. It is the same
`pre_tool_call` hook that strips Markdown/HTML from outbound DM text; this patch
adds **one** behavior: on the **Facebook channel**, every URL in an outbound
message is reduced to its **bare registrable domain** (scheme, `www.`, and
path/query all stripped).

- Deployed live to CT 5000 (Richard's agent) on **2026-06-01** (Session N).
- Files: `format.py`, `__init__.py`. (`test_format.py` and `plugin.yaml` are
  unchanged from the base `output-sanitize` plugin and are not included here.)

## Root cause

Facebook Messenger **silently drops outbound messages from the agent's account
that contain anything it classifies as a clickable link.** The drop happens
*after* Beeper hands the message to Meta, so Beeper logs the message as "sent
successfully" — the failure is invisible in logs. **Only the recipient's screen
is authoritative.**

Scope of the problem:
- **Outbound only.** Inbound links (customer → agent, e.g. an Amazon cart URL)
  arrive fully formed.
- **Facebook only.** The same agent sending the same full `https://` link over
  **Instagram** delivers fine. So the reduction is gated to the Facebook channel
  and Instagram keeps full clickable links.

## Evidence (controlled send tests, judged on the recipient's live Messenger screen)

| Outbound content | Result |
|---|---|
| `https://miralefleur.com/collections/bouquet` (full URL) | **DROPPED** |
| `miralefleur.com/collections/bouquet` (bare domain + path) — *Test G* | **DROPPED** |
| `miralefleur.com` (bare domain, no path) — *Test E* | **DELIVERED** |
| Inbound link (customer → agent) | arrives fully formed (unaffected) |
| Full `https://` link over Instagram (same agent) | delivered fine (unaffected) |

**Live Session-N confirmation (2026-06-01):** after deploy, the agent replied
to the Facebook chat with `miralefleur.com` (bare domain); the message
**arrived on the recipient's screen** and the stored reply showed the URL
reduced to the bare domain with no scheme/path.

## Decision: domain-only

`www.` + scheme + **path** are all stripped. Test G proved that a bare domain
*with a path* is still dropped — only the bare domain with **no path** (Test E)
is proven to deliver. So the reducer cannot preserve paths; it collapses every
URL to the bare registrable domain.

## Design

- **Facebook-gated.** Reduction only runs when the Beeper `chatID` contains the
  channel marker `local-facebook`. Instagram / other channels keep full links.
- **Fails open / safe.** If `chatID` is absent, URLs are left untouched. Any
  exception in the hook is swallowed and the original text is sent — formatting
  must never cost delivery.
- **Rewrite-only.** The hook never blocks a send; it mutates `args["text"]` in
  place (the `output-sanitize` no-copy mechanism). Returns `None`.
- Plain prose with periods (`Thanks. Bye.`) is not matched — the URL regex
  requires a TLD-like suffix with no surrounding whitespace.

## Known limitation

Because paths are stripped, **per-product deep links collapse to the same bare
domain.** If the agent emits ten distinct product URLs
(`.../products/love-bomb`, `.../products/lovesick`, …) they all become
`miralefleur.com`, so the customer sees ten identical "links." This is inherent
to the domain-only decision (Meta drops path-bearing links regardless), **not** a
sanitizer bug. The right fix is upstream (agent prompt): on Facebook, do not
present per-item deep links — give product names plus the single collection
domain, or describe items without individual links. Tracked as a follow-up.

## Re-apply after Hermes upgrades

This patch lives in the bundled plugin tree, which a Hermes upgrade can
overwrite. After any upgrade:

1. Re-copy `format.py` and `__init__.py` into
   `plugins/output-sanitize/`, clear `__pycache__`, restart the gateway
   (`hermes gateway run --replace`, single instance).
2. **Re-run the canary:** `python3 test_format.py` in the plugin dir must print
   `ALL TESTS PASS`. The mutation-propagation test is the canary for the
   no-copy arg-rewrite mechanism — if a future Hermes copies tool args before
   invoking hooks, that test fails and the rewrite silently stops (fails open,
   no crash; full URLs would start sending again).
