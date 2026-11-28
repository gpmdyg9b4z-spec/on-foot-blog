#!/usr/bin/env python3
"""Keep post photos phone-sized, and point each <img> at the right copy with srcset.

For every photo in _posts/*.html (images/<slug>/<name>.jpg):
  - if it is larger than 1200px on the long edge, it is shrunk in place to 1200px,
    so the site never serves a copy big enough to be worth taking instead of licensing;
  - an 800px copy, <name>-800.jpg, is written next to it;
  - the <img> gets srcset/sizes and its real width/height.

Upload whatever size you have; the Action does the rest on every push.
Idempotent: photos already at 1200px and existing 800px copies are left alone.
Uses Pillow where it is installed (the Action installs it), otherwise macOS `sips`.
To run it locally before build_site.py:

    python3 .github/scripts/make_variants.py
"""
import re, shutil, subprocess, sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parents[2]
MAX = 1200          # largest copy the site serves
SMALL = 800         # phone copy
QUALITY = 78        # for the 1200px copy; the 800px copy uses 72
SIZES = {'wide': '(max-width: 860px) calc(100vw - 4rem), 824px',
         'normal': '(max-width: 860px) calc(100vw - 4rem), 696px'}
IMG = re.compile(r'(<figure class="photo( wide)?"[^>]*>\s*<img src="\.\./(images/[^"]+?)\.jpg")([^>]*?)(>)')


def dims(path):
    if Image:
        with Image.open(path) as im:
            return im.size
    out = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', str(path)],
                         capture_output=True, text=True, check=True).stdout
    v = dict(re.findall(r'(pixelWidth|pixelHeight): (\d+)', out))
    return int(v['pixelWidth']), int(v['pixelHeight'])


def resize(src, dst, long_edge, quality):
    """Write src scaled to long_edge (never enlarged) to dst; dst may be src."""
    if Image:
        with Image.open(src) as im:
            keep = {k: im.info[k] for k in ('exif', 'icc_profile', 'xmp') if im.info.get(k)}
            im.load()
            im.thumbnail((long_edge, long_edge), Image.LANCZOS)
            im.save(dst, 'JPEG', quality=quality, optimize=True, progressive=True, **keep)
        return
    if not shutil.which('sips'):
        sys.exit('Need Pillow (pip install pillow) or macOS sips to resize photos.')
    subprocess.run(['sips', '-Z', str(long_edge), '-s', 'formatOptions', str(quality), str(src), '--out', str(dst)],
                   capture_output=True, check=True)


def main():
    shrunk = made = changed = 0
    for post in sorted((ROOT / '_posts').glob('*.html')):
        page = post.read_text(encoding='utf-8')

        def fix(m):
            nonlocal shrunk, made
            head, wide, base, rest, close = m.groups()
            src = ROOT / f'{base}.jpg'
            if not src.exists():
                return m.group(0)
            w, h = dims(src)
            if max(w, h) > MAX:
                old = ROOT / f'{base}-{MAX}.jpg'      # an earlier 1200px copy, if there is one
                if old.exists():
                    old.replace(src)
                else:
                    resize(src, src, MAX, QUALITY)
                shrunk += 1
                w, h = dims(src)
            small = ROOT / f'{base}-{SMALL}.jpg'
            if not small.exists():
                if max(w, h) > SMALL:
                    resize(src, small, SMALL, 72)
                else:
                    shutil.copyfile(src, small)
                made += 1
            sw = round(w * min(1, SMALL / max(w, h)))
            rest = re.sub(r'\s+(srcset|sizes|width|height)="[^"]*"', '', rest)
            sizes = SIZES['wide' if wide else 'normal']
            return (f'{head} srcset="../{base}-{SMALL}.jpg {sw}w, ../{base}.jpg {w}w" sizes="{sizes}"'
                    f'{rest} width="{w}" height="{h}"{close}')

        new = IMG.sub(fix, page)
        if new != page:
            post.write_text(new, encoding='utf-8'); changed += 1
    # copies from the old three-size scheme that nothing uses any more
    stale = [p for p in (ROOT / 'images').glob(f'*/*-{MAX}.jpg')]
    for p in stale:
        p.unlink()
    print(f'shrunk to {MAX}px: {shrunk}; {SMALL}px copies written: {made}; '
          f'old {MAX}px copies removed: {len(stale)}; posts updated: {changed}')


if __name__ == '__main__':
    sys.exit(main())
