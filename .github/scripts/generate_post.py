#!/usr/bin/env python3
"""
Generate a formatted HTML blog post from a walking tour transcript,
plus a JSON sidecar for use by the Getty metadata tool.
Called by GitHub Actions after a new .txt is pushed to _transcripts/.
"""

import os
import sys
import json
import re
import anthropic

TRANSCRIPT_PATH = os.environ["TRANSCRIPT_PATH"]
SLUG = os.environ["SLUG"]
OUTPUT_PATH = f"_posts/{SLUG}.html"
JSON_PATH = f"_data/{SLUG}.json"

os.makedirs("_data", exist_ok=True)

with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
    transcript = f.read()

SYSTEM_PROMPT = """You are a writer producing blog posts for "On Foot — Walking Tour Notes", a personal heritage-style blog of guided walking tours.

Your task: given a raw audio transcript of a guided walk, produce a single complete, self-contained HTML page in the exact style and structure described below.

─── STYLE REFERENCE ───

The blog aesthetic is sepia/heritage: dark ink header, aged parchment body, crimson and gold accents. Use this CSS variable palette:
  --ink: #141218
  --paper: #f4f0e6
  --aged: #e6dcc8
  --sepia: #7a6045
  --crimson: #8c1f28
  --gold: #a8832a
  --ash: #635c52

Fonts (load from Google Fonts):
  EB Garamond (body text, italic variants)
  Cormorant Garamond (headings, light weight)
  Overpass Mono (labels, metadata, monospace elements)

─── REQUIRED PAGE STRUCTURE ───

1. <header> — dark background (#141218), contains:
   - .header-label (Overpass Mono, gold, uppercase): "Walking Tour Transcript — [Location]"
   - <h1> in Cormorant Garamond, light weight, with <em> for a subtitle phrase in gold
   - .header-sub: guide name and tour operator if mentioned
   - .header-meta: route summary | duration | guide name — inferred from transcript

2. <nav class="toc"> — table of contents with anchor links to each section, gold left border

3. <main> — max-width 760px, centred. Contains sections, each with:
   - .section-tag (Overpass Mono, gold, uppercase): "Stop N · Place Name" or "Introduction" etc.
   - <h2> in Cormorant Garamond with optional <em> phrase
   - .location span where relevant: "◉ Place Name · Date/century"
   - Prose paragraphs
   - story-box divs (data-label attribute for the box title) for anecdotes and set pieces
   - key-fact divs with a large number/date and explanatory text
   - blockquote for direct guide quotes (with <cite> attribution)
   - .iza-says / .guide-says class for inline guide voice (italic, sepia, left border)
   - .highlight / .highlight-blue / .highlight-green spans for emphasis within prose
   - .practical divs (dark background) for visitor tips, opening hours, etc.

4. <footer> — dark, Overpass Mono, small. Tour operator if known, disclaimer line.

─── CONTENT INSTRUCTIONS ───

- Infer the title, subtitle, location, date, guide name, route, and duration from the transcript. If the date is not stated, omit it.
- Structure the post stop-by-stop, following the order of the walk.
- Extract and present the guide's best anecdotes in story-boxes with evocative data-label titles.
- Use key-fact callouts for significant numbers, years, or statistics mentioned.
- Quote the guide directly (in blockquote) for their most vivid or memorable lines. Clean up transcription errors but preserve the guide's voice.
- Use .guide-says for shorter inline guide remarks.
- Write connecting prose between stops in a polished but unstuffy editorial voice — as if a good magazine writer attended the walk and is now writing it up.
- Include practical info (opening times, ticket prices, tips) if mentioned.
- The HTML must be complete and self-contained (no external dependencies except Google Fonts and the CSS defined inline in <style>).
- Output ONLY the raw HTML. No markdown, no code fences, no preamble. Start with <!DOCTYPE html>.

─── CSS ───

Include full CSS in a <style> block in <head>. Model it closely on the Kraków tour blog style: noise texture overlay, header with large watermark glyph (use ✦ or a relevant symbol), toc with gold left border, story-box with gold top border and floating label, key-fact with dark background and large gold number, blockquote with crimson left border, practical box with dark background and gold left border, .guide-says with sepia left border and italic text, highlight spans with yellow/blue/green backgrounds.

The page must look beautiful and complete when opened in a browser."""


