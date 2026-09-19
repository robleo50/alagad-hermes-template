---
name: alagad-receipts
description: Reads photos and screenshots customers send — a GCash or Maya payment receipt, a bank-transfer confirmation, a purchase order, a handwritten order list — with the vision tool, then says back what was read, in words, before anything is acted on. Triggers when a message arrives with a photo or screenshot, when a customer says "sent na po" or "eto po resibo" with an image, or when someone photographs an order list or PO. Do NOT use this for a text-only "paid na po" (that's `ph-payment-confirmation`), for "how do I pay?" (`ph-gcash-maya-instructions`), or for pricing a typed order (`ph-order-intake`). A read is never a confirmed payment — see the CANNOT section.
license: Apache-2.0
metadata:
  author: alagad
  version: "1.0"
---

# Alagad Receipts and Photographed Orders

Filipino customers send proof and orders as pictures: a GCash or Maya
screenshot, a bank app confirmation, a photo of a purchase order, a
handwritten list. You read the image with vision_analyze, say back what you
read, and only then hand the result to the skill that decides what happens
next.

Reading is this skill's whole job. Accepting a payment belongs to
`ph-payment-confirmation`. Sending payment details belongs to
`ph-gcash-maya-instructions`. Pricing an order belongs to `ph-order-intake`.

## When to use this skill

Trigger signals:
- A message with a photo or screenshot attached, especially with "sent na
  po", "eto po", "for confirmation", "resibo", "proof of payment"
- "eto po yung order ko" with a photo of a list or a PO
- "pa-check po kung tama" with an image
- A receipt from GCash, Maya, BPI, BDO, UnionBank, Metrobank, Landbank or
  another Philippine bank app

Do NOT trigger on:
- "paid na po" with no image → `ph-payment-confirmation` asks for the
  reference number
- "saan ako magbabayad?" → `ph-gcash-maya-instructions`
- A typed list of items → `ph-order-intake` directly
- A product photo with "meron ba kayo nito?" → answer from the catalog; look
  at the image if it helps, but this is not a receipt flow

## Procedure

### Step 1 — Look at the image

Call vision_analyze with the photo the message carries (its path or link) and
a question that names what you want. For a receipt: "Read this payment
receipt: app, status, amount, reference number, date and time, sender's first
name." For an order photo: "List every line item with its quantity." Do this
in the same reply.

If you cannot see the image at all (no vision tool on this channel, or the
tool fails), say so in business terms. Ask the customer to type the amount and
reference number, or say the owner will check the picture.

### Step 2 — Decide what kind of document it is

- GCash: blue interface, 13-digit reference number
- Maya: green or teal interface, 12-digit reference number
- Bank transfer (InstaPay or PESONet): the bank's colours, 12 to 15 digit
  reference number
- Purchase order: a form with item lines and quantities, sometimes a PO number
- Handwritten order: a list, usually with the quantity before the item
- Something else: a menu, a product photo, a screenshot of a chat. Not a
  receipt.

The full reference-number formats and the bank colour guide live in
`ph-payment-confirmation`'s references. Use them; do not repeat them here.

### Step 3 — Extract field by field, and grade each read

For a payment receipt: status (Sent, Successful, Completed), amount, reference
number, date and time, sender's first name, and the receiving account name if
shown.

For each field ask: did I read every character clearly? A field is CLEAR only
when every digit is legible. A reference number with one uncertain digit is
UNCLEAR. Never fill in a digit you cannot see.

For an order: each line as quantity, item, variant, plus the customer's name
and date if written. Mark any line you cannot read.

### Step 4 — Say the read back in words, before acting

Repeat what you read, in plain text, and ask if it is right:

*"Nakita ko po sa screenshot: GCash, Successful, 1,500 pesos, reference
1234567890123, sent today 2:14 PM. Tama po ba?"*

*"Nabasa ko po sa listahan: 2 kilo bangus, 1 dozen itlog, 3 pack pancit
canton. Hindi ko po nabasa yung ikaapat na line. Ano po yun?"*

Wait for the customer's yes or correction before anything is logged or
confirmed. If the customer corrects a field, use their correction and keep a
note that the image read differed.

### Step 5 — Blurry, partial, cropped or wrong

Do not go on to confirmation when:
- The amount or the reference number is not fully legible
- The status, amount or reference number is cropped out of the picture
- The image is a photo of a screen with glare, or a small thumbnail
- The receipt shows Pending or Failed, or a receiving name that is not this
  business

Ask once, and be specific about what is missing:

*"Medyo malabo po yung reference number. Pakisend po ng full screenshot ng
receipt, hindi cropped, o yung share-receipt link mula sa app."*

If the second image is still unreadable, stop asking. Tell the customer the
owner will verify it, and note it for the owner. Never say "confirmed" to end
the back-and-forth.

### Step 6 — Hand off

- Payment receipt, every field CLEAR, customer confirmed the read → continue
  with `ph-payment-confirmation`. It matches the amount to the active order,
  checks for a duplicate reference number, watches the scam patterns, sends
  the acknowledgment and records the payment. Do not do those steps here.
- Order photo or PO, lines confirmed → continue with `ph-order-intake` to
  price it and compute the total, then the usual payment and delivery skills.
- Log the lead or order when the Google tools are in your tool list, per
  `alagad-google`: contact_save for a new customer's name and number;
  tracker_add_row with name, contact, channel, enquiry (for example "Paid
  1,500 pesos by GCash, reference ending 0123, order 12") and status. Say
  "noted" only after the tool returned success. If the Google tools are not
  listed on this channel, keep the record in memory as the ph skills describe
  and tell the owner.

## Pitfalls

- A screenshot shows what the sender's screen showed, not that money arrived.
  Only the owner's own wallet or bank shows that. This skill says "nabasa ko"
  (I read it), never "na-receive na". "Received" is `ph-payment-confirmation`'s
  word, after its checks pass.
- Never guess digits. The reference number is matched later, and one wrong
  digit makes the record useless. If unsure, ask.
- Never ask for an MPIN, OTP, PIN, CVV, password or full card number. If one
  appears in the image, do not repeat it and do not record it.
- Do not read out a stranger's full name, full account number or mobile
  number from the image. First name and the last four digits at most.
- Edited screenshots exist: mismatched fonts, a blurred patch around the
  amount, a reference number of the wrong length. Do not accuse. Say you
  cannot read it clearly, ask for the in-app share link, and escalate to the
  owner if it persists. The scam patterns are in `ph-payment-confirmation`'s
  references.
- Do not loop. Two requests for a better photo, then hand to the owner.
- Do not describe the tool or the image file to the customer. "Let me look at
  the screenshot" is fine. File names and paths are not.
- Handwritten orders: the quantity usually comes first ("2 kg bangus"), and
  "1/2" and "1 doz" are common. Read them as written, then confirm.

## What this skill CANNOT do

- It cannot confirm that a payment arrived. It reads a picture. Confirmation
  is `ph-payment-confirmation`'s decision and, in the end, the owner's wallet.
- It cannot check a reference number with GCash, Maya or a bank. No tool does.
- It cannot detect a forged screenshot reliably. It can flag the signs and ask
  for the share link.
- It cannot read PDF files or multi-page scans as documents. Ask for a photo
  or screenshot of the page instead.
- It cannot read a QR code. Ask for the number or the share link.
- It cannot process a refund or a reversal. Escalate to the owner.
- It cannot correct a logged row afterwards; the sheet is append only. If a
  read turns out wrong after logging, add a corrected row and tell the owner.

## Verification

After this skill runs:
1. The reply repeats every field you relied on, in words, and asks for (or
   has received) the customer's confirmation.
2. No field marked UNCLEAR was used as fact.
3. Nothing was called "confirmed", "received" or "noted" unless the follow-on
   skill or a tool actually did it.
4. If a better photo was requested, the reason named the field and why.
