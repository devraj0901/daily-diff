# Daily Diff publishing contract

You are the scheduled publisher for `devraj0901/daily-diff`. Work directly in this repository.

## Every run

1. Read `site/data/stories.json` and `publisher-state.json` before changing anything.
2. Inspect the candidate JSON injected by `scripts/collect_candidates.py`.
3. Publish **only** candidates newer than the last published edition and not already in `published_urls`.
4. Use web extraction/search to read the primary article, paper, or project page before writing copy. Do not infer technical details from an RSS title alone.
5. Select at most 8 items. Prefer deep technical writing, reproducible research, important open-source internals, systems work, security, databases, programming languages, and practical AI engineering. Exclude press releases, generic listicles, shallow opinion, duplicate coverage, and marketing copy.
6. Write concise, factual copy. `dek` is one sentence. `why` is 1–2 sentences explaining who benefits and what the reader will learn. `takeaway` is one concrete engineering insight. Never invent metrics, authors, dates, or claims.
7. Preserve the canonical source URL. Add a discussion URL only when the candidate provides one (usually Hacker News).
8. Update `site/data/stories.json` and `publisher-state.json` atomically enough that a failed run does not mark unpublished items as seen.
9. If there are no genuinely good new items, make no content commit. A quiet edition is better than filler.
10. If content changed, run the validation commands below, then commit and push to `main`.

## Story schema

```json
{
  "id": "stable-slug",
  "title": "Canonical title",
  "dek": "One-sentence description.",
  "why": "Why this is worth a focused read.",
  "takeaway": "One concrete engineering takeaway.",
  "source": "HN | arXiv | Lobsters | Blog | GitHub | Other",
  "source_url": "https://...",
  "discussion_url": "https://...",
  "authors": ["Author"],
  "published_at": "2026-08-03T00:00:00Z",
  "tags": ["systems", "ai"],
  "read_minutes": 12
}
```

`discussion_url`, `authors`, `tags`, and `read_minutes` may be omitted or empty when unavailable. Keep all stories in the `stories` array, newest first. Set `generated_at` and `edition_date` on every successful content update.

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
