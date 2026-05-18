---
name: ph-business-hours-and-holidays
description: Answers questions about whether the business is currently open, what time they operate, and whether they're closed for holidays. Triggers on "open ba kayo?", "anong oras kayo?", "what time po kayo open", "are you open today?", "open ba kayo on Sunday?", "holiday ba kayo bukas?", "open kayo this weekend?". Use this skill to answer with awareness of the current PH time, operating hours, and PH public holidays. Do NOT use this for booking appointments — that's `ph-appointment-booking`.
license: Apache-2.0
metadata:
  author: alagad
  version: "1.0"
---

# PH Business Hours & Holidays

You answer "are you open?" questions with awareness of the current Philippine
time (UTC+8) and the country's public holidays.

## When to use this skill

Trigger phrases:
- "open ba kayo?", "open ba kayo ngayon?"
- "anong oras kayo open/closed?", "what time po"
- "open ba kayo on Sunday/Saturday?"
- "open ba kayo bukas?"
- "holiday ba kayo this {day}?"
- "schedule niyo po?"
- "operating hours?"

Do NOT trigger on:
- "I want to book/order/buy" → use the relevant intake skill
- "available ba kayo on {date} at {time}?" (asking about specific appointment
  slot) → that's `ph-appointment-booking`

## Procedure

### Step 1 — Read operating hours and closures

From `~/.hermes/USER.md`:

```markdown
## Operating Hours
- Mon-Fri: 9:00 AM - 6:00 PM
- Saturday: 10:00 AM - 4:00 PM
- Sunday: closed

## Holiday Schedule
- Closed on all regular holidays
- Open on special holidays (Black Saturday, Ninoy Aquino Day, etc.)
- Custom closures: Dec 24 half-day (until 12 PM), closed Dec 25-Jan 1
```

If `## Operating Hours` is missing, escalate to the tenant. Don't make up hours.

### Step 2 — Determine current Philippine time

Philippine Standard Time is UTC+8, no daylight saving. Get current PH time:

```bash
TZ=Asia/Manila date
```

### Step 3 — Determine status

Compute:
1. What day of the week is today (PH time)?
2. What are today's hours per USER.md?
3. Is today a holiday per `references/ph-public-holidays.md`?
4. If a holiday, does the tenant operate on this type of holiday?
5. Is the current PH time within operating hours?

Result is one of:
- **Open now** — currently within hours, not a holiday
- **Closed for the day** — past closing time, will reopen tomorrow (or later)
- **Not open today** — closed all day (Sunday for many SMBs, or a holiday)
- **About to close** — within 30 min of closing
- **About to open** — within 1 hour of opening

### Step 4 — Reply with the right template

Use `templates/hours-reply-taglish.md` — it has variants for each status.

Always include:
- The current status
- The next time the business opens (if not currently open)
- Hours for the rest of the week or the day they asked about

### Step 5 — Offer a path forward

Don't just answer "we're closed" and stop. Always end with one of:
- "Pa-message lang po and we'll reply pagkabukas namin"
- "Pwede po kayong mag-place ng order/booking ngayon, ipa-prepare namin agad
  pagkabukas"
- "May urgent ba? Subukan ko po kung pwede ma-arrange"

The agent is always-on; the business isn't. The reply should communicate that
distinction without leaving the customer feeling abandoned.

## Pitfalls

- **Don't forget time zones.** A customer messaging from overseas (OFWs, balikbayans)
  might assume PH time. Use PH time as the authoritative reference.
- **"Open ngayon?" at 11:59 PM.** Don't say "yes" if you close in 1 minute.
  Lead with the closing time.
- **Lunch breaks.** Some businesses close for lunch (12:00-1:00 PM). If
  USER.md lists this, honor it.
- **"24/7" businesses.** Some sari-sari and food businesses operate 24/7. The
  skill should handle this gracefully — never say "we're closed" if there's no
  closing time configured.
- **Brownouts and emergencies.** If the tenant has set a manual `closed_today: true`
  flag (for power outages, illness, etc.), respect it regardless of normal hours.

## Verification

After replying:
1. The customer knows whether they can transact now
2. The customer knows when they can next transact
3. The agent has offered a way forward (place order async, get notified, etc.)

## Reference files

- `templates/hours-reply-taglish.md` — Reply variants by status
- Shared: `../ph-appointment-booking/references/ph-public-holidays.md` — PH
  public holidays (single source of truth across the pack)
