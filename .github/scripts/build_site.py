#!/usr/bin/env python3
"""
Build the site from the posts.

Each post carries a <script type="application/json" id="walk-meta"> block with its
date, place, themes, series and card text. From those this script:
  1. writes index.html from .github/templates/index.html (cards, filters, counts);
  2. writes a "More walks" block (previous/next and related walks) at the foot of each post;
  3. makes sure each post has the shared stylesheet, nav bar and meta tags.

Run from the repo root:  python .github/scripts/build_site.py
It is safe to run repeatedly; it only rewrites files whose content changes.
"""

import glob
import html
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from onfoot import (PLACE_GROUPS, PLACES, SERIES, SITE_URL, THEMES,  # noqa: E402
                    finalise_post, label, read_walk_meta)

TEMPLATE = ".github/templates/index.html"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
e = lambda t: html.escape(t or "", quote=True)
warnings = []


def load_walks():
    walks = []
    for path in sorted(glob.glob("_posts/*.html")):
        slug = os.path.basename(path)[:-5]
        if slug == "index":
            continue
        page = open(path, encoding="utf-8").read()
        meta = read_walk_meta(page)
        if meta is None:
            side = f"_data/{slug}.json"
            if os.path.exists(side):
                meta = json.load(open(side, encoding="utf-8")).get("walk_meta")
        if meta is None:
            warnings.append(f"{slug}: no walk-meta block — shown with defaults; add one to place it properly.")
            h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
            sub = re.search(r'<div class="header-sub">(.*?)</div>', page, re.S)
            meta = {"date": "1900-01-01", "place": "", "location_label": "", "themes": [], "series": [],
                    "title_html": re.sub(r"\s*<br\s*/?>\s*", " ", h1.group(1)).strip() if h1 else slug,
                    "subtitle": html.unescape(re.sub(r"<[^>]+>", "", sub.group(1))).strip() if sub else "",
                    "excerpt": "", "search": ""}
        meta["slug"] = slug
        meta["lead_photo"] = lead_photo(slug, page)
        meta["title_html"] = re.sub(r"\s*<br\s*/?>\s*", " ", meta.get("title_html", slug))
        walks.append(meta)
    for side in glob.glob("_data/*.json"):
        slug = os.path.basename(side)[:-5]
        if not os.path.exists(f"_posts/{slug}.html") and "walk_meta" in json.load(open(side, encoding="utf-8")):
            warnings.append(f"{slug}: card data saved in {side} but the post isn't in _posts/ — not listed.")
    walks.sort(key=lambda w: (w["date"], w["slug"]), reverse=True)
    return walks


def lead_photo(slug, page):
    """The post's first photo, for its homepage card: (src, alt), preferring images/<slug>/card.jpg."""
    m = re.search(r'<figure class="photo[^"]*"[^>]*>\s*<img src="\.\./(images/[^"]+)"[^>]*? alt="([^"]*)"', page)
    if not m:
        return None
    card = f"images/{slug}/card.jpg"
    return (card if os.path.exists(card) else m.group(1)), m.group(2)


def fmt_date(iso):
    y, m, d = iso.split("-")
    return int(d), f"{MONTHS[int(m) - 1]} {y}"


def card_html(w):
    day, monthyear = fmt_date(w["date"])
    tags = "".join(f'<span class="tag">{e(label(THEMES, t))}</span>' for t in w.get("themes", []))
    photo = w.get("lead_photo")
    thumb = (f'\n        <img class="post-thumb" src="{photo[0]}" alt="" loading="lazy" width="480" height="320">'
             if photo else "")
    cls = "post-card has-photo" if photo else "post-card"
    return f'''      <a class="{cls}" href="_posts/{w["slug"]}.html" data-place="{e(w.get("place"))}" data-themes="{e(" ".join(w.get("themes", [])))}" data-series="{e(" ".join(w.get("series", [])))}" data-search="{e(w.get("search", "").lower())}">
        <div class="post-date"><span class="date-day">{day}</span><span class="date-monthyear">{monthyear}</span></div>{thumb}
        <div class="post-body">
          <div class="post-location-label">{e(w.get("location_label"))}</div>
          <h2 class="post-title">{w["title_html"]}</h2>
          <div class="post-subtitle">{e(w.get("subtitle"))}</div>
          <div class="post-excerpt">{e(w.get("excerpt"))}</div>
          <div class="post-meta">{tags}<span class="read-link">Read &rarr;</span></div>
        </div>
      </a>'''


def button(filter_, value, text, n, active=False):
    cls = "filter-btn active" if active else "filter-btn"
    return f'          <button class="{cls}" data-filter="{filter_}" data-value="{e(value)}"><span>{e(text)}</span><span class="n">{n}</span></button>'


