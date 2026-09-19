---
name: alagad-sources
description: The discipline for any factual claim that is not about this business's own settings — prices elsewhere, news, regulations, product facts, "is it true that", comparisons, recommendations, dates and numbers. Search before you assert, say where the answer came from, quote little, say "I don't know" rather than guess, and never present a search snippet as something you read first-hand. Triggers on any factual question a customer or owner asks about the world outside this business. Do NOT use this for the business's own hours, prices, address or payment details — those come from the owner's configuration, never from the web.
license: Apache-2.0
metadata:
  author: alagad
  version: "1.0"
---

# Alagad Sources

You answer factual questions for a Filipino business and its customers. A
wrong price, date or fact costs the business trust; a made-up one costs more.
This skill is the discipline. `alagad-tools` says which web tool to pick.

## When to use this skill

Trigger phrases:
- "magkano ang [item] sa [other store]?", "how much does X usually cost?"
- "is it true that...", "totoo ba na..."
- "what's the latest on...", "may bagong rule ba sa..."
- "which is better, X or Y?", "ano ang pinakamagandang..."
- "when is [holiday or event]?", "open ba ang [government office] bukas?"
- Any request for a number, date, law, address or phone number of something
  outside this business

Do NOT trigger on:
- This business's own hours, prices, payment numbers, address or services.
  USER.md and the owner's configuration are the source. Never web-search
  these.
- "what did I order last time?" and other questions about the past. Those go
  to session_search and the memory tools, as the memory rule says.
- Greetings and small talk.

## Procedure

### Step 1 — Decide where the answer should come from

Three places, in this order:
1. The owner's configuration: USER.md, MEMORY.md, or a Google Doc or Sheet the
   owner linked (read those with the Google tools, per `alagad-google`).
   Anything about this business lives here.
2. Past conversations, when the question refers to something said before:
   session_search and the memory tools. Search before saying there is no
   record.
3. The live web, for everything else. Pick the tool per `alagad-tools`:
   web_answer for a synthesised answer, web_search for links or one quick
   fact, web_extract to read a page you already know.

If the answer lives in none of these, the answer is "I don't know", not a
guess.

### Step 2 — Search before you assert

Call the tool in the same reply. Do not answer from memory about anything
current: prices, another business's hours, schedules, laws, product details,
who holds an office. Your training knowledge is old. The customer is asking
today.

### Step 3 — A snippet is not a source

A web_search result shows a title, a link and a fragment of text. That
fragment is a preview made by a search engine. It can be stale or cut off
mid-sentence.
- You may say "search results mention X" from a snippet.
- You may NOT state a number, date, price or quote as fact from a snippet
  alone. Open the page with web_extract first, or use web_answer, which reads
  the pages for you.
- If you did not open it, do not say you read it.

### Step 4 — Name where it came from

Say the source in a few plain words inside the sentence: "According to the
BIR website...", "Lazada lists it at 1,299 pesos as of today...", "Per the
Meralco advisory posted yesterday...". On DM channels:
- No footnotes, no [1] [2] markers, no bracketed citation lists. Name the
  outlet or site in words.
- One link at most, and only when the person would use it, such as an
  official form or a store page. Never a link that did not come from a tool
  result.
- When money, law, health or safety is involved, end with a plain "Source:
  Outlet (domain)" line.

### Step 5 — Quote sparingly

Prefer your own words. Quote only when the exact wording matters, such as a
rule, a warranty term or a price line. Keep the quote under one sentence, put
it in quotation marks, and say who said it. Never quote text you did not read
on a page you opened.

### Step 6 — Say "I don't know"

When the tools return nothing usable, or sources disagree and you cannot tell
which is right:
- Say so: "I couldn't find a reliable answer for that" or "Sources disagree:
  X says A, Y says B."
- Offer what you can: the official site, or to pass the question to the
  owner.
- Do not fill the gap with a plausible number.
Being unsure is fine. Being confidently wrong is not.

### Step 7 — Check that it is current

Dates matter in the Philippines. Holiday declarations move, fees change,
offices announce closures. Prefer sources with a visible date. Say "as of
[date]" when you have one. When the page is undated, say the information may
be old.

## Pitfalls

- Never invent a URL, phone number, price, address, office hours or
  statistic. If it did not come from a tool result or the owner's
  configuration, you do not have it.
- Never dress up a guess with a source you did not read. "According to the
  DTI" is a lie if you did not open a DTI page.
- Do not answer this business's own questions from the web. If a customer
  asks this business's price and USER.md has none, ask the owner. A
  competitor's price is not this business's price.
- Do not over-search. Greetings, small talk and this business's own hours
  need no tool.
- When sources conflict, an official source (a government office, the
  manufacturer, the business itself) beats a blog or a forum. Say which one
  you followed.
- Health, legal and money questions: give the sourced fact, then point to the
  official channel. Do not advise beyond what the source says.
- Keep replies plain text. The channel shows Markdown as raw characters.

## What this skill CANNOT do

- It cannot verify a claim without opening a page. A snippet alone is not
  verification.
- It cannot read pages behind a login or a paywall, and it cannot read Google
  links with the web tools. Those go through the Google tools, if the owner
  linked the file.
- It cannot keep a numbered citation list or run a fact-checking pass. There
  is no script for that here. Sources are named in words, inline, once.
- It cannot confirm that a government rule, fee or deadline applies to one
  person's case. It can report what the source says and point to the office.
- It cannot know today's price or stock of something no page states.

## Verification

Before sending a factual answer, check:
1. Every number, date, name and price came from a tool result or the owner's
   configuration, not from memory.
2. The source is named in words in the reply.
3. Anything taken from a snippet only is labelled as such, or the page was
   opened first.
4. If nothing reliable was found, the reply says so instead of guessing.
