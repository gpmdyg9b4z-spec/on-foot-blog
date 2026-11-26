#!/usr/bin/env python3
"""
Generate a blog post from notes taken on a walking tour.

Writes:
  _posts/<slug>.html   the post, using the shared stylesheet assets/post.css
  _data/<slug>.json    metadata sidecar (Getty captioning/keywording context)

The post gets a walk-meta block (date, place, themes, series, card text) that
build_site.py uses for the homepage, filters and "More walks" links.

Environment: ANTHROPIC_API_KEY, NOTES_PATH, SLUG.
"""

import json
import os
import re
import sys
from datetime import date

import anthropic

sys.path.insert(0, os.path.dirname(__file__))
from onfoot import MODEL, PLACES, SERIES, THEMES, finalise_post, strip_fences, walk_meta_block  # noqa: E402

NOTES_PATH = os.environ["NOTES_PATH"]
SLUG = os.environ["SLUG"]
POST_PATH = f"_posts/{SLUG}.html"
JSON_PATH = f"_data/{SLUG}.json"

os.makedirs("_data", exist_ok=True)

with open(NOTES_PATH, encoding="utf-8") as f:
    notes = f.read()
with open("index.html", encoding="utf-8") as f:
    index_html = f.read()

# Use the most recent post on the homepage as the markup template, so new posts
# follow whatever the current hand-edited house style is.
first_card = re.search(r'<a class="post-card" href="_posts/([^"]+)\.html"', index_html)
exemplar_slug = first_card.group(1) if first_card else "hastings-stade-2026"
with open(f"_posts/{exemplar_slug}.html", encoding="utf-8") as f:
    exemplar = f.read()

client = anthropic.Anthropic()


def call(system: str, user: str, effort: str) -> str:
    """One streamed request, with server-side refusal fallback. Fails loudly on
    truncation or refusal rather than writing a partial file."""
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": effort},
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        sys.exit(f"Request declined ({getattr(msg.stop_details, 'category', None)}); nothing written.")
    if msg.stop_reason == "max_tokens":
        sys.exit("Output hit max_tokens; nothing written.")
    return "".join(b.text for b in msg.content if b.type == "text")


# ─── 1. The post ────────────────────────────────────────────────────────────

POST_SYSTEM = f"""You write posts for "On Foot — Walking Tour Notes", a personal blog of guided walking tours, written up from the author's notes.

Given raw notes from a walk, produce one complete HTML page that matches the house template below exactly in structure, class names and tone.

Rules:
- Use British English spelling throughout.
- Styling comes from the shared stylesheet: put <link rel="stylesheet" href="../assets/post.css"> in <head>. Do not write your own CSS, except an optional short <style> block that sets the header watermark glyph, e.g. `header::before {{ content: '⚓'; }}`, chosen to suit the walk.
- Use only the classes the template uses: header-label, header-sub, header-meta, toc / toc-title, section, section-tag, location, story-box (with data-label), key-fact / key-fact-number / key-fact-text, blockquote with <cite>, guide-says, highlight / highlight-blue / highlight-green, practical, divider, footnote.
- The header label reads "Walking Tour Notes — <place>". Header meta gives route, duration and the guiding organisation, inferred from the notes; omit anything not stated.
- Follow the walk stop by stop. Put the guide's best anecdotes in story-boxes with evocative data-labels, significant numbers in key-facts, the guide's most vivid lines in blockquotes (tidy them up, keep their voice), shorter remarks in .guide-says, and visitor information in .practical.
- Privacy: never name guides, volunteers, residents or other members of the public — say "the guide", "a volunteer", or give their role or organisation — and leave out personal details such as family, where they grew up, nationality, religion or career history. Named historical and public figures are fine.
- Never mention recordings, audio, transcripts or transcription. The post is written from notes; if something was unclear, say it isn't clear in the notes.
- Connecting prose: polished but unstuffy, as if a good magazine writer had been on the walk. Where a claim made on the walk is disputed or a popular story doesn't hold up, say so plainly.
- The page starts with <!DOCTYPE html>, has <html lang="en-GB"> and a <title> of the form "<Headline> — <Place>". Include the same <nav class="home-nav"> bar as the template.
- Output only the HTML: no commentary, no code fences.

House template (a real post — copy its structure, not its content):
<template>
{exemplar}
</template>"""

print(f"Generating post: {SLUG} (template: {exemplar_slug}, notes {len(notes):,} chars)")
post_html = strip_fences(call(
    POST_SYSTEM,
    f"Slug: {SLUG}\n\nNotes:\n<notes>\n{notes}\n</notes>",
    effort="high",
))
if not post_html.lstrip().lower().startswith("<!doctype html"):
    sys.exit("Model output does not look like an HTML page; nothing written.")

