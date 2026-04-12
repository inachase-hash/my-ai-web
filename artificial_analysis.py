"""Fetch article cards from Artificial Analysis (no public RSS on /feed).

Listing: https://artificialanalysis.ai/articles — each card is <a href="/articles/...">
with the title in the following <img alt="...">.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from rss_sources import (
    ARTIFICIAL_ANALYSIS_LISTING_URL,
    ARTIFICIAL_ANALYSIS_NAME,
    ARTIFICIAL_ANALYSIS_WEIGHT,
)

# <a ... href="/articles/slug"> ... first <img alt="Title"
_CARD_RE = re.compile(
    r'href="(/articles/(?!page-)[^"#]+)"[^>]*>'
    r'(?:[^<]|<(?!/?img\b))*?'
    r'<img\b[^>]*\salt="([^"]*)"',
    re.IGNORECASE | re.DOTALL,
)

if TYPE_CHECKING:
    from utils import Article

# Drop junk paths mistaken for articles (image dimensions, long hex blobs, etc.)
_SLUG_BAD = re.compile(r"^\d+x\d+$|^[a-f0-9-]{24,}$")
_HAS_LETTERS = re.compile(r"[a-zA-Z]")


def _slug_ok(slug: str) -> bool:
    if not slug or len(slug) < 3:
        return False
    if _SLUG_BAD.search(slug):
        return False
    if re.search(r"\d+x\d+", slug):
        return False
    if not _HAS_LETTERS.search(slug):
        return False
    return True


def fetch_artificial_analysis_articles() -> list["Article"]:
    """Return Article rows from the /articles listing. Empty list on failure."""
    # Import here: avoids circular import at module load (utils imports this lazily).
    from utils import Article, _fetch_feed_bytes

    raw = _fetch_feed_bytes(ARTIFICIAL_ANALYSIS_LISTING_URL)
    if raw is None:
        return []

    try:
        html = raw.decode("utf-8", errors="replace")
    except Exception:
        return []

    seen_paths: set[str] = set()
    pairs: list[tuple[str, str]] = []
    for m in _CARD_RE.finditer(html):
        path = m.group(1)
        if path in seen_paths:
            continue
        seen_paths.add(path)
        slug = path.rsplit("/", 1)[-1]
        if not _slug_ok(slug):
            continue
        alt = (m.group(2) or "").strip()
        title = alt if alt else slug.replace("-", " ").title()
        pairs.append((path, title))

    if not pairs:
        print(f"[warn] No Artificial Analysis articles parsed from {ARTIFICIAL_ANALYSIS_LISTING_URL}")
        return []

    base = datetime.now(timezone.utc)
    articles: list[Article] = []
    for i, (path, title) in enumerate(pairs):
        link = f"https://artificialanalysis.ai{path}"
        dt = base - timedelta(minutes=i * 40)
        articles.append(
            Article(
                title=title,
                link=link,
                source=ARTIFICIAL_ANALYSIS_NAME,
                date=dt,
                summary="",
                source_weight=ARTIFICIAL_ANALYSIS_WEIGHT,
            )
        )
    return articles
