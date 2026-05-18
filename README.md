# Alagad Hermes Template

**Target:** VM 100 on NEST (Proxmox), Ubuntu 24.04 + Hermes Agent
**Purpose:** Authoritative source for the Alagad golden template — the VM image every tenant clones from
**Maintained by:** Alagad (PAL Tech LLC)

This repo holds everything that has to be on VM 100 before it becomes the Convoy template tenants spin up. Tracked here so changes are versioned, reviewable, and reproducible — instead of living only on a snapshot.

## What's in here

```
alagad-hermes-template/
├── README.md                  This file
├── VERSION                    Template version (semver)
├── install.sh                 Run on VM 100 to apply everything in this repo
├── config/
│   ├── config.yaml            Hermes config — plugins, tools, model provider
│   ├── USER.md.template       Tenant placeholder USER.md (filled at onboarding)
│   └── MEMORY.md.template     Empty MEMORY.md starter
└── skills/                    Alagad PH Essentials — 6 Filipino SMB skills
    ├── ph-payment-confirmation/
    ├── ph-gcash-maya-instructions/
    ├── ph-appointment-booking/
    ├── ph-order-intake/
    ├── ph-delivery-coordination/
    └── ph-business-hours-and-holidays/
```

## Quick install on VM 100

```bash
git clone https://github.com/robleo50/alagad-hermes-template.git
cd alagad-hermes-template
./install.sh
```

The script:
1. Enables 3 bundled Hermes plugins (`disk-cleanup`, `hermes-achievements`, `image_gen`)
2. Copies the 6 PH skills into `~/.hermes/skills/`
3. Drops `USER.md` and `MEMORY.md` starter files into `~/.hermes/`
4. Writes `~/.hermes/config.yaml` with the curated toolset config
5. Runs verification (`hermes doctor`, `hermes plugins list`, `hermes skills list`)

After it succeeds, run the standard template-prep sequence (SSH host keys, machine-id, cloud-init clean, bash history, apt cache) and convert to a Proxmox template.

## What this deliberately excludes (v1)

- **External services** — no Langfuse, no Honcho server, no mem0. Defer to v1.1 when hosted instances exist.
- **42-evey hermes-plugins** — community plugin set, useful but adds support burden.
- **SkillClaw auto-evolution** — privacy concerns about cross-tenant skill leakage.
- **MCP servers** — none in v1. Tenants install what they need.
- **Tenant-specific tokens** — Telegram bots, Messenger pages, Tavily keys are per-tenant onboarding, not template settings.

## Skill pack overview

| Skill | What it does |
|---|---|
| `ph-payment-confirmation` | Recognizes GCash, Maya, and bank transfer payment proofs and confirms them |
| `ph-gcash-maya-instructions` | Sends payment instructions when a customer asks how to pay |
| `ph-appointment-booking` | Books appointments, checks availability, sends reminders |
| `ph-order-intake` | Takes orders, computes totals, asks for the right details |
| `ph-delivery-coordination` | Handles delivery questions: address, courier, ETA, fees |
| `ph-business-hours-and-holidays` | Answers "are you open?" with awareness of PH public holidays |

Each skill follows the [agentskills.io](https://agentskills.io) open standard — portable to Claude Code, OpenAI Codex, or any agent runtime that supports the spec.

## Versioning

The `VERSION` file follows semver. Bump when:
- **Major** — breaking config schema change (tenants must re-onboard)
- **Minor** — new skill added or new plugin enabled
- **Patch** — wording, bug fixes, template tweaks

## Support

- Docs: https://alagad.net/docs
- Issues: file in this repo
