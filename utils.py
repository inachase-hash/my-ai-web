"""Fetch RSS feeds, normalize entries, deduplicate, rank, and serialize for output."""

from __future__ import annotations

import html
import math
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser

from rss_sources import FEEDS, FeedSource

# Many CDNs / FeedBurner block or HTML-wrap default clients; XML then fails with "not well-formed".
_FEED_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; rv:128.0) Gecko/20100101 Firefox/128.0 "
        "AI-News-Aggregator/1.0"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.1",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    unescaped = html.unescape(text)
    plain = _TAG_RE.sub(" ", unescaped)
    return _WS_RE.sub(" ", plain).strip()


def _normalize_title_key(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    return _WS_RE.sub(" ", t).strip()


def _title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _entry_datetime(entry: dict[str, Any]) -> datetime | None:
    if entry.get("published_parsed"):
        try:
            t = entry["published_parsed"]
            return datetime(*t[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    if entry.get("updated_parsed"):
        try:
            t = entry["updated_parsed"]
            return datetime(*t[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    raw = entry.get("published") or entry.get("updated")
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError):
            pass
    return None


def _format_date_iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recency_score(dt: datetime | None, now: datetime) -> float:
    """Higher = more recent. Decays by half every ~3.5 days."""
    if dt is None:
        return 0.0
    age_hours = max(0.0, (now - dt.astimezone(timezone.utc)).total_seconds() / 3600.0)
    half_life_hours = 84.0  # ~3.5 days
    return math.exp(-math.log(2) * age_hours / half_life_hours)


@dataclass
class Article:
    title: str
    link: str
    source: str
    date: datetime | None
    summary: str
    source_weight: float

    def to_json_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "link": self.link,
            "source": self.source,
            "date": _format_date_iso(self.date),
            "summary": self.summary,
        }

    def rank_score(self, now: datetime) -> float:
        return _recency_score(self.date, now) * 10.0 + self.source_weight


def _fetch_feed_bytes(url: str, timeout_s: int = 30) -> bytes | None:
    req = urllib.request.Request(url, headers=_FEED_REQUEST_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        print(f"[warn] HTTP {exc.code} fetching {url}")
        return None
    except urllib.error.URLError as exc:
        print(f"[warn] Network error fetching {url}: {exc.reason}")
        return None
    except OSError as exc:
        print(f"[warn] Failed to fetch {url}: {exc}")
        return None


def _parse_feed(source: FeedSource) -> list[Article]:
    articles: list[Article] = []
    raw = _fetch_feed_bytes(source.url)
    if raw is None:
        return articles
    try:
        parsed = feedparser.parse(raw)
    except Exception as exc:  # noqa: BLE001 — RSS fetch must not crash the run
        print(f"[warn] Failed to parse feed {source.name} ({source.url}): {exc}")
        return articles

    if getattr(parsed, "bozo", False) and not getattr(parsed, "entries", None):
        bozo_msg = getattr(parsed, "bozo_exception", None)
        print(f"[warn] Feed may be malformed: {source.name} — {bozo_msg}")
        return articles

    for entry in getattr(parsed, "entries", []) or []:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or entry.get("id") or "").strip()
        if not title or not link:
            continue
        raw_summary = entry.get("summary") or entry.get("description") or ""
        summary = _strip_html(raw_summary)
        if len(summary) > 2000:
            summary = summary[:1997] + "..."
        dt = _entry_datetime(entry)
        articles.append(
            Article(
                title=title,
                link=link,
                source=source.name,
                date=dt,
                summary=summary,
                source_weight=source.weight,
            )
        )
    return articles


def fetch_all_articles() -> list[Article]:
    all_items: list[Article] = []
    for src in FEEDS:
        try:
            items = _parse_feed(src)
            all_items.extend(items)
            print(f"[ok] {src.name}: {len(items)} entries")
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] Unexpected error for {src.name}: {exc}")

    try:
        from artificial_analysis import fetch_artificial_analysis_articles

        aa_items = fetch_artificial_analysis_articles()
        all_items.extend(aa_items)
        print(f"[ok] Artificial Analysis: {len(aa_items)} entries")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Unexpected error for Artificial Analysis: {exc}")

    return all_items


def deduplicate_articles(articles: list[Article], similarity_threshold: float = 0.88) -> list[Article]:
    """Drop duplicates: exact normalized title, then fuzzy title match vs kept items."""
    kept: list[Article] = []
    seen_keys: set[str] = set()
    norm_titles: list[tuple[str, Article]] = []

    for art in articles:
        key = _normalize_title_key(art.title)
        if key in seen_keys:
            continue
        dup = False
        for norm, existing in norm_titles:
            if _title_similarity(key, norm) >= similarity_threshold:
                dup = True
                break
        if dup:
            continue
        seen_keys.add(key)
        norm_titles.append((key, art))
        kept.append(art)
    return kept


def rank_and_top(articles: list[Article], limit: int = 20) -> list[Article]:
    now = datetime.now(timezone.utc)
    scored = sorted(articles, key=lambda a: a.rank_score(now), reverse=True)
    return scored[:limit]


def articles_to_json_list(articles: list[Article]) -> list[dict[str, str]]:
    return [a.to_json_dict() for a in articles]
