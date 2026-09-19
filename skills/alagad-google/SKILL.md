---
name: alagad-google
description: How to use the business's connected Google tools — calendar (free slots, book, upcoming, cancel), contacts (save, search, list), the lead-tracker sheet (add a row, read rows, list headers) and reading a Google Doc the owner links. Triggers when the owner or a customer asks to book, check or cancel an appointment, save or look up a contact, log a lead, read or add to a Google Sheet, read a Google Doc, or pastes a docs.google.com link. Do NOT use this for a photographed receipt or order (that's `alagad-receipts`) or for facts from the web (that's `alagad-sources`). There is no Gmail, no Drive browsing and no editing here — see the CANNOT section before promising anything.
license: Apache-2.0
metadata:
  author: alagad
  version: "1.0"
---

# Alagad Google Tools

The business may have a Google account connected through Alagad. When it is,
eleven Google tools appear in your tool list, each with the prefix
mcp__alagad_google__ (for example mcp__alagad_google__calendar_book). This
skill says which one to use for what, and what none of them can do.

If none of these tools is in your tool list, Google is not connected on this
channel. Take the details down, say the owner will handle the Google side, and
do not promise a booking or a logged row.

## When to use this skill

Trigger phrases:
- "book me for Tuesday 2pm", "may slot ba bukas?", "pa-cancel ng appointment ko"
- "save my number", "do we have a contact for Ana?", "sino po si Ana?"
- "log this lead", "add to the tracker", "ilagay mo sa sheet"
- "how many leads this week?", "read the tracker", "ano ang nasa sheet?"
- "here's the price list" followed by a Google Docs or Sheets link
- Any docs.google.com link pasted into the chat

Do NOT trigger on:
- A photo of a receipt, PO or order list → `alagad-receipts` (it comes back
  here to log the result)
- A question about the world, another store's price, news → `alagad-sources`
- "how do I pay?" → `ph-gcash-maya-instructions`

## The eleven tools

| Tool | Use it when | What to give it |
|------|-------------|-----------------|
| calendar_free_slots | Someone asks for available times | date as YYYY-MM-DD; duration in minutes if not 30 |
| calendar_book | The person picked a time you already checked | title, start as YYYY-MM-DDTHH:MM:SS in the business's local time, duration_minutes, optional description |
| calendar_upcoming | "what's booked?", "anong schedule ko?" | days ahead (default 7) |
| calendar_cancel | Cancel an appointment this assistant booked | the event_id from calendar_upcoming, only where agent_booked is true |
| contact_save | A new customer gave a name plus a phone or email | name; phone, email, note optional |
| contact_search | Find one saved person | part of a name, a phone, or an email |
| contact_list | "show me my contacts" | nothing; returns up to 200 |
| tracker_add_row | Log a lead or enquiry | name, contact, channel, enquiry, status, notes, each as its own field |
| tracker_read | Read or count rows | range optional; spreadsheet optional |
| sheet_headers | You need a sheet's column names | spreadsheet optional |
| doc_read | Read a Google Doc the owner linked | document (link or ID, required); offset only when continuing |

## Procedure

### Step 1 — Which sheet or doc?

- The tracker is the default. Leave spreadsheet empty and the sheet tools use
  the business's own lead tracker.
- Any other sheet needs its link or ID pasted by the owner. You cannot search,
  list or browse Drive, so you cannot find a file by its name. If someone says
  "the sheet from last month" and no link is in the conversation, ask for the
  link.
- A doc always needs a link. doc_read has no default document.
- Google links never go to the web tools. web_extract and web_search hit a
  sign-in wall on docs.google.com.
- Match the link to the tool. A link with /spreadsheets/ goes to the sheet
  tools. A link with /document/ goes to doc_read. The wrong pairing fails.

### Step 2 — Booking

Free slots first, book second. Never promise a time you have not checked.
Turn "bukas 2pm" into a concrete date and time in the business's local time
before calling. If calendar_free_slots returns nothing near the requested
time, offer the closest times it did return, at most three.

Book with a title that names the person and the service, like
"Haircut - Ana". When calendar_book returns success, say the date and time
back in words. If it fails, say it did not go through. Do not say "booked"
unless the tool returned success in this reply.

Rescheduling: there is no reschedule tool. To move an appointment this
assistant booked, check free slots for the new time, book the new time, then
cancel the old event_id. Tell the person both steps happened. If the old
appointment was not booked by this assistant (agent_booked is false), you
cannot cancel it. Book nothing and say the owner has to change it.

### Step 3 — Contacts

Save when you have a name plus at least a phone or an email. For a returning
customer, contact_search by name or phone before saving, so you do not create
a duplicate. contact_search needs something to search for; ask for a name if
none was given. contact_list returns up to 200 rows; when the owner asks about
one person, search instead of listing.

### Step 4 — Logging a lead

Give each detail as its own field: name, contact, channel (Telegram,
Messenger, Viber, walk-in), enquiry, status (New, Follow up, Booked, Paid),
notes. Do not pack everything into notes; the sheet's columns fill from the
named fields. Call sheet_headers first only when the owner named a different
sheet and you need its columns. If the tool answers that no tracker sheet is
set up, stop and tell the owner. Do not retry.

### Step 5 — Reading, and what to do when truncated is true

- tracker_read returns up to 500 rows per call and includes truncated. When
  truncated is true, the answer also carries next_range. Call tracker_read
  again with range set to that next_range, and repeat until truncated is
  false. Only then count, total or summarise.
- doc_read returns up to 60,000 characters per call and includes truncated
  and next_offset. Same rule: call again with offset set to next_offset until
  truncated is false.
- Never answer "how many" or "the total" from the first page. If the first
  page already holds a specific fact the owner asked for (one name in row 3),
  you may answer it and say the sheet continues.
- If a full read would take many calls, say what you have read so far and ask
  whether to read the rest.

### Step 6 — When a tool says no

The tools answer in plain words. Repeat the meaning in business terms, do not
retry, and do not look for another route:
- "No Google account is connected", "the connection has expired", "missing
  the permission": only the owner can fix this, from their Alagad dashboard.
  Say that and move on.
- "not shared with the business's connected Google account": ask the owner to
  share that file with the Google account they connected to Alagad. That is a
  normal private share to one account.
- "not booked by this assistant": the owner has to change or cancel it.
- "Google did not answer properly": you may try once more, then report.

## Pitfalls

- Never ask anyone to make a file public or to set sharing to "anyone with
  the link". A private share with the connected account is the only sharing
  you may ever ask for.
- Never ask anyone to set up Google credentials, sign in to Google for you,
  create an API key, download a client secret, install anything, or authorise
  you. Connecting Google is one action the owner takes in their Alagad
  dashboard. You do not describe how it works, and you never claim a missing
  "skill" or file is the reason.
- Never invent a booking, a contact or a row. If you did not call the tool and
  see success, it did not happen.
- Dates are YYYY-MM-DD. Start times are YYYY-MM-DDTHH:MM:SS in the business's
  local time (Philippine time is UTC+8). Do not add a Z or a timezone offset.
- Give duration, days and offset as plain numbers, not quoted text.
- Do not call calendar_cancel on anything the owner booked by hand.
- Do not name tools, files, folders or skills to a customer. Say what happened
  in business terms: "Booked for Tuesday 2 PM", "Added to your lead list".

## What this skill CANNOT do

Say plainly that you cannot, offer what you can, and never describe a
workaround:
- Gmail: no reading, sending or searching email.
- Drive: no browsing, listing, searching, uploading, creating, moving or
  sharing files. You reach only the tracker and a file whose link was pasted.
- Docs: read only. No creating, editing, commenting or formatting. Only a
  Google Doc can be read; an uploaded Word or PDF file in Drive cannot.
- Sheets: read and append only. No editing an existing row, no deleting, no
  clearing, no sorting, no formulas, no new tabs, no new spreadsheets.
- Calendar: no editing or rescheduling an event in place, no attendees or
  invitations, no Google reminders, no other calendars, no cancelling events
  the owner made.
- Contacts: no editing or deleting a saved contact, no groups, no export.
- Nothing here confirms a payment or reads a receipt.

## Verification

After a Google action:
1. The tool returned success in this reply, and the reply states the result in
   words.
2. If the owner asks, a follow-up read shows it: calendar_upcoming for a
   booking, contact_search for a contact, tracker_read for a row.
3. Any truncated read was followed to the end before a count or total.
