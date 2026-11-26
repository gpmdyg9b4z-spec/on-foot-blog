# On Foot — Walking Tour Notes

A static blog written up from walking tour notes via GitHub Actions + Claude API.

## How it works

The homepage (`index.html`) and the "More walks" links at the foot of each post are **generated** from the posts by `.github/scripts/build_site.py`. Don't edit `index.html` by hand; change `.github/templates/index.html` instead.

Every post carries a small data block in its `<head>` that drives its homepage card, the filters and the related-walk links:

```html
<script type="application/json" id="walk-meta">
{
 "date": "2026-08-01",
 "place": "uk/sussex",
 "location_label": "Hastings Old Town · East Sussex",
 "title_html": "Nets, Tar &amp; the <em>Ghost of Dunkirk</em>",
 "subtitle": "The Stade Historic Fishing Quarter Walk · Old Hastings Preservation Society",
 "excerpt": "Two or three sentences for the homepage card and link previews.",
 "themes": ["water", "industry", "war"],
 "series": [],
 "search": "lowercase keywords places people organisations"
}
</script>
```

- `place`: `london/central`, `london/n`, `london/nw`, `london/e`, `london/se`, `london/sw`, `london/w`, `uk/<county>` or `abroad/<country>`.
- `themes` (1–3): `architecture`, `regeneration`, `industry`, `water`, `nature`, `faith`, `migration`, `war`, `ancient`, `medieval`, `science`, `arts`, `empire`, `activism`, `food`.
- `series`: `open-house`, `lfa`, `open-city`, `free-tours`, or empty.

Labels for these codes live in `.github/scripts/onfoot.py`; a new code works straight away and can be given a nicer label there.

### Two ways to add a walk

**Upload a finished post** to `_posts/` (include the data block above). On push to `main`, the Action rebuilds the homepage and walk links and commits the result. A post without a data block still appears, at the bottom, with a warning in the Action log.

**Or push your notes** to `_notes/<slug>.txt`. The Action sends it to Claude, which writes the post (using the newest post as its template), the data block, and a metadata sidecar in `_data/<slug>.json` for Getty captioning; then it rebuilds the site. To regenerate a post, run the workflow manually from the **Actions** tab with its slug.

To build locally: `python .github/scripts/build_site.py` from the repo root.

After adding photos, run `python3 .github/scripts/make_variants.py` (macOS, uses `sips`) before building. It writes 800px and 1200px copies next to each 1600px photo and adds `srcset`, so phones download a smaller file.

## Setup

### 1. Add your Anthropic API key as a repo secret

Go to **Settings → Secrets and variables → Actions → New repository secret**

- Name: `ANTHROPIC_API_KEY`
- Value: your key from console.anthropic.com

### 2. Enable GitHub Pages

Go to **Settings → Pages**

- Source: `Deploy from a branch`
- Branch: `main`, folder: `/ (root)`

Your blog will be live at `https://gpmdyg9b4z-spec.github.io/on-foot-blog/`

### 3. Push your notes

Name your file descriptively — the filename becomes the post slug and URL:

```
_notes/wandsworth-lfa-2026.txt   →   _posts/wandsworth-lfa-2026.html
_notes/hampstead-garden-suburb.txt →  _posts/hampstead-garden-suburb.html
```

The Action infers the title, organiser, location, date, and route from the notes. Guides and members of the public are not named in posts.

## File structure

```
_notes/           ← drop .txt notes here
_posts/           ← posts (hand-uploaded or written by the Action)
_data/            ← Getty metadata sidecars written by the Action
assets/post.css   ← shared post styles; a post's own <style> holds only overrides
images/           ← web-sized photos for posts (see "Photographs" below)
index.html        ← homepage (generated — edit .github/templates/index.html)
about.html        ← about page (edit manually)
.github/
  workflows/
    generate-post.yml   ← the Action
  scripts/
    generate_post.py    ← calls the Claude API, writes post HTML + sidecar
    build_site.py       ← builds index.html and the "More walks" links from the posts
    make_variants.py    ← 800/1200px photo copies + srcset (run locally after adding photos)
    onfoot.py           ← shared helpers and the theme/place/series vocabularies
  templates/
    index.html          ← homepage template
```

## Photographs

Posts can carry photos styled by `assets/post.css`. Put a web-sized copy (about 1600px on the long edge) in `images/<slug>/` and link it to its Getty Images page:

```html
<figure class="photo">
  <img src="../images/<slug>/<file>.jpg" alt="Describe the picture" loading="lazy" width="1600" height="1067">
  <figcaption>Caption text.
    <a class="photo-licence" href="https://www.gettyimages.co.uk/detail/news-photo/…">Licence on Getty Images</a>
  </figcaption>
</figure>
```

Use `class="photo wide"` to let an image run wider than the text column.

Put the credit before the link: `<span class="photo-credit">Sergio Amiti / Getty Images</span>`. Add `og:image` (the lead photo) to the post's `<head>` so shared links show it.

The homepage card shows the post's first photo. If `images/<slug>/card.jpg` exists (960×640), it is used instead, which keeps the homepage light. Photos and card thumbnails ignore right-click, drag and long-press, which deters casual saving but cannot prevent screenshots.

## Notes tips

- Rough notes work fine — Claude tidies them up
- The fuller the notes, the better the post
- No need to add metadata — location, distance etc. are inferred
