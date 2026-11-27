# On Foot blog

How the site is built: see `README.md`. Don't edit `index.html` by hand; it is generated from `.github/templates/index.html`.

This blog is one of several linked projects; Getty Images sales come first. Cross-project priorities, open decisions and the backlog live in the hub: https://github.com/gpmdyg9b4z-spec/knowledge-base/tree/main/hub. Read `hub/backlog.md` before larger changes, and update it when you finish one.

- British English, direct tone.
- Never name guides, volunteers or members of the public.
- Every photo should link to its Getty Images page. A photo without one is a submission to chase.
- Run `python3 .github/scripts/build_site.py` after changing posts, and check that it reports no unexpected changes.
