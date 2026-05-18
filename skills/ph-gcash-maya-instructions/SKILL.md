---
name: ph-gcash-maya-instructions
description: Sends payment instructions when a customer asks how to pay. Triggers on "how do I pay", "saan ako magbabayad", "paano magbayad", "GCash number niyo", "Maya number", "bank details", "magkano deposit", "payment methods", or any variant asking for the merchant's payment information. Use this skill to send the tenant's configured GCash number, Maya number, bank accounts, or QR code. Do NOT use this for confirming a payment that was already made — that's `ph-payment-confirmation`.
license: Apache-2.0
metadata:
  author: alagad
  version: "1.0"
---

# Send Philippine Payment Instructions

You send the tenant's payment details when a customer asks where or how to pay.
Each tenant has configured their accepted payment methods in their USER.md;
this skill formats and sends them.

## When to use this skill

Trigger phrases:
- "how do I pay?", "where do I pay?", "payment methods po?"
- "saan po ako magbabayad?", "paano mag-bayad?"
- "GCash number niyo po?", "Maya number?", "BPI account?"
- "bank details po", "deposit account"
- "magkano po deposit?" (when asking about reservation deposits)
- "payment options" / "mode of payment"

Do NOT trigger on:
- "paid na po" or any "I already paid" claim → use `ph-payment-confirmation`
- "I want a refund" → escalate, no skill yet
- "payment failed" / "hindi nag-push through" → escalate

## Procedure

### Step 1 — Read the tenant's configured payment methods

The tenant's payment details are in `~/.hermes/USER.md` under the `## Payment Methods`
heading. Expected structure:

```markdown
## Payment Methods
- GCash: 09XX-XXX-XXXX (Account name: ...)
- Maya: 09XX-XXX-XXXX (Account name: ...)
- BPI: 1234-5678-90 (Account name: ...)
- QR Ph: see image at ~/.hermes/assets/qr-ph.jpg
```

If USER.md does not have a `## Payment Methods` section, escalate to the tenant —
don't make up account numbers. Reply to the customer with: *"Pasensya na po,
i-confirm ko po sa team and mag-mememessage ako agad."*

### Step 2 — Determine what to send

If the customer specified a method ("GCash number niyo po?"), send only that
method. If they asked generically ("paano magbayad?"), send all configured methods
in this priority order:

1. QR Ph (if configured) — most flexible, customer picks their own app
2. GCash
3. Maya
4. Bank transfers (BPI, BDO, etc.)
5. Cash on delivery (only if tenant supports it)

### Step 3 — Include the amount and reference

If there's an active order, always include:
- The exact amount to pay
- A reference the customer should include (their name, or the order ID, or both)
- A deadline if the order has one (e.g., reservation expires in 2 hours)

This prevents the "wrong amount" and "which order is this" headaches downstream.

### Step 4 — Send using the template

Use `templates/payment-instructions-taglish.md` (default) or
`templates/payment-instructions-english.md` for English-only customers.

If a QR code image is configured, attach it after the text — the customer can
scan with any supported wallet.

### Step 5 — Set the follow-up expectation

End with: *"Pakishare po ng reference number/screenshot pagkatapos ng payment
para ma-confirm agad."* — This trains the customer to send proof, which makes
`ph-payment-confirmation` work smoothly.

## Pitfalls

- **Never invent account numbers.** If USER.md doesn't have a method configured,
  don't guess from earlier in the conversation. Escalate.
- **Don't share screenshots of your own payment proofs to other customers.** Each
  customer gets the merchant's *receiving* details, not anyone's transaction proofs.
- **Watch for typos in the configured numbers.** If a number is exactly 10 digits
  starting with 09, that's correct. If it's 11 digits or starts with +63, the
  tenant configured it wrong — they need 09XX-XXX-XXXX format. Flag this to the
  tenant once, don't bug them every time.
- **Don't send all methods if customer asked for one.** "GCash number niyo?" gets
  just GCash. Don't bury the answer in a wall of options.
- **Reservation deposits.** Some tenants (salons, party venues) take a partial
  deposit to lock the booking. Check if there's a `deposit_percent` in USER.md
  and compute the deposit amount rather than the full total.

## Verification

After sending, the conversation memory should show:
1. The payment instructions sent to the customer
2. The expected amount and reference noted (for `ph-payment-confirmation` to match against)
3. A timestamp for the "waiting for payment" state

If the customer doesn't respond within 24 hours, the next interaction should
gently re-prompt: *"Hi po, just following up — natuloy po ba ang payment?"*

## Reference files

- `templates/payment-instructions-taglish.md` — Default reply template
- `templates/payment-instructions-english.md` — English-only template
- `references/qr-ph-explainer.md` — How QR Ph works (in case customer asks)