def filters_html(walks):
    total = len(walks)
    places = Counter(w.get("place", "") for w in walks)
    groups = Counter(p.split("/")[0] for p in places.elements() if p)
    out = ['      <div class="sidebar-section">', '        <span class="sidebar-label">Where</span>',
           '        <div class="filter-buttons">', button("place", "", "Everywhere", total, True)]
    for g in list(PLACE_GROUPS) + sorted(set(groups) - set(PLACE_GROUPS)):
        if not groups[g]:
            continue
        out.append(f'          <span class="filter-sub">{e(label(PLACE_GROUPS, g))}</span>')
        out.append(button("place", g, {"london": "All London", "uk": "All rest of UK", "abroad": "All abroad"}.get(g, "All"), groups[g]))
        subs = sorted((p for p in places if p.startswith(g + "/")),
                      key=lambda p: (list(PLACES).index(p) if p in PLACES else 99, label(PLACES, p)))
        out += [button("place", p, label(PLACES, p), places[p]) for p in subs]
    out += ["        </div>", "      </div>"]

    themes = Counter(t for w in walks for t in w.get("themes", []))
    out += ['      <div class="sidebar-section">', '        <span class="sidebar-label">Theme</span>',
            '        <div class="filter-buttons">', button("theme", "", "All themes", total, True)]
    out += [button("theme", t, label(THEMES, t), n)
            for t, n in sorted(themes.items(), key=lambda kv: label(THEMES, kv[0]))]
    out += ["        </div>", "      </div>"]

    series = Counter(s for w in walks for s in w.get("series", []))
    if series:
        out += ['      <div class="sidebar-section">', '        <span class="sidebar-label">Organised by</span>',
                '        <div class="filter-buttons">', button("series", "", "Anyone", total, True)]
        out += [button("series", s, label(SERIES, s), n)
                for s, n in sorted(series.items(), key=lambda kv: label(SERIES, kv[0]))]
        out += ["        </div>", "      </div>"]
    return "\n".join(out)


def related(w, walks, exclude):
    def score(o):
        s = 2 * len(set(w.get("themes", [])) & set(o.get("themes", [])))
        if w.get("place") and o.get("place") == w.get("place"):
            s += 3
        elif w.get("place") and o.get("place", "").split("/")[0] == w["place"].split("/")[0]:
            s += 1
        s += len(set(w.get("series", [])) & set(o.get("series", [])))
        return s
    pool = [o for o in walks if o["slug"] not in exclude]
    pool.sort(key=lambda o: (score(o), o["date"]), reverse=True)
    return [o for o in pool[:3] if score(o) > 0]


def link(o, kicker, cls=""):
    c = f' class="{cls}"' if cls else ""
    return (f'<a href="{o["slug"]}.html"{c}><span class="walk-kicker">{kicker}</span>'
            f'<span class="walk-name">{o["title_html"]}</span>'
            f'<span class="walk-where">{e(o.get("location_label"))}</span></a>')


def walk_links_html(i, walks):
    w = walks[i]
    newer = walks[i - 1] if i > 0 else None
    older = walks[i + 1] if i + 1 < len(walks) else None
    pn = []
    if older:
        pn.append(link(older, "&larr; Previous walk", "prev"))
    if newer:
        pn.append(link(newer, "Next walk &rarr;", "next"))
    rel = related(w, walks, {w["slug"]} | {o["slug"] for o in (newer, older) if o})
    parts = ["<!-- walk-links: generated by build_site.py, do not edit -->",
             '<aside class="walk-links" aria-label="More walks">',
             "  <h2>More walks</h2>"]
    if pn:
        parts.append('  <nav class="walk-pn">' + "".join(pn) + "</nav>")
    if rel:
        parts.append('  <div class="walk-related">' + "".join(link(o, "Related") for o in rel) + "</div>")
    parts += ['  <a class="walk-index" href="../index.html">All walks &rarr;</a>', "</aside>",
              "<!-- /walk-links -->"]
    return "\n".join(parts) + "\n"


def write_if_changed(path, text):
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    if old != text:
        open(path, "w", encoding="utf-8").write(text)
        return True
    return False


def main():
    walks = load_walks()
    changed = []

    tpl = open(TEMPLATE, encoding="utf-8").read()
    index = (tpl.replace("{{SITE_URL}}", SITE_URL)
                .replace("{{FILTERS}}", filters_html(walks))
                .replace("{{CARDS}}", "\n\n".join(card_html(w) for w in walks))
                .replace("{{COUNT}}", str(len(walks))))
    if write_if_changed("index.html", index):
        changed.append("index.html")

    for i, w in enumerate(walks):
        path = f"_posts/{w['slug']}.html"
        page = open(path, encoding="utf-8").read()
        page = finalise_post(w["slug"], page, w.get("excerpt", ""))
        block = walk_links_html(i, walks)
        page, n = re.subn(r"<!-- walk-links:.*?<!-- /walk-links -->\n?", lambda m: block, page, count=1, flags=re.S)
        if not n:
            page, n = re.subn(r"(\n?<footer)", lambda m: "\n" + block + m.group(1).lstrip("\n"), page, count=1)
            if not n:
                page = page.replace("</body>", block + "</body>", 1)
        if write_if_changed(path, page):
            changed.append(path)


    print(f"{len(walks)} walks; {len(changed)} files updated.")
    for c in changed:
        print("  updated", c)
    for w_ in warnings:
        print("  note:", w_)


if __name__ == "__main__":
    main()
