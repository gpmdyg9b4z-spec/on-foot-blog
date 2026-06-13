#!/usr/bin/env python3
"""
Scan _posts/ and _data/ and regenerate index.html with
client-side search, area filters (London subdivided by postal district),
city filters, and theme filters.
All filter data is embedded as JSON in the page — no server required.
"""

import os
import re
import json
import glob
from datetime import datetime

POST_DIR = "_posts"
DATA_DIR = "_data"
INDEX_PATH = "index.html"

# London postal prefix → human-readable area label
LONDON_AREAS = {
    "EC": "City & East",
    "WC": "City & East",
    "E":  "East London",
    "N":  "North London",
    "NW": "North-West London",
    "W":  "West London",
    "SW": "South-West London",
    "SE": "South-East London",
    "BR": "South-East London",
    "CR": "South London",
}

def postal_to_area(postal):
    """Convert a postal district like SW18 to a London area label."""
    if not postal:
        return None
    postal = postal.strip().upper()
    for prefix in sorted(LONDON_AREAS.keys(), key=len, reverse=True):
        if postal.startswith(prefix):
            return LONDON_AREAS[prefix]
    return None

def load_json_sidecar(slug):
    path = os.path.join(DATA_DIR, f"{slug}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def extract_meta(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    slug = os.path.basename(filepath).replace(".html", "")
    sidecar = load_json_sidecar(slug)

    # ── From HTML ──
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
    title = re.sub(r'<[^>]+>', ' ', title_match.group(1)).strip() if title_match else slug.replace("-", " ").title()
    title = re.sub(r'\s+', ' ', title).strip()

    sub_match = re.search(r'class="header-sub"[^>]*>(.*?)</div>', content, re.DOTALL)
    subtitle = re.sub(r'<[^>]+>', '', sub_match.group(1)).strip() if sub_match else ""

    p_match = re.search(r'<p>(.*?)</p>', content, re.DOTALL)
    excerpt_raw = p_match.group(1) if p_match else ""
    excerpt = re.sub(r'<[^>]+>', '', excerpt_raw).strip()
    if len(excerpt) > 200:
        excerpt = excerpt[:200].rsplit(' ', 1)[0] + "…"

    # ── From JSON sidecar ──
    loc = sidecar.get("location", {})
    city = loc.get("city", "")
    postal = loc.get("postal_district", "")
    country = loc.get("country", "")

    # Determine location label for display
    if city.lower() == "london":
        area = postal_to_area(postal)
        location_label = f"London · {area}" if area else "London"
        filter_city = f"London · {area}" if area else "London"
    elif city:
        location_label = f"{city}, {country}" if country else city
        filter_city = city
    else:
        location_label = ""
        filter_city = ""

    # Themes from JSON secondary_themes + primary_theme
    caption_ctx = sidecar.get("caption_context", {})
    themes = []
    primary = caption_ctx.get("primary_theme", "")
    if primary:
        themes.append(primary)
    themes += caption_ctx.get("secondary_themes", [])
    # Deduplicate preserving order
    seen = set()
    themes_clean = []
    for t in themes:
        if t and t.lower() not in seen:
            seen.add(t.lower())
            themes_clean.append(t)

    # Date — prefer JSON, fall back to file mtime
    date_str = sidecar.get("date")
    if date_str:
        try:
            date = datetime.fromisoformat(date_str)
        except Exception:
            date = datetime.fromtimestamp(os.path.getmtime(filepath))
    else:
        date = datetime.fromtimestamp(os.path.getmtime(filepath))

    # Walk stats
    walk = sidecar.get("walk", {})
    distance = walk.get("distance_km")
    distance_str = f"{distance} km" if distance else ""

    return {
        "slug": slug,
        "title": title,
        "subtitle": subtitle,
        "excerpt": excerpt,
        "location_label": location_label,
        "filter_city": filter_city,
        "themes": themes_clean,
        "date": date,
        "distance": distance_str,
        "path": f"_posts/{os.path.basename(filepath)}",
        # Search blob — all text Claude can match against
        "search_text": " ".join([
            title, subtitle, excerpt, location_label,
            city, postal, " ".join(themes_clean),
            sidecar.get("caption_context", {}).get("suggested_caption_prefix", ""),
            " ".join(sidecar.get("vocabulary", {}).get("confirmed_spellings", []))
        ]).lower()
    }


# ── Load all posts ──
posts = []
for fp in sorted(glob.glob(f"{POST_DIR}/*.html"), key=os.path.getmtime, reverse=True):
    try:
        posts.append(extract_meta(fp))
    except Exception as e:
        print(f"Warning: could not parse {fp}: {e}")

# ── Collect filter options ──
all_cities = sorted(set(p["filter_city"] for p in posts if p["filter_city"]))
all_themes = sorted(set(t for p in posts for t in p["themes"]))

# Separate London areas from other cities
london_areas = sorted(set(
    p["filter_city"] for p in posts
    if p["filter_city"].startswith("London")
))
other_cities = sorted(set(
    p["filter_city"] for p in posts
    if p["filter_city"] and not p["filter_city"].startswith("London")
))

# ── Serialise posts for JS ──
posts_json = json.dumps([
    {
        "slug": p["slug"],
        "title": p["title"],
        "subtitle": p["subtitle"],
        "excerpt": p["excerpt"],
        "location_label": p["location_label"],
        "filter_city": p["filter_city"],
        "themes": p["themes"],
        "date_day": p["date"].strftime("%d"),
        "date_month": p["date"].strftime("%b").upper(),
        "date_year": p["date"].strftime("%Y"),
        "distance": p["distance"],
        "path": p["path"],
        "search_text": p["search_text"]
    }
    for p in posts
], indent=2, ensure_ascii=False)

london_areas_json = json.dumps(london_areas)
other_cities_json = json.dumps(other_cities)
all_themes_json = json.dumps(all_themes)

index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>On Foot — Walking Tour Notes</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Overpass+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
  :root {{
    --ink: #141218; --paper: #f4f0e6; --aged: #e6dcc8;
    --sepia: #7a6045; --crimson: #8c1f28; --gold: #a8832a; --ash: #635c52;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: var(--paper); color: var(--ink); font-family: 'EB Garamond', Georgia, serif; font-size: 18px; line-height: 1.75; min-height: 100vh; display: flex; flex-direction: column; }}
  body::before {{ content: ''; position: fixed; inset: 0; background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E"); pointer-events: none; z-index: 100; }}

  header {{ background: var(--ink); color: var(--paper); padding: 4rem 2rem 3rem; text-align: center; position: relative; overflow: hidden; }}
  header::before {{ content: '✦'; position: absolute; font-size: 20rem; opacity: 0.03; top: 50%; left: 50%; transform: translate(-50%,-50%); color: var(--gold); line-height: 1; }}
  .masthead-label {{ font-family: 'Overpass Mono', monospace; font-size: 0.65rem; letter-spacing: 0.3em; text-transform: uppercase; color: var(--gold); margin-bottom: 1rem; }}
  header h1 {{ font-family: 'Cormorant Garamond', serif; font-size: clamp(2.5rem,7vw,4.5rem); font-weight: 300; line-height: 1.1; margin-bottom: 0.5rem; }}
  header h1 em {{ font-style: italic; color: var(--gold); }}
  .masthead-sub {{ font-style: italic; font-size: 1.05rem; color: #a08870; }}

  nav.site-nav {{ background: #1e1a16; padding: 0.6rem 2rem; display: flex; gap: 2rem; font-family: 'Overpass Mono', monospace; font-size: 0.65rem; letter-spacing: 0.2em; text-transform: uppercase; }}
  nav.site-nav a {{ color: var(--ash); text-decoration: none; }}
  nav.site-nav a:hover {{ color: var(--gold); }}

  .controls {{ max-width: 780px; margin: 2.5rem auto 0; padding: 0 2rem; }}

  .search-wrap {{ position: relative; margin-bottom: 1.5rem; }}
  .search-wrap input {{ width: 100%; background: var(--aged); border: 1px solid #c4b898; padding: 0.65rem 1rem 0.65rem 2.4rem; font-family: 'EB Garamond', Georgia, serif; font-size: 1rem; color: var(--ink); outline: none; }}
  .search-wrap input:focus {{ border-color: var(--sepia); }}
  .search-wrap::before {{ content: '⌕'; position: absolute; left: 0.75rem; top: 50%; transform: translateY(-50%); color: var(--ash); font-size: 1.1rem; pointer-events: none; }}

  .filter-group {{ margin-bottom: 1rem; }}
  .filter-label {{ font-family: 'Overpass Mono', monospace; font-size: 0.58rem; letter-spacing: 0.25em; text-transform: uppercase; color: var(--ash); margin-bottom: 0.5rem; display: block; }}
  .filter-buttons {{ display: flex; flex-wrap: wrap; gap: 0.4rem; }}
  .filter-btn {{ font-family: 'Overpass Mono', monospace; font-size: 0.58rem; letter-spacing: 0.12em; text-transform: uppercase; padding: 0.3rem 0.7rem; border: 1px solid #c4b898; background: transparent; color: var(--ash); cursor: pointer; transition: all 0.15s; }}
  .filter-btn:hover {{ border-color: var(--sepia); color: var(--sepia); }}
  .filter-btn.active {{ background: var(--ink); color: var(--gold); border-color: var(--ink); }}

  .filter-divider {{ width: 1px; background: #c4b898; margin: 0 0.3rem; align-self: stretch; }}

  main {{ max-width: 780px; margin: 0 auto; padding: 2rem 2rem 6rem; flex: 1; }}

  .results-count {{ font-family: 'Overpass Mono', monospace; font-size: 0.62rem; letter-spacing: 0.25em; text-transform: uppercase; color: var(--ash); border-bottom: 1px solid var(--aged); padding-bottom: 0.5rem; margin-bottom: 2rem; }}

  .post-card {{ display: grid; grid-template-columns: 80px 1fr; gap: 0 2rem; padding: 2rem 0; border-bottom: 1px solid var(--aged); text-decoration: none; color: inherit; transition: background 0.12s; }}
  .post-card:hover {{ background: var(--aged); margin: 0 -1.5rem; padding: 2rem 1.5rem; }}
  .post-card.hidden {{ display: none; }}

  .post-date-block {{ text-align: center; padding-top: 0.3rem; }}
  .post-date-day {{ font-family: 'Cormorant Garamond', serif; font-size: 2.2rem; font-weight: 300; color: var(--sepia); line-height: 1; }}
  .post-date-month {{ font-family: 'Overpass Mono', monospace; font-size: 0.58rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--sepia); }}
  .post-date-year {{ font-family: 'Overpass Mono', monospace; font-size: 0.55rem; color: var(--ash); }}

  .post-location {{ font-family: 'Overpass Mono', monospace; font-size: 0.58rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold); margin-bottom: 0.25rem; }}
  .post-title {{ font-family: 'Cormorant Garamond', serif; font-size: 1.55rem; font-weight: 300; line-height: 1.2; color: var(--ink); margin-bottom: 0.2rem; }}
  .post-subtitle {{ font-style: italic; font-size: 0.95rem; color: var(--sepia); margin-bottom: 0.45rem; }}
  .post-excerpt {{ font-size: 0.88rem; color: var(--ash); line-height: 1.5; margin-bottom: 0.5rem; }}
  .post-tags {{ display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.4rem; }}
  .post-tag {{ font-family: 'Overpass Mono', monospace; font-size: 0.52rem; letter-spacing: 0.1em; text-transform: uppercase; border: 1px solid #c4b898; padding: 0.15rem 0.45rem; color: var(--ash); }}
  .post-read-more {{ font-family: 'Overpass Mono', monospace; font-size: 0.6rem; letter-spacing: 0.2em; text-transform: uppercase; color: var(--crimson); }}

  .no-results {{ font-style: italic; color: var(--ash); padding: 2rem 0; }}

  footer {{ background: var(--ink); color: #6b6459; text-align: center; padding: 2rem; font-family: 'Overpass Mono', monospace; font-size: 0.62rem; letter-spacing: 0.15em; }}
  footer span {{ color: var(--gold); }}

  @media (max-width: 520px) {{
    .post-card {{ grid-template-columns: 60px 1fr; gap: 0 1rem; }}
    .post-date-day {{ font-size: 1.6rem; }}
    .controls {{ padding: 0 1rem; }}
    main {{ padding: 1.5rem 1rem 4rem; }}
  }}
</style>
</head>
<body>

<header>
  <p class="masthead-label">A personal record of guided walks</p>
  <h1>On <em>Foot</em></h1>
  <p class="masthead-sub">Notes from the street, the square &amp; the river&rsquo;s edge</p>
</header>

<nav class="site-nav">
  <a href="index.html">All Walks</a>
  <a href="about.html">About</a>
</nav>

<div class="controls">

  <div class="search-wrap">
    <input type="text" id="search" placeholder="Search walks, places, themes…" autocomplete="off">
  </div>

  <div class="filter-group" id="location-filters">
    <span class="filter-label">Location</span>
    <div class="filter-buttons" id="location-btn-group">
      <button class="filter-btn active" data-filter-location="">All</button>
    </div>
  </div>

  <div class="filter-group" id="theme-filters">
    <span class="filter-label">Theme</span>
    <div class="filter-buttons" id="theme-btn-group">
      <button class="filter-btn active" data-filter-theme="">All</button>
    </div>
  </div>

</div>

<main>
  <p class="results-count" id="results-count"></p>
  <div id="post-list"></div>
  <p class="no-results hidden" id="no-results">No walks match your search.</p>
</main>

<footer>
  <span>On Foot</span> &mdash; Walking Tour Notes &mdash; Est. 2026
</footer>

<script>
const POSTS = {posts_json};
const LONDON_AREAS = {london_areas_json};
const OTHER_CITIES = {other_cities_json};
const ALL_THEMES = {all_themes_json};

// ── Build location filter buttons ──
const locGroup = document.getElementById('location-btn-group');

if (LONDON_AREAS.length) {{
  const londonLabel = document.createElement('span');
  londonLabel.style.cssText = 'font-family:Overpass Mono,monospace;font-size:0.55rem;letter-spacing:0.15em;text-transform:uppercase;color:var(--sepia);align-self:center;padding:0 0.3rem;';
  londonLabel.textContent = 'London:';
  locGroup.appendChild(londonLabel);

  LONDON_AREAS.forEach(area => {{
    const btn = document.createElement('button');
    btn.className = 'filter-btn';
    btn.dataset.filterLocation = area;
    // Show just the area part after "London · "
    btn.textContent = area.replace('London · ', '');
    locGroup.appendChild(btn);
  }});
}}

if (LONDON_AREAS.length && OTHER_CITIES.length) {{
  const div = document.createElement('div');
  div.className = 'filter-divider';
  locGroup.appendChild(div);
}}

OTHER_CITIES.forEach(city => {{
  const btn = document.createElement('button');
  btn.className = 'filter-btn';
  btn.dataset.filterLocation = city;
  btn.textContent = city;
  locGroup.appendChild(btn);
}});

// ── Build theme filter buttons ──
const themeGroup = document.getElementById('theme-btn-group');
ALL_THEMES.forEach(theme => {{
  const btn = document.createElement('button');
  btn.className = 'filter-btn';
  btn.dataset.filterTheme = theme;
  btn.textContent = theme;
  themeGroup.appendChild(btn);
}});

// ── Render post cards ──
function renderCard(p) {{
  const tags = p.themes.slice(0, 4).map(t =>
    `<span class="post-tag">${{t}}</span>`).join('');
  return `
    <a class="post-card" href="${{p.path}}" data-city="${{p.filter_city}}" data-themes="${{p.themes.join('|')}}">
      <div class="post-date-block">
        <div class="post-date-day">${{p.date_day}}</div>
        <div class="post-date-month">${{p.date_month}}</div>
        <div class="post-date-year">${{p.date_year}}</div>
      </div>
      <div>
        <p class="post-location">${{p.location_label}}${{p.distance ? ' &middot; ' + p.distance : ''}}</p>
        <h2 class="post-title">${{p.title}}</h2>
        <p class="post-subtitle">${{p.subtitle}}</p>
        <p class="post-excerpt">${{p.excerpt}}</p>
        ${{tags ? `<div class="post-tags">${{tags}}</div>` : ''}}
        <span class="post-read-more">Read &rarr;</span>
      </div>
    </a>`;
}}

const listEl = document.getElementById('post-list');
listEl.innerHTML = POSTS.map(renderCard).join('');

// ── Filter state ──
let activeLocation = '';
let activeTheme = '';
let searchQuery = '';

function applyFilters() {{
  const cards = listEl.querySelectorAll('.post-card');
  let visible = 0;

  cards.forEach(card => {{
    const city = card.dataset.city || '';
    const themes = card.dataset.themes || '';
    const slug = card.getAttribute('href').replace('_posts/','').replace('.html','');
    const post = POSTS.find(p => p.slug === slug);
    const searchText = post ? post.search_text : '';

    const locMatch = !activeLocation || city === activeLocation;
    const themeMatch = !activeTheme || themes.split('|').includes(activeTheme);
    const searchMatch = !searchQuery || searchText.includes(searchQuery.toLowerCase());

    if (locMatch && themeMatch && searchMatch) {{
      card.classList.remove('hidden');
      visible++;
    }} else {{
      card.classList.add('hidden');
    }}
  }});

  document.getElementById('results-count').textContent =
    visible === POSTS.length
      ? `All Walks — ${{POSTS.length}} ${{POSTS.length === 1 ? 'post' : 'posts'}}`
      : `${{visible}} of ${{POSTS.length}} walks`;

  document.getElementById('no-results').classList.toggle('hidden', visible > 0);
}}

// ── Location filter clicks ──
document.getElementById('location-btn-group').addEventListener('click', e => {{
  const btn = e.target.closest('.filter-btn');
  if (!btn) return;
  document.querySelectorAll('[data-filter-location]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeLocation = btn.dataset.filterLocation;
  applyFilters();
}});

// ── Theme filter clicks ──
document.getElementById('theme-btn-group').addEventListener('click', e => {{
  const btn = e.target.closest('.filter-btn');
  if (!btn) return;
  document.querySelectorAll('[data-filter-theme]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeTheme = btn.dataset.filterTheme;
  applyFilters();
}});

// ── Search ──
document.getElementById('search').addEventListener('input', e => {{
  searchQuery = e.target.value.trim();
  applyFilters();
}});

// ── Init ──
applyFilters();
</script>

</body>
</html>"""

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(index_html)

print(f"Index written: {len(posts)} posts, {len(london_areas)} London areas, {len(other_cities)} other cities, {len(all_themes)} themes.")
