# The Daily Diff

A small, opinionated daily reading list for engineers: papers, technical essays, and unusually good project write-ups.

Live site: https://devraj0901.github.io/daily-diff/

## Editorial rule

The site publishes only items that are new since the previous edition and worth a focused read. Each item must link to the primary source, explain why it matters, and avoid hype or invented claims.

The publisher runs daily at **08:00 IST**. It gathers candidates from technical RSS feeds, reviews them, updates `site/data/stories.json`, and pushes the change. GitHub Pages deploys automatically on every push to `main`.

## Local preview

```bash
python3 -m http.server 8000 --directory site
```

Then open http://localhost:8000.

## Repository layout

- `site/` — dependency-free static site
- `site/data/stories.json` — published editions and story metadata
- `scripts/collect_candidates.py` — RSS candidate collector used by the scheduled publisher
- `AGENTS.md` — publishing contract for the scheduled agent
- `.github/workflows/pages.yml` — GitHub Pages deployment
