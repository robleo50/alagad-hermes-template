---
name: ph-payment-confirmation
description: Confirms customer payments via GCash, Maya, or bank transfer when a customer sends a payment screenshot, reference number, or message like "paid na po", "bayad na", "nag-send na", "transferred na", or any variant claiming a payment was made. Use this skill to verify the payment claim against the order, acknowledge receipt, and update the conversation memory. Do NOT use this skill for refund requests or payment failures — those have different flows.
license: Apache-2.0
metadata:
  author: alagad
  version: "1.0"
---

# Philippine Payment Confirmation

You handle payment confirmations from Filipino customers who pay via GCash, Maya,
QR Ph, or bank transfer (BPI, BDO, UnionBank, Metrobank, Landbank). Customers
typically prove payment by sending a screenshot, a reference number, or just
saying "paid na po" with no proof at all.

## When to use this skill

Trigger phrases (English, Tagalog, Taglish):
- "paid na po", "bayad na", "nabayaran na", "nag-bayad na ako"
- "nag-send na po", "transferred na", "nag-GCash na ako", "Maya na po"
- "here's my reference number", "ref no.", "reference: ..."
- Customer sends an image that looks like a payment app screenshot
- "for confirmation po", "confirm niyo na po"

Do NOT trigger on:
- "how do I pay?" → use `ph-gcash-maya-instructions` instead
- "I want a refund" → handle as a refund request (no skill yet, escalate)
- "the payment failed" → escalate to human, do not auto-confirm

## Procedure

### Step 1 — Identify the claimed payment method

Look for these signals in the customer's message:
- **GCash:** "GCash", "G-Cash", a 13-digit reference number, blue GCash UI screenshot
- **Maya:** "Maya", "PayMaya" (legacy name still common), green/teal Maya UI screenshot
- **QR Ph:** "QR Ph", "QRPh", "scanned the QR" — interoperable, may settle to GCash or Maya
- **Bank transfer:** Bank name mentioned (BPI, BDO, etc.), longer 12-15 digit reference, bank app screenshot
- **InstaPay / PESONet:** "InstaPay" = instant, "PESONet" = same-day batch

If none are identifiable, ask: *"Salamat po! Pwede po ba malaman kung GCash, Maya,
or bank transfer ang ginamit niyo?"*

### Step 2 — Extract verification details

Try to get all three:
1. **Reference number** — required. GCash: 13 digits. Maya: 12 digits. Banks: 12-15 digits.
2. **Amount** — must match the order total. Watch for typos and senders rounding up.
3. **Timestamp** — when the payment was made. Same-day payments are normal; older
   payments (>24h) may indicate this is a different transaction.

If the customer sent a screenshot, extract these visually. If they sent text only,
ask politely: *"Pakishare po ng reference number para ma-check namin agad."*

### Step 3 — Match against the active order

Check `~/.hermes/sessions/` and conversation memory for an active order or invoice
for this customer. The amount should match exactly. Acceptable mismatches:
- Customer rounded up (e.g., ₱497 invoice, ₱500 paid) — accept and note credit
- Customer paid in installment — accept partial, note balance

Unacceptable mismatches:
- Underpayment by more than ₱5 — politely ask to top up
- Payment ₱100+ over the total — flag for manual review (could be wrong order)

### Step 4 — Acknowledge

Use the template at `templates/confirmation-taglish.md` (default) or
`templates/confirmation-english.md` if the customer has been writing in pure English.

Key elements of the acknowledgment:
- Thank them by name if known
- Restate the amount and order
- State next steps (preparing, scheduling, dispatching)
- Set an ETA expectation if applicable

### Step 5 — Update memory

Write to `~/.hermes/MEMORY.md` under a "Recent payments" section:
```
- [YYYY-MM-DD HH:MM] <customer_name>: ₱<amount> via <method>, ref <number>, order <id>
```

This is the only audit trail the agent has — keep it consistent.

## Pitfalls

- **Don't auto-confirm without a reference number.** "Paid na po" without proof is
  a common scam pattern. Always ask for the ref number or screenshot first.
- **Don't confirm twice.** If MEMORY.md already shows this reference, reply with
  "Na-confirm na po ito kanina" — duplicate confirmations create duplicate orders.
- **Watch for screenshot edits.** Edited screenshots are common. If the screenshot
  looks suspicious (mismatched fonts, unusual layout), ask for the in-app share
  link instead, which can't be faked.
- **Don't ask for sensitive data.** Never ask for MPIN, OTP, card CVV, or login
  credentials. A reference number alone is enough to verify.
- **Time zones.** PH is UTC+8. Customers occasionally send screenshots from devices
  set to other zones — don't reject a payment over a 1-hour timestamp mismatch.

## Verification

After confirming, the conversation memory should show:
1. The payment recorded under "Recent payments"
2. The associated order moved from "Pending payment" to "Paid"
3. A reply sent to the customer acknowledging receipt

If any of these are missing, the skill did not complete successfully — retry the
relevant step rather than re-confirming with the customer.

## Reference files

- `references/payment-methods.md` — Full reference number formats per provider
- `references/scam-patterns.md` — Common payment fraud patterns to watch for
- `templates/confirmation-taglish.md` — Default reply template
- `templates/confirmation-english.md` — English-only reply template
