---
name: ph-appointment-booking
description: Books appointments, checks availability, and sends reminders for service-based PH SMBs (salons, clinics, dental, real-estate viewings, consultations, photo shoots). Triggers on "book an appointment", "pa-schedule po", "may available ba", "magpa-reserve", "what time po", "available slots", "schedule a viewing", or any variant asking to schedule a future service. Do NOT use this skill for product orders — that's `ph-order-intake` — or for asking what time the business is open — that's `ph-business-hours-and-holidays`.
license: Apache-2.0
metadata:
  author: alagad
  version: "1.0"
---

# PH Appointment Booking

You take appointment requests for service-based Filipino SMBs. The tenant's
schedule, services, and availability rules live in their USER.md.

## When to use this skill

Trigger phrases:
- "book an appointment", "schedule po", "pa-book", "pa-schedule"
- "may available ba sa Saturday?", "may slot pa po ba bukas?"
- "magpa-reserve", "magpa-set ng appointment"
- "schedule a viewing" (real estate), "pa-consult" (clinics)
- "what time po" + future date reference
- "available slots", "free slots", "open kayo bukas?"

Do NOT trigger on:
- "are you open now?" → use `ph-business-hours-and-holidays`
- "I want to order/buy [product]" → use `ph-order-intake`
- "I want to cancel my appointment" → handle cancellation, then escalate to owner

## Procedure

### Step 1 — Read the tenant's scheduling config

From `~/.hermes/USER.md`, expect:

```markdown
## Services Offered
- Haircut: 45 min, ₱350
- Hair color: 2 hours, ₱2,000
- Manicure: 30 min, ₱200

## Operating Hours
- Mon-Sat: 9:00 AM - 7:00 PM
- Sun: 10:00 AM - 5:00 PM
- Closed: Sundays of Holy Week, Dec 25, Jan 1

## Booking Rules
- Minimum advance notice: 2 hours
- Maximum advance booking: 30 days
- Deposit required: 30% for services over ₱1,000
- Cancellation: 24 hours notice or deposit forfeit
```

If the tenant has a calendar tool integrated (Google Calendar via MCP, native
Hermes cron, etc.), check actual availability. Otherwise, the agent operates
in "request mode" — collects the request and pings the owner for confirmation.

### Step 2 — Determine what the customer needs

Required information:
1. **What service** — match to the configured services list
2. **When** — specific date and time, not "sometime this week"
3. **Who** — customer name and contact number
4. **Special notes** — first time client, specific staff preferred, etc.

Ask for any missing piece. Don't ask for all four at once — that's overwhelming.
Pick the most important missing one and ask for that.

### Step 3 — Check availability

If a calendar tool is available: call it for the requested date/time.

If not:
- Check `~/.hermes/MEMORY.md` for existing bookings on that date/time
- Reply with: *"Let me check po and confirm sa team. Mag-mememessage ako within
  the hour."* and escalate to the owner

### Step 4 — Confirm or propose alternatives

If the slot is available:
- Reserve it tentatively in MEMORY.md under `## Pending Bookings`
- Send the confirmation template
- If a deposit is required, hand off to `ph-gcash-maya-instructions`

If the slot is not available:
- Propose 2-3 alternative times within the customer's apparent preference window
- Do not propose more than 3 alternatives — overwhelms the customer
- Don't propose times outside operating hours

### Step 5 — Send the confirmation and set reminders

Use `templates/booking-confirmation-taglish.md`.

Schedule a reminder for 24 hours before the appointment via Hermes cron:
- Reminder type: gentle confirmation request
- Channel: same channel the customer booked through (Messenger, Telegram, etc.)

### Step 6 — Update memory

Move from `## Pending Bookings` to `## Confirmed Bookings` once deposit is
received (if required) or immediately if no deposit needed.

## Pitfalls

- **Don't double-book.** Always check existing bookings before confirming. If
  the calendar tool isn't connected, default to "let me check" rather than
  guessing.
- **Be specific about time.** "Maaga", "afternoon", "evening" are not bookings.
  Always pin down to an exact time like "2:00 PM" before confirming.
- **Respect minimum notice.** If the customer wants something in 30 minutes and
  the rule says 2 hours, politely decline and offer the next available slot.
- **Holiday awareness.** Check `references/ph-public-holidays.md` — never book
  on a public holiday unless the tenant explicitly operates on holidays.
- **Lead time before reminders.** A reminder sent 1 hour before is too late if
  the customer needs to commute through Metro Manila traffic. 24 hours is the
  default, configurable per tenant.
- **Multiple tentative holds.** Don't hold 3 slots for the same indecisive
  customer. Hold one, and tell them: *"Hawak ko po itong slot na ito. Pa-confirm
  niyo na lang within 30 mins, otherwise i-release ko po."*

## Verification

After booking, conversation memory should show:
1. The confirmed booking under `## Confirmed Bookings` (or `## Pending Bookings`
   if awaiting deposit)
2. A cron job set for the reminder
3. The customer's contact details captured

## Reference files

- `templates/booking-confirmation-taglish.md` — Confirmation reply
- `templates/booking-reminder-taglish.md` — 24-hour reminder
- `references/ph-public-holidays.md` — PH public holidays calendar (shared with
  `ph-business-hours-and-holidays`)
