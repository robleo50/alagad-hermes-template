# Alagad Hermes Template

**Target:** CT 9000 `alagad-template` on NEST (Proxmox), Ubuntu 24.04 + Hermes Agent (0.14.x)
**Purpose:** Authoritative source for the Alagad golden template — the image every tenant clones from
**Maintained by:** Alagad (PAL Tech LLC)

> **Status (2026-05-31):** Refreshed for the middleware era. The golden image is
> now **CT 9000** (formerly "VM 100"), and tenant agents have a three-part web
> capability — **search** (CT 9300), **fetch** (CT 9301), and **answer**
> (CT 9302). This repo is being reconciled with the post-capability-bake CT 9000;
> the first middleware-era asset committed here is the `plugins/web-answer/`
> Hermes plugin. Some older sections below still describe the v1 (VM 100) image
> and are being updated.

This repo holds what has to be on the golden image before it becomes the
template tenants spin up. Tracked here so changes are versioned, reviewable, and
reproducible — instead of living only on a snapshot.

## What's in here

```
alagad-hermes-template/
├── README.md                  This file
├── VERSION                    Template version (semver)
├── install.sh                 Run on the golden image to apply everything in this repo
├── config/
│   ├── config.yaml            Hermes config — plugins, tools, model provider
│   ├── USER.md.template       Tenant placeholder USER.md (filled at onboarding)
│   └── MEMORY.md.template     Empty MEMORY.md starter
├── plugins/
│   └── web-answer/            web_answer tool -> Alagad Answer adapter (CT 9302)
└── skills/                    Alagad PH Essentials — 6 Filipino SMB skills
    ├── ph-payment-confirmation/
    ├── ph-gcash-maya-instructions/
    ├── ph-appointment-booking/
    ├── ph-order-intake/
    ├── ph-delivery-coordination/
    └── ph-business-hours-and-holidays/
```

## Web middleware integration (search / fetch / answer)

Tenant agents reach three multi-tenant web services, each behind a per-tenant
token carried in a URL path and each safety-filtered + audited:

| Hermes tool | Service (CT) | Endpoint | Wiring |
|---|---|---|---|
| `web_search` | search, CT 9300 | `192.168.8.240:8500/t/<token>` | `SEARXNG_URL` (baked, built-in tool) |
| `web_extract` | fetch, CT 9301 | `192.168.8.241:8600/t/<token>` | `TAVILY_BASE_URL` (baked, built-in tool) |
| `web_answer` | answer, CT 9302 | `192.168.8.242:8700/t/<token>` | `ALAGAD_ANSWER_URL` (this repo's `plugins/web-answer/`) |

`web_search` and `web_extract` are built-in Hermes tools selected by
`web.search_backend` / `web.extract_backend` in `config.yaml`. `web_answer` is
not a built-in — it ships as the **`plugins/web-answer/`** plugin in this repo
(see its README), registered into the `web` toolset and gated on
`ALAGAD_ANSWER_URL`.

Two bake prerequisites for `web_answer` on CT 9000 (tracked, not yet applied):
1. an `answer.conf` gateway drop-in carrying `ALAGAD_ANSWER_URL` (which
   `spin-workspace.py` token-substitutes per tenant), and
2. **tenant-fw v3** — the egress allowlist `/etc/nftables.d/alagad-tenant.nft`
   must permit `192.168.8.242:8700` (see `plugins/web-answer/README.md`).

## Quick install on the golden image

```bash
git clone https://github.com/robleo50/alagad-hermes-template.git
cd alagad-hermes-template
./install.sh
```

The script copies the PH skills into `~/.hermes/skills/`, drops `USER.md` /
`MEMORY.md` starters into `~/.hermes/`, writes `~/.hermes/config.yaml`, and runs
verification (`hermes doctor`, `hermes plugins list`, `hermes skills list`).
Bundling the `web-answer` plugin into the golden image's Hermes tree is done at
bake time (see the plugin README) — wiring it into `install.sh` is a follow-up.

After it succeeds, run the standard template-prep sequence (SSH host keys,
machine-id, cloud-init clean, bash history, apt cache) and convert to a Proxmox
template.

## Skill pack overview

| Skill | What it does |
|---|---|
| `ph-payment-confirmation` | Recognizes GCash, Maya, and bank transfer payment proofs and confirms them |
| `ph-gcash-maya-instructions` | Sends payment instructions when a customer asks how to pay |
| `ph-appointment-booking` | Books appointments, checks availability, sends reminders |
| `ph-order-intake` | Takes orders, computes totals, asks for the right details |
| `ph-delivery-coordination` | Handles delivery questions: address, courier, ETA, fees |
| `ph-business-hours-and-holidays` | Answers "are you open?" with awareness of PH public holidays |

Each skill follows the [agentskills.io](https://agentskills.io) open standard.

## Versioning

The `VERSION` file follows semver. Bump when:
- **Major** — breaking config schema change (tenants must re-onboard)
- **Minor** — new skill added or new plugin enabled
- **Patch** — wording, bug fixes, template tweaks

## Support

- Docs: https://alagad.net/docs
- Issues: file in this repo
