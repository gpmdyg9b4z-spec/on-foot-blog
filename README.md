# On Foot — Walking Tour Notes

A static blog generated from walking tour transcripts via GitHub Actions + Claude API.

## How it works

1. Drop a `.txt` transcript into `_transcripts/`
2. Push to `main`
3. GitHub Action fires, sends the transcript to Claude
4. Claude generates a formatted HTML post in `_posts/`
5. `index.html` is regenerated automatically
6. Changes are committed back to the repo

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
_posts/           ← generated HTML posts (committed by Action)
index.html        ← auto-regenerated blog index
about.html        ← static about page (edit manually)
.github/
  workflows/
    generate-post.yml   ← the Action
  scripts/
    generate_post.py    ← calls Claude API, writes post HTML
    update_index.py     ← rebuilds index.html from _posts/
```

## Transcript tips

- Raw audio transcripts work fine — Claude cleans up transcription errors
- The longer and richer the transcript, the better the post
- No need to add metadata — guide name, location, distance etc. are inferred
