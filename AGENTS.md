# Daily Diff publishing contract

You are the scheduled publisher for `devraj0901/daily-diff`. Work directly in this repository.

## Every run

1. Read `site/data/stories.json` and `publisher-state.json` before changing anything.
2. Inspect the candidate JSON injected by `scripts/collect_candidates.py`.
3. Read Karakeep as a separate high-signal source. Use the Karakeep MCP search tool with `is:link` plus an `after:YYYY-MM-DD` cutoff based on `last_published_at`, sorted newest first. Search enough results to cover the interval, then fetch the full markdown for promising bookmarks with the bookmark-content tool. Do not assume the RSS collector includes Karakeep; it does not.
4. Publish **only** candidates newer than the last published edition and not already in `published_urls`. For Karakeep, use the bookmark creation timestamp as the freshness timestamp and its canonical bookmarked URL as `source_url`.
5. Use web extraction/search or the Karakeep bookmark content to read the primary article before writing copy. Do not infer technical details from a title or short summary alone.
6. Select at most **5 items** across all sources. The default edition should be application-oriented: useful tools, project write-ups, workflows, implementation lessons, self-hosted systems, practical AI engineering, and discussions that generate build ideas. Use Reddit and GitHub Trending as discovery sources, then read the linked primary project/article before accepting it. Keep excellent deep technical work eligible, but do not let academic papers, C++, compiler internals, or low-level performance pieces dominate the edition unless they have a clear practical payoff. A healthy mix is usually 2–3 practical/application items, 1 strong technical essay, and 0–2 wildcard ideas. Exclude press releases, generic listicles, shallow opinion, duplicate coverage, and marketing copy. Karakeep items are eligible, not automatic inclusions.
7. Write concise, factual copy. `dek` is one sentence. `why` is 1–2 sentences explaining who benefits and what the reader will learn. `takeaway` is one concrete engineering insight. Never invent metrics, authors, dates, or claims.
8. Preserve the canonical source URL. Add a discussion URL only when the candidate provides one (usually Hacker News).
9. Update `site/data/stories.json` and `publisher-state.json` atomically enough that a failed run does not mark unpublished items as seen.
10. If there are no genuinely good new items, make no content commit. A quiet edition is better than filler.
11. Keep the run bounded: make one Karakeep search covering the cutoff, fetch full content for no more than 4 promising Karakeep bookmarks, and do not retry a stalled source indefinitely. If Karakeep or a primary page is unavailable, continue with the other candidates and report the skipped source.
12. If content changed, run the validation commands below, then commit and push to `main`.

## Story schema

```json
{
  "id": "stable-slug",
  "title": "Canonical title",
  "dek": "One-sentence description.",
  "why": "Why this is worth a focused read.",
  "takeaway": "One concrete engineering takeaway.",
  "source": "HN | arXiv | Lobsters | Reddit | GitHub Trending | Karakeep | Blog | GitHub | Other",
  "source_url": "https://...",
  "discussion_url": "https://...",
  "authors": ["Author"],
  "published_at": "2026-08-03T00:00:00Z",
  "tags": ["systems", "ai"],
  "read_minutes": 12
}
```

`discussion_url`, `authors`, `tags`, and `read_minutes` may be omitted or empty when unavailable. Keep all stories in the `stories` array, newest first. Set `generated_at` and `edition_date` on every successful content update.

Collector candidates from GitHub Trending may contain `discovered_at` instead of `published_at`; treat that as the freshness of the trending signal, but use the repository's real release/publication date in the final story when it is available.

## State schema

```json
{
  "last_published_at": "2026-08-03T00:00:00Z",
  "published_urls": ["https://canonical.example/article"]
}
```

Keep at most 500 URLs in state. Never delete story history from `stories.json` merely to keep the file short.

## Validation

```bash
python3 -m json.tool site/data/stories.json >/dev/null
python3 -m json.tool publisher-state.json >/dev/null
python3 - <<'PY'
import json
p=json.load(open('site/data/stories.json'))
assert isinstance(p['stories'], list)
for s in p['stories']:
    assert s['title'] and s['source_url'] and s['why'] and s['takeaway']
print(f"validated {len(p['stories'])} stories")
PY
```
