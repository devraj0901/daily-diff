#!/usr/bin/env python3
"""Collect fresh RSS candidates for the Daily Diff publisher.

This is deliberately deterministic. Editorial selection and summarisation happen
in the scheduled agent after it reads the primary sources.
"""
from __future__ import annotations
import datetime as dt
import email.utils
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "publisher-state.json"
FEEDS = [
    ("HN", "https://hnrss.org/frontpage?points=50"),
    ("Lobsters", "https://lobste.rs/rss"),
    ("arXiv", "https://export.arxiv.org/rss/cs.AI"),
    ("arXiv", "https://export.arxiv.org/rss/cs.LG"),
    ("arXiv", "https://export.arxiv.org/rss/cs.DB"),
    ("arXiv", "https://export.arxiv.org/rss/cs.SE"),
]
UA = "daily-diff-candidate-collector/1.0 (+https://devraj0901.github.io/daily-diff/)"

def parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    try:
        value = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            value = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

def text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())

def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, text/xml"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()

def parse_feed(source: str, feed_url: str, payload: bytes) -> list[dict]:
    root = ET.fromstring(payload)
    entries = root.findall(".//item")
    atom = False
    if not entries:
        atom = True
        entries = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "entry"]
    results = []
    for item in entries:
        def child(name: str) -> ET.Element | None:
            for node in list(item):
                if node.tag.rsplit("}", 1)[-1] == name:
                    return node
            return None
        title = text(child("title"))
        link_node = child("link")
        link = ""
        if link_node is not None:
            link = link_node.attrib.get("href", "") or text(link_node)
        if atom and not link:
            for node in list(item):
                if node.tag.rsplit("}", 1)[-1] == "link" and node.attrib.get("href"):
                    link = node.attrib["href"]
                    break
        date = parse_date(text(child("pubDate")) or text(child("published")) or text(child("updated")))
        summary = text(child("description")) or text(child("summary"))
        summary = re.sub(r"https?://\S+", "", summary).strip()
        author = text(child("author")) or text(child("creator"))
        if title and link:
            results.append({"title": title, "url": link, "source": source, "feed": feed_url, "published_at": date, "summary": summary[:1200], "author": author})
    return results

def main() -> int:
    try:
        state = json.loads(STATE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    seen = set(state.get("published_urls", []))
    last = parse_date(state.get("last_published_at"))
    last_dt = dt.datetime.fromisoformat(last.replace("Z", "+00:00")) if last else dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3)
    candidates: list[dict] = []
    errors = []
    for source, url in FEEDS:
        try:
            candidates.extend(parse_feed(source, url, get(url)))
        except Exception as exc:  # network/feed failures should not stop other feeds
            errors.append(f"{source}: {exc}")
    unique = {}
    for item in candidates:
        canonical = item["url"].split("#", 1)[0]
        item["url"] = canonical
        if canonical in seen or canonical in unique:
            continue
        published = parse_date(item.get("published_at"))
        if published:
            item["published_at"] = published
            if dt.datetime.fromisoformat(published.replace("Z", "+00:00")) <= last_dt:
                continue
        unique[canonical] = item
    ordered = sorted(unique.values(), key=lambda item: item.get("published_at") or "", reverse=True)[:80]
    output = {"last_published_at": state.get("last_published_at"), "candidate_count": len(ordered), "candidates": ordered, "feed_errors": errors}
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