# ─── 2. Metadata sidecar + index card ───────────────────────────────────────

place_list = "\n".join(f"  {k} = {v}" for k, v in PLACES.items())
theme_list = "\n".join(f"  {k} = {v}" for k, v in THEMES.items())
series_list = "\n".join(f"  {k} = {v}" for k, v in SERIES.items())

JSON_SYSTEM = f"""You extract structured metadata from walking tour notes for a London-based editorial photographer who shoots Getty Images editorial stock on the same walks, and who publishes the walks on a blog.

Return ONLY a valid JSON object (no fences, no commentary) with exactly this schema. Use British English. Use null where the notes don't say.

{{
  "slug": "string",
  "title": "string — full walk title",
  "date": "YYYY-MM-DD if stated, else null",
  "location": {{
    "city": "string", "area": "string — neighbourhood or district", "country": "string",
    "postal_district": "string or null — e.g. SW18",
    "coordinates_approx": "string or null — e.g. 51.4567,-0.1912"
  }},
  "guide": {{"affiliation": "string or null — organisation only, never a person's name"}},
  "walk": {{
    "distance_km": "number or null", "duration_approx": "string or null",
    "start_point": "string", "end_point": "string", "route_summary": "string — one sentence"
  }},
  "stops": [{{
    "name": "string", "type": "string — building, park, street, bridge, pub, church, viewpoint…",
    "description": "string — one sentence for caption use", "date_built": "string or null",
    "historical_period": "string or null", "notable_associations": ["string"]
  }}],
  "getty_keywords": {{
    "subjects": ["string"], "concepts": ["string"], "historical_figures": ["string — full names"],
    "architectural_styles": ["string"], "time_periods": ["string"], "events": ["string"]
  }},
  "caption_context": {{
    "borough_or_region": "string", "primary_theme": "string", "secondary_themes": ["string"],
    "suggested_caption_prefix": "string — reusable opening phrase for captions from this walk"
  }},
  "vocabulary": {{
    "confirmed_spellings": ["string"], "local_terms": ["string — 'term: definition'"]
  }},
  "walk_meta": {{
    "date": "YYYY-MM-DD — same as above; if not stated, null",
    "place": "a place code from the list below; if none fits, 'london/<area>', 'uk/<county>' or 'abroad/<country>' in lowercase",
    "location_label": "string — e.g. 'SE London · Sydenham Hill Wood, SE26' or 'Sirmione · Lake Garda, Lombardy, Italy'",
    "themes": ["1–3 theme codes from the list below — only the ones the walk is really about"],
    "series": ["series codes from the list below if the walk was part of one, else empty"],
    "subtitle": "string — '<Tour name> · <organiser>' as known; no personal names",
    "excerpt": "string — 2–3 sentences, the hook of the walk, in the voice of the post",
    "search": "string — lowercase space-separated keywords: places, streets, postcodes, historical figures, organisations; no guide or private names"
  }}
}}

Place codes:
{place_list}

Theme codes:
{theme_list}

Series codes:
{series_list}"""

print("Generating metadata sidecar…")
raw = strip_fences(call(
    JSON_SYSTEM,
    f"Slug: {SLUG}\n\nNotes:\n<notes>\n{notes}\n</notes>",
    effort="medium",
))
try:
    data = json.loads(raw)
except json.JSONDecodeError as e:
    with open(JSON_PATH + ".raw", "w", encoding="utf-8") as f:
        f.write(raw)
    sys.exit(f"Sidecar JSON did not parse ({e}); raw output saved to {JSON_PATH}.raw")
data["slug"] = SLUG

meta = data.pop("walk_meta", {}) or {}
meta["date"] = meta.get("date") or data.get("date") or date.today().isoformat()
h1 = re.search(r"<h1[^>]*>(.*?)</h1>", post_html, re.S)
meta["title_html"] = re.sub(r"\s*<br\s*/?>\s*", " ", h1.group(1)).strip() if h1 else SLUG
post_html = re.sub(r'<script type="application/json" id="walk-meta">.*?</script>\n?', "", post_html, flags=re.S)
post_html = post_html.replace("</head>", walk_meta_block(meta) + "</head>", 1)
post_html = finalise_post(SLUG, post_html, meta.get("excerpt", ""))

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"Sidecar written: {JSON_PATH}")

with open(POST_PATH, "w", encoding="utf-8") as f:
    f.write(post_html if post_html.endswith("\n") else post_html + "\n")
print(f"Post written: {POST_PATH}")
