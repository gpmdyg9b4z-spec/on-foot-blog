"""Shared helpers for the On Foot build scripts: site constants, post chrome
(navigation bar, meta tags) and the theme/location vocabularies used by the index."""

import html
import os
import re

SITE_URL = "https://gpmdyg9b4z-spec.github.io/on-foot-blog"
SITE_NAME = "On Foot — Walking Tour Notes"
MODEL = "claude-opus-5-5"


def nav_html(slug: str) -> str:
    """Standard top bar for a post: back to index, optional language switch, About."""
    if slug.endswith("-it"):
        base = slug[:-3]
        return ('<nav class="home-nav"><a class="home-link" href="../index.html">On Foot</a>'
                '<span class="home-title">Appunti di camminate guidate</span><span class="home-links">'
                f'<a href="{base}.html" hreflang="en" lang="en">English</a>'
                '<a href="../about.html">Chi sono</a></span></nav>')
    italian = (f'<a href="{slug}-it.html" hreflang="it" lang="it">Italiano</a>'
               if os.path.exists(f"_posts/{slug}-it.html") else "")
    return ('<nav class="home-nav"><a class="home-link" href="../index.html">On Foot</a>'
            '<span class="home-title">Walking Tour Notes</span><span class="home-links">'
            f'{italian}<a href="../about.html">About</a></span></nav>')


def trim_description(text: str, limit: int = 170) -> str:
    text = " ".join(html.unescape(re.sub(r"<[^>]+>", "", text)).split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:—–- ") + "…"


def meta_tags(slug: str, title: str, description: str) -> str:
    e = lambda t: html.escape(t, quote=True)
    url = f"{SITE_URL}/_posts/{slug}.html"
    d = trim_description(description)
    tags = [
        f'<meta name="description" content="{e(d)}">',
        f'<link rel="canonical" href="{url}">',
        f'<meta property="og:site_name" content="{SITE_NAME}">',
        '<meta property="og:type" content="article">',
        f'<meta property="og:title" content="{e(title)}">',
        f'<meta property="og:description" content="{e(d)}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:locale" content="{"it_IT" if slug.endswith("-it") else "en_GB"}">',
        '<meta name="twitter:card" content="summary">',
    ]
    return "\n".join(tags)


def finalise_post(slug: str, page: str, description: str) -> str:
    """Make a generated page conform to the site: shared stylesheet, nav bar,
    en-GB language tag and meta/Open Graph tags. Safe to run more than once."""
    if 'href="../assets/post.css"' not in page:
        page = re.sub(r"(</title>\n?)", r'\1<link rel="stylesheet" href="../assets/post.css">\n', page, count=1)
    page = re.sub(r'<html lang="en">', '<html lang="en-GB">', page, count=1)
    nav = nav_html(slug)
    old_nav = re.compile(r'<(nav|div) class="home-nav">.*?</\1>', re.S)
    if old_nav.search(page):
        page = old_nav.sub(lambda m: nav, page, count=1)
    else:
        page = re.sub(r"(<body[^>]*>\n?)", lambda m: m.group(1) + nav + "\n", page, count=1)
    if 'name="description"' not in page:
        title_m = re.search(r"<title>(.*?)</title>", page, re.S)
        title = html.unescape(title_m.group(1).strip()) if title_m else slug
        page = re.sub(r"(<title>.*?</title>\n?)", lambda m: m.group(1) + meta_tags(slug, title, description) + "\n",
                      page, count=1, flags=re.S)
    return page


def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def index_vocabulary(index_html: str):
    """Return the location and theme filter values already on the index page."""
    locs = re.findall(r'data-filter="location" data-value="([^"]+)">([^<]+)</button>', index_html)
    themes = re.findall(r'data-filter="theme" data-value="([^"]+)">([^<]+)</button>', index_html)
    return locs, themes


# ─── Vocabularies for filters ────────────────────────────────────────────────
# Codes are stored in each post's walk-meta block; labels are what readers see.
# Add new codes here; an unknown code still works and is shown title-cased.

THEMES = {
    "architecture": "Architecture",
    "regeneration": "Housing & regeneration",
    "industry": "Industry & trade",
    "water": "Rivers & coast",
    "nature": "Nature & gardens",
    "faith": "Faith",
    "migration": "Migration",
    "war": "War & conflict",
    "ancient": "Roman & ancient",
    "medieval": "Medieval & Tudor",
    "science": "Science & engineering",
    "arts": "Arts, books & film",
    "empire": "Empire",
    "activism": "Protest & community",
    "food": "Food & drink",
}

SERIES = {
    "open-house": "Open House",
    "lfa": "London Festival of Architecture",
    "open-city": "Open City tours",
    "free-tours": "Free walking tours",
}

PLACE_GROUPS = {"london": "London", "uk": "Rest of UK", "abroad": "Abroad"}
PLACES = {
    "london/central": "Central", "london/n": "North", "london/nw": "North-west",
    "london/e": "East", "london/se": "South-east", "london/sw": "South-west", "london/w": "West",
    "uk/sussex": "East Sussex", "uk/essex": "Essex",
}


def label(vocab: dict, code: str) -> str:
    return vocab.get(code) or code.split("/")[-1].replace("-", " ").title()


def read_walk_meta(page: str):
    """Return the JSON walk-meta block embedded in a post, or None."""
    import json
    m = re.search(r'<script type="application/json" id="walk-meta">(.*?)</script>', page, re.S)
    return json.loads(m.group(1)) if m else None


def walk_meta_block(meta: dict) -> str:
    import json
    return ('<script type="application/json" id="walk-meta">\n'
            + json.dumps(meta, ensure_ascii=False, indent=1) + "\n</script>\n")
