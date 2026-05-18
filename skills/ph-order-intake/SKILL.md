---
name: ph-order-intake
description: Takes product orders from customers for retail PH SMBs (sari-sari, flowers, food, baked goods, online retail, fashion). Triggers on "I want to order", "order po", "pa-order", "bibili po", "gusto ko ng", "available pa ba ang", "magkano ang", "may stock pa ba", "kumuha ng" followed by a product. Use this skill to identify products, compute totals, capture order details, and prepare the order for payment and delivery. Do NOT use this skill for appointments (use `ph-appointment-booking`) or for payment confirmation of an existing order (use `ph-payment-confirmation`).
license: Apache-2.0
metadata:
  author: alagad
  version: "1.0"
---

# PH Order Intake

You take product orders for retail Filipino SMBs. The tenant's product catalog,
pricing, and inventory live in their USER.md or a referenced catalog file.

## When to use this skill

Trigger phrases:
- "I want to order", "I'd like to buy"
- "order po", "pa-order po", "bibili po"
- "gusto ko ng {product}", "kumuha ng {product}"
- "available pa ba ang {product}?", "may stock pa ba?"
- "magkano ang {product}?" (combined with intent to buy, not just price-checking)
- "include niyo na po ang {product}" (adding to existing order)

Do NOT trigger on:
- "I want to book/reserve" → `ph-appointment-booking`
- "paid na po" → `ph-payment-confirmation`
- "where do I pay?" → `ph-gcash-maya-instructions`

## Procedure

### Step 1 — Read the tenant's product catalog

From `~/.hermes/USER.md` or `~/.hermes/catalog.md`:

```markdown
## Products
- Roses (red): ₱150/stem, ₱1,500/dozen
- Roses (white): ₱180/stem, ₱1,800/dozen
- Bouquet (small): ₱800
- Bouquet (medium): ₱1,500

## Minimum Order
- Delivery: ₱500
- Pickup: no minimum

## Stock Tracking
- Manual: check with owner before confirming
- Auto: see ~/.hermes/inventory.json
```

If the customer's requested product isn't in the catalog, say:
*"Pasensya na po, wala po kaming {product}. Pero mayroon naman po kaming
{closest_match} — okay ba po?"* and offer an alternative.

### Step 2 — Identify quantity and variants

Many customers underspecify. Examples and what to ask:

- "isang dozen na rose" → which color? red or white?
- "2 bouquets" → small or medium? same recipient or different?
- "5 yung manok" → whole, half, by piece? what flavor?

Ask one clarifying question at a time, not a checklist.

### Step 3 — Compute the running total

Show the math, in pesos, with peso sign:

```
- 1 dozen red roses: ₱1,500
- 1 small bouquet: ₱800
Subtotal: ₱2,300
```

Don't include delivery fee yet — that comes from `ph-delivery-coordination` once
the address is known.

### Step 4 — Verify stock (if applicable)

If `stock_tracking: auto` is configured, check inventory.

If `stock_tracking: manual`, the agent should not promise stock — say:
*"Hayaan niyo po, i-check ko muna sa team kung may available na ganitong dami."*
and escalate to the owner with the order details.

### Step 5 — Capture customer details

Required:
- Name
- Contact number (for delivery/pickup coordination)
- Delivery or pickup?
- Date/time needed (especially important for perishables and special-occasion orders)

For occasion-based orders (flowers, cakes), also ask:
- For who? (recipient name)
- Special message to include?
- Any specific date requirement? (Mother's Day, anniversary, etc.)

### Step 6 — Confirm the order

Use `templates/order-summary-taglish.md`. End with:
*"Tama po ba ito? Reply with 'Yes' to confirm and i-aassist ko po kayo sa payment."*

Wait for confirmation before moving to payment instructions.

### Step 7 — Hand off

Once confirmed, the typical next steps are:
1. Customer confirms → call `ph-gcash-maya-instructions` to send payment details
2. Customer pays → `ph-payment-confirmation` validates
3. Address/courier → `ph-delivery-coordination` handles logistics

Record the order in MEMORY.md under `## Active Orders`:
```
- [order_id] {customer_name}: {items}, ₱{total}, {needed_by}, status: awaiting payment
```

## Pitfalls

- **Don't compute totals wrong.** Show the math line by line. Customers catch
  arithmetic errors and lose trust fast.
- **Don't promise stock you can't verify.** "Available pa po" without checking is
  the fastest way to disappoint a customer. Default to "let me check" when
  inventory isn't auto-tracked.
- **Special-occasion deadlines.** "For tomorrow" means different things — for
  flowers, it means tomorrow morning delivery; for cake, it means tomorrow
  before the party. Always pin down a specific time.
- **Don't take orders below minimum without flagging.** If the order is below
  the configured minimum and the customer wants delivery, politely explain:
  *"Pasensya po, ang minimum po sa delivery ay ₱500. Pwede po i-add ang {suggestion}?"*
- **Bulk orders.** Orders of 10+ items or > ₱5,000 should be flagged for owner
  review before confirmation, in case of special pricing or capacity constraints.

## Verification

After the order is captured:
1. Order written to MEMORY.md under `## Active Orders` with status
2. Customer has received the order summary
3. Next step (payment or owner review) is clearly initiated

## Reference files

- `templates/order-summary-taglish.md` — Order summary template
- `templates/out-of-stock-taglish.md` — Out-of-stock response with alternatives
