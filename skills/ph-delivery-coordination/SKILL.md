---
name: ph-delivery-coordination
description: Coordinates delivery for an active order — captures the address, computes delivery fee based on tenant's coverage zones, picks the right courier (Lalamove, Grab Express, Borzo, in-house rider), and gives the customer an ETA. Triggers on "deliver po", "magkano shipping", "may delivery ba kayo", "address ko po", "saan magaling kayo", "Lalamove", "Grab", "delivery fee", or any address/logistics question on an active order. Do NOT use this skill if there is no active order — that's `ph-order-intake` first.
license: Apache-2.0
metadata:
  author: alagad
  version: "1.0"
---

# PH Delivery Coordination

You handle the address capture, fee computation, and courier coordination for an
active order. Each tenant configures their delivery zones, couriers, and fee
schedule in USER.md.

## When to use this skill

Trigger phrases (assumes there is an active order in MEMORY.md):
- "deliver po", "may delivery ba?"
- "magkano shipping fee?", "magkano delivery?"
- "address ko po:", "dito ako sa..."
- "saan kayo nag-dedeliver?", "covered ba ang {area}?"
- "Lalamove", "Grab Express", "Borzo" — customer naming a specific courier
- "may rider ba kayo?"
- "ETA?", "kelan dadating?"

Do NOT trigger on:
- No active order in MEMORY.md → run `ph-order-intake` first
- "I want to track my order" → escalate to courier tracking, agent can't see this
- "Saan po address niyo?" (asking for *merchant's* address, for pickup) → answer
  from USER.md directly, no skill needed

## Procedure

### Step 1 — Read the tenant's delivery configuration

From USER.md:

```markdown
## Delivery Configuration

### Coverage zones
- Zone 1 (₱100 fee): Makati, BGC, Ortigas, Mandaluyong
- Zone 2 (₱150 fee): QC (south), Pasig, San Juan, Manila
- Zone 3 (₱250 fee): QC (north), Marikina, Las Piñas, Parañaque, Pasay
- Outside Metro Manila: Lalamove/Grab cost shouldered by customer

### Couriers
- Default: Lalamove (motorcycle for orders < 5kg)
- Bulky/fragile: Grab Express (car/van)
- Same-day Metro Manila: Borzo
- Provincial: J&T Express, LBC, Flash Express

### Operating zones for in-house rider (if any)
- In-house only: Makati, BGC (within ₱150 fee)

### Cutoff times
- Same-day delivery cutoff: 2:00 PM
- Next-day: order before 6:00 PM
```

### Step 2 — Capture the address

Required components for PH addresses:
1. **Unit/floor/building** if applicable
2. **Street number and name**
3. **Barangay** (very common in PH addresses, helps couriers)
4. **City/Municipality**
5. **Landmark** — Filipino customers often give landmarks ("near 7-Eleven", "tapat
   ng simbahan"). These are useful for the courier, even if not strictly required.

Ask in one message:
*"Para sa delivery po, pakishare ng full address: unit/building, street, barangay,
city, plus landmark kung meron. Salamat!"*

### Step 3 — Determine zone and fee

Match the city/barangay against configured zones. If unclear:
- Ask: *"Anong city po ito specifically?"* (some places straddle borders)
- Default to the higher-fee zone if ambiguous, and explain

If outside coverage:
- Offer Lalamove/Grab "ka-share fare" (customer pays courier fee)
- Quote a rough estimate based on distance
- Don't book the courier yet — let the customer decide

### Step 4 — Determine timing

Cutoff awareness:
- Order placed before cutoff for same-day → offer same-day
- Past cutoff → offer next-day, explain why
- For special-occasion orders (Valentine's, Mother's Day), book in advance

Ask: *"Anong time po pwede mag-receive? Or anytime today/bukas okay?"*

For surprise gifts: confirm the recipient will be at the address. The agent
should suggest: *"Para sigurado may makakatanggap, baka pwede magtanong muna sa
recipient kung nandun siya?"*

### Step 5 — Compute final total and confirm

Update the order total with delivery fee. Send the updated total to the customer:

```
Updated po ang total:
Subtotal: ₱{subtotal}
Delivery fee ({zone}): ₱{delivery_fee}
Total: ₱{new_total}

Address: {captured_address}
Delivery time: {eta_window}
```

Then continue to payment via `ph-gcash-maya-instructions`.

### Step 6 — After payment, book the courier

Once payment is confirmed (`ph-payment-confirmation`), book the courier or
dispatch the in-house rider. If this is a manual step for the tenant:
- Add to MEMORY.md under `## Pending Dispatch`
- Notify the owner via configured escalation channel
- Reply to the customer: *"Ipapasundo ko na po sa rider, mag-uupdate ako once
  na-book na ang courier."*

If the courier is bookable via MCP/API, do the booking and share the tracking
link/details with the customer.

## Pitfalls

- **Don't quote provincial delivery as flat-fee.** Provincial is courier-dependent
  and usually charged at courier cost. Don't promise a flat ₱150 to Cebu — that's
  going to lose money fast.
- **Address formatting.** Couriers in PH prefer the format: `Unit/Bldg, Street,
  Barangay, City`. Don't reorder this — it confuses the rider's GPS.
- **Floods and weather.** During typhoons or heavy rain, couriers may suspend
  service. Don't promise an ETA you can't keep. The skill should check
  `~/.hermes/MEMORY.md` for a `weather_advisory_active: true` flag (the tenant or
  owner can set this manually) and adjust messaging.
- **Sunday/holiday courier availability.** Lalamove and Grab operate, but with
  fewer riders. ETAs stretch — adjust quotes accordingly.
- **Don't share the rider's personal number unprompted.** Once the courier is
  booked, share the tracking link, not the rider's personal contact. Sharing
  personal numbers creates harassment risk for the rider.

## Verification

After this skill runs:
1. Address captured in MEMORY.md under the order
2. Delivery fee computed and added to order total
3. ETA window communicated to customer
4. (After payment) courier booked or owner notified to dispatch

## Reference files

- `templates/delivery-quote-taglish.md` — Quote message
- `references/metro-manila-zones.md` — Zone reference for fee calculation