client = anthropic.Anthropic()

print(f"Generating post for: {SLUG}")
print(f"Transcript length: {len(transcript)} chars")

message = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=8000,
    system=SYSTEM_PROMPT,
    messages=[
        {
            "role": "user",
            "content": f"""Please generate the blog post HTML for this walking tour transcript.

Slug (use for any internal references): {SLUG}

Transcript:
---
{transcript}
---

Output only the complete HTML. Nothing else."""
        }
    ]
)

html = message.content[0].text

# Strip any accidental markdown fences
if html.startswith("```"):
    lines = html.split("\n")
    html = "\n".join(lines[1:])
    if html.rstrip().endswith("```"):
        html = html.rstrip()[:-3].rstrip()

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Post written to: {OUTPUT_PATH}")

# ─── SECOND CALL: JSON SIDECAR ───────────────────────────────────────────────

JSON_SYSTEM = """You are a metadata extraction assistant for a photographer who shoots editorial stock images on walking tours.

Given a walking tour transcript, extract structured metadata useful for captioning and keywording Getty Images editorial photos taken on the same walk.

Return ONLY a valid JSON object — no markdown, no fences, no explanation. Use this exact schema:

{
  "slug": "string — the walk identifier",
  "title": "string — full walk title",
  "date": "string — ISO date if mentioned, else null",
  "location": {
    "city": "string",
    "area": "string — neighbourhood or district",
    "country": "string",
    "postal_district": "string or null — e.g. SW18",
    "coordinates_approx": "string or null — e.g. 51.4567,-0.1912"
  },
  "guide": {
    "name": "string or null",
    "affiliation": "string or null — tour company, trust, etc."
  },
  "walk": {
    "distance_km": "number or null",
    "duration_approx": "string or null",
    "start_point": "string",
    "end_point": "string",
    "route_summary": "string — one sentence"
  },
  "stops": [
    {
      "name": "string — place or stop name",
      "type": "string — e.g. building, park, street, bridge, pub, church, viewpoint",
      "description": "string — one sentence for caption use",
      "date_built": "string or null",
      "historical_period": "string or null — e.g. Victorian, Georgian, Medieval",
      "notable_associations": ["string — person or event names"]
    }
  ],
  "getty_keywords": {
    "subjects": ["string — primary subjects visible or implied, Getty-style"],
    "concepts": ["string — themes and concepts, Getty-style"],
    "historical_figures": ["string — full names mentioned"],
    "architectural_styles": ["string — e.g. Georgian, Brutalist, Arts and Crafts"],
    "time_periods": ["string — centuries or named eras relevant to the walk"],
    "events": ["string — named historical events mentioned"]
  },
  "caption_context": {
    "borough_or_region": "string",
    "primary_theme": "string — one phrase summarising the walk's main theme",
    "secondary_themes": ["string"],
    "suggested_caption_prefix": "string — a reusable opening phrase for image captions from this walk, e.g. 'A view of [area], an area undergoing significant regeneration in south-west London'"
  },
  "vocabulary": {
    "confirmed_spellings": ["string — proper nouns and place names with correct spelling"],
    "local_terms": ["string — local or historical terms explained briefly, format: 'term: definition'"]
  }
}"""

print("Generating JSON sidecar...")

json_message = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=3000,
    system=JSON_SYSTEM,
    messages=[
        {
            "role": "user",
            "content": f"""Extract metadata from this walking tour transcript.

Slug: {SLUG}

Transcript:
---
{transcript}
---

Return only the JSON object."""
        }
    ]
)

json_raw = json_message.content[0].text.strip()

# Strip any accidental markdown fences
if json_raw.startswith("```"):
    lines = json_raw.split("\n")
    json_raw = "\n".join(lines[1:])
    if json_raw.rstrip().endswith("```"):
        json_raw = json_raw.rstrip()[:-3].rstrip()

# Validate and pretty-print
try:
    data = json.loads(json_raw)
    # Ensure slug is set
    data["slug"] = SLUG
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"JSON sidecar written to: {JSON_PATH}")
except json.JSONDecodeError as e:
    print(f"Warning: JSON parse error — {e}")
    print("Raw output saved as-is for inspection.")
    with open(JSON_PATH + ".raw", "w", encoding="utf-8") as f:
        f.write(json_raw)
