#!/usr/bin/env python3
"""Make smaller copies of post photos and point each <img> at them with srcset.

For every photo in _posts/*.html (images/<slug>/<name>.jpg, about 1600px), this writes
<name>-800.jpg and <name>-1200.jpg next to it and adds srcset/sizes to the <img> tag,
so phones download a 1200px or 800px copy instead of the full 1600px one.

Idempotent: existing variants and tags that already have srcset are left alone.
Uses Pillow where it is installed (the GitHub Action installs it), otherwise macOS `sips`.
The Action runs it on every push, so photos added from any device get their copies.
To run it locally before build_site.py:

    python3 .github/scripts/make_variants.py
"""
import os, re, shutil, subprocess, sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = (800, 1200)
QUALITY = '72'
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


def variant(src, dst, long_edge):
    if dst.exists():
        return
    w, h = dims(src)
    if max(w, h) <= long_edge:
        shutil.copyfile(src, dst)
        return
    if Image:
        with Image.open(src) as im:
            keep = {k: im.info[k] for k in ('exif', 'icc_profile', 'xmp') if im.info.get(k)}
            im.thumbnail((long_edge, long_edge), Image.LANCZOS)
            im.save(dst, 'JPEG', quality=int(QUALITY), optimize=True, progressive=True, **keep)
        return
    if not shutil.which('sips'):
        sys.exit('Need Pillow (pip install pillow) or macOS sips to make photo copies.')
    subprocess.run(['sips', '-Z', str(long_edge), '-s', 'formatOptions', QUALITY, str(src), '--out', str(dst)],
                   capture_output=True, check=True)


def main():
    made = changed = 0
    for post in sorted((ROOT / '_posts').glob('*.html')):
        page = post.read_text(encoding='utf-8')

        def fix(m):
            nonlocal made
            head, wide, base, rest, close = m.groups()
            if 'srcset=' in rest:
                # keep sizes in step with the figure's class (a lead may have moved)
                want = SIZES['wide' if wide else 'normal']
                return re.sub(r'sizes="[^"]*"', f'sizes="{want}"', m.group(0))
            src = ROOT / f'{base}.jpg'
            if not src.exists():
                return m.group(0)
            w, h = dims(src)
            parts = []
            for long_edge in WIDTHS:
                dst = ROOT / f'{base}-{long_edge}.jpg'
                existed = dst.exists(); variant(src, dst, long_edge); made += not existed
                vw = round(w * min(1, long_edge / max(w, h)))
                parts.append(f'../{base}-{long_edge}.jpg {vw}w')
            parts.append(f'../{base}.jpg {w}w')
            sizes = SIZES['wide' if wide else 'normal']
            return f'{head} srcset="{", ".join(parts)}" sizes="{sizes}"{rest}{close}'

        new = IMG.sub(fix, page)
        if new != page:
            post.write_text(new, encoding='utf-8'); changed += 1
    print(f'variants written: {made}; posts updated: {changed}')


if __name__ == '__main__':
    sys.exit(main())
