# On Foot — Walking Tour Notes

A static blog generated from walking tour transcripts via GitHub Actions + Claude API.

## How it works

1. Drop one or more `.txt` transcripts into `_transcripts/`
2. Push to `main`
3. The GitHub Action sends each new or changed transcript to Claude, using the most recent post on the homepage as the template
4. Claude writes the post to `_posts/<slug>.html` and a metadata sidecar to `_data/<slug>.json` (Getty captioning context plus the homepage card text)
5. A card for the post is inserted into `index.html` in date order — the rest of the hand-edited index is left alone
6. Changes are committed back to `main`

To regenerate a post, run the workflow manually from the **Actions** tab and give it the slug. Hand-written posts can be uploaded straight to `_posts/` as before; add their card to `index.html` by hand.

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

### 3. Push a transcript

Name your file descriptively — the filename becomes the post slug and URL:

```
_transcripts/wandsworth-lfa-2026.txt   →   _posts/wandsworth-lfa-2026.html
_transcripts/hampstead-garden-suburb.txt →  _posts/hampstead-garden-suburb.html
```

The Action infers the title, guide name, location, date, and route from the transcript content.

## File structure

```
_transcripts/     ← drop .txt transcripts here
_posts/           ← posts (hand-uploaded or written by the Action)
_data/            ← per-post metadata sidecars written by the Action
assets/post.css   ← shared post styles; a post's own <style> holds only overrides
images/           ← web-sized photos for posts (see "Photographs" below)
index.html        ← homepage (hand-edited; the Action only inserts cards)
about.html        ← about page (edit manually)
.github/
  workflows/
    generate-post.yml   ← the Action
  scripts/
    generate_post.py    ← calls the Claude API, writes post HTML + sidecar
    update_index.py     ← inserts a card for a post into index.html
    onfoot.py           ← shared helpers (nav bar, meta tags)
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

## Transcript tips

- Raw audio transcripts work fine — Claude cleans up transcription errors
- The longer and richer the transcript, the better the post
- No need to add metadata — guide name, location, distance etc. are inferred
