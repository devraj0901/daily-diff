#!/usr/bin/env python3
"""Collect fresh candidates for the Daily Diff publisher.

This is deliberately deterministic. Editorial selection and summarisation happen
in the scheduled agent after it reads the primary sources. The source mix is
intentionally broader than academic feeds: practical Reddit discussions gathered
through Camofox MCP and GitHub Trending projects are useful idea-discovery signals,
not automatic picks. Reddit is intentionally not fetched here; Camofox MCP is the
sole Reddit adapter.
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
from html.parser import HTMLParser
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
UA = "daily-diff-candidate-collector/1.1 (+https://devraj0901.github.io/daily-diff/)"


class TrendingParser(HTMLParser):
    """Extract repository cards from GitHub's public Trending HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.in_article = False
        self.in_heading = False
        self.in_description = False
        self.heading = []
        self.description = []
        self.href = ""
        self.language = ""
        self.stars_today = ""
        self.items: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class", "") or ""
        if tag == "article" and "Box-row" in classes:
            self.in_article = True
            self.heading = []
            self.description = []
            self.href = ""
            self.language = ""
            self.stars_today = ""
        elif self.in_article and tag == "h2":
            self.in_heading = True
        elif self.in_article and tag == "a" and self.in_heading:
            self.href = attributes.get("href", "") or ""
        elif self.in_article and tag == "p":
            self.in_description = True

    def handle_data(self, data: str) -> None:
        if self.in_heading:
            self.heading.append(data)
        elif self.in_description:
            self.description.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2":
            self.in_heading = False
        elif tag == "p":
            self.in_description = False
        elif tag == "article" and self.in_article:
            title = " ".join("".join(self.heading).split())
            if title and self.href:
                url = urllib.parse.urljoin("https://github.com", self.href)
                self.items.append({
                    "title": title,
                    "url": url,
                    "summary": " ".join("".join(self.description).split())[:1200],
                })
            self.in_article = False


def parse_github_trending(payload: bytes) -> list[dict]:
    parser = TrendingParser()
    parser.feed(payload.decode("utf-8", "replace"))
    return parser.items

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


def get_github_trending() -> bytes:
    request = urllib.request.Request(
        "https://github.com/trending",
        headers={"User-Agent": UA, "Accept": "text/html"},
    )
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
    try:
        for item in parse_github_trending(get_github_trending())[:20]:
            candidates.append({
                "title": item["title"],
                "url": item["url"],
                "source": "GitHub Trending",
                "feed": "https://github.com/trending",
                "published_at": None,
                "discovered_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                "summary": item["summary"],
                "author": "",
            })
    except Exception as exc:  # discovery source failure should not stop RSS
        errors.append(f"GitHub Trending: {exc}")
    unique = {}
    for item in candidates:
        canonical = item["url"].split("#", 1)[0]
        item["url"] = canonical
        if canonical in seen or canonical in unique:
            continue
        published = parse_date(item.get("published_at"))
        discovered = parse_date(item.get("discovered_at"))
        freshness = published or discovered
        if published:
            item["published_at"] = published
        if discovered:
            item["discovered_at"] = discovered
        if freshness:
            if dt.datetime.fromisoformat(freshness.replace("Z", "+00:00")) <= last_dt:
                continue
        unique[canonical] = item
    # Keep discovery sources in the candidate set. Reddit is supplied by the
    # scheduled agent through Camofox MCP; GitHub Trending has a
    # discovery timestamp rather than an article publication timestamp, so it
    # is still eligible for the publisher's new-only cutoff.
    ordered = sorted(
        unique.values(),
        key=lambda item: item.get("published_at") or item.get("discovered_at") or "",
        reverse=True,
    )[:140]
    output = {"last_published_at": state.get("last_published_at"), "candidate_count": len(ordered), "candidates": ordered, "feed_errors": errors}
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
