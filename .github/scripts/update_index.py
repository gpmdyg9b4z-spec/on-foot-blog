#!/usr/bin/env python3
"""
Add (or refresh) homepage cards in index.html for the given post slugs.

index.html is hand-maintained, so this script edits it in place rather than
regenerating it: it removes any existing card for the slug, builds a new card
from the post and its _data/<slug>.json sidecar, inserts it in date order,
adds a filter button for any new location or theme, and updates the post count.

Usage: python update_index.py <slug> [<slug> ...]   (or SLUGS="a b" in the environment)
"""

import html
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from onfoot import index_vocabulary  # noqa: E402

INDEX = "index.html"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CARD_RE = re.compile(r'\n?[ \t]*<a class="post-card" href="_posts/([^"]+)\.html".*?</a>\n', re.S)
e = lambda t: html.escape(t or "", quote=True)


def card_date(card: str):
    m = re.search(r'<span class="date-day">(\d+)</span><span class="date-monthyear">(\w{3}) (\d{4})</span>', card)
    if not m:
        return date.min
    return date(int(m.group(3)), MONTHS.index(m.group(2)) + 1, int(m.group(1)))


def inner(html_text: str, pattern: str) -> str:
    m = re.search(pattern, html_text, re.S)
    return m.group(1).strip() if m else ""


def build_card(slug: str) -> tuple[str, date, dict]:
    post = open(f"_posts/{slug}.html", encoding="utf-8").read()
    sidecar_path = f"_data/{slug}.json"
    if not os.path.exists(sidecar_path):
        sys.exit(f"No sidecar at {sidecar_path}; run generate_post.py first.")
    data = json.load(open(sidecar_path, encoding="utf-8"))
    card = data.get("index_card") or {}

    try:
        d = date.fromisoformat(data.get("date") or "")
    except ValueError:
        d = date.today()
        print(f"  {slug}: no date in transcript, using today ({d}) — edit the card if that's wrong.")

    title = re.sub(r"\s*<br\s*/?>\s*", " ", inner(post, r"<h1[^>]*>(.*?)</h1>"))
    subtitle = inner(post, r'<div class="header-sub">(.*?)</div>')
    themes = [t.lower() for t in card.get("themes", [])][:5]
    tags = "".join(f'<span class="tag">{e(t.title())}</span>' for t in themes)

    html_card = f'''
      <a class="post-card" href="_posts/{slug}.html" data-location="{e(card.get("location_code", ""))}" data-themes="{e(" ".join(themes))}" data-search="{e(card.get("search", "").lower())}">
        <div class="post-date"><span class="date-day">{d.day}</span><span class="date-monthyear">{MONTHS[d.month - 1]} {d.year}</span></div>
        <div class="post-body">
          <div class="post-location-label">{e(card.get("location_label", ""))}</div>
          <div class="post-title">{title}</div>
          <div class="post-subtitle">{subtitle}</div>
          <div class="post-excerpt">{e(card.get("excerpt", ""))}</div>
          <div class="post-meta">{tags}<span class="read-link">Read &rarr;</span></div>
        </div>
      </a>
'''
    return html_card, d, card


def add_filter_button(index: str, group: str, value: str, label: str) -> str:
    btn = f'        <button class="filter-btn" data-filter="{group}" data-value="{e(value)}">{e(label)}</button>\n'
    block = re.search(rf'(<div class="filter-buttons" id="{group}-filters">.*?)(\s*</div>)', index, re.S)
    return index[:block.end(1)] + "\n" + btn.rstrip("\n") + index[block.end(1):]


def main(slugs):
    index = open(INDEX, encoding="utf-8").read()
    for slug in slugs:
        new_card, d, meta = build_card(slug)
        # drop an existing card for this slug
        index = re.sub(rf'\n?[ \t]*<a class="post-card" href="_posts/{re.escape(slug)}\.html".*?</a>\n',
                       "\n", index, count=1, flags=re.S)
        # insert before the first card that is older
        pos = None
        for m in CARD_RE.finditer(index):
            if card_date(m.group(0)) < d:
                pos = m.start()
                break
        if pos is None:
            last = list(CARD_RE.finditer(index))
            pos = last[-1].end() if last else index.index('<div class="posts-list" id="posts-list">') + len('<div class="posts-list" id="posts-list">\n')
        index = index[:pos] + new_card.rstrip("\n") + "\n" + index[pos:]

        locs, themes = index_vocabulary(index)
        code = meta.get("location_code", "")
        if code and code not in {v for v, _ in locs}:
            index = add_filter_button(index, "location", code, meta.get("location_button") or code.title())
            print(f"  added location filter: {code}")
        for t in [t.lower() for t in meta.get("themes", [])]:
            if t not in {v for v, _ in themes}:
                index = add_filter_button(index, "theme", t, t.title())
                themes.append((t, t.title()))
                print(f"  added theme filter: {t}")
        print(f"Card added: {slug} ({d})")

    n = len(CARD_RE.findall(index))
    index = re.sub(r'(<div class="results-count" id="results-count">)\d+ posts?(</div>)',
                   lambda m: f"{m.group(1)}{n} {'post' if n == 1 else 'posts'}{m.group(2)}", index, count=1)
    open(INDEX, "w", encoding="utf-8").write(index)


if __name__ == "__main__":
    slugs = sys.argv[1:] or os.environ.get("SLUGS", "").split()
    if not slugs:
        sys.exit("Usage: update_index.py <slug> [<slug> ...]")
    main(slugs)
