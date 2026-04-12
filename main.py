#!/usr/bin/env python3
"""Fetch AI news from RSS, dedupe, rank, save JSON, and render static HTML."""

from __future__ import annotations

import json
from pathlib import Path

from generate_html import generate_from_json_file
from utils import (
    articles_to_json_list,
    deduplicate_articles,
    fetch_all_articles,
    rank_and_top,
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
NEWS_JSON = DATA_DIR / "news.json"
INDEX_HTML = OUTPUT_DIR / "index.html"


def main() -> None:
    print("Fetching RSS feeds…")
    articles = fetch_all_articles()
    print(f"Total raw entries: {len(articles)}")

    articles = deduplicate_articles(articles)
    print(f"After deduplication: {len(articles)}")

    top = rank_and_top(articles, limit=20)
    payload = articles_to_json_list(top)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    NEWS_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {NEWS_JSON} ({len(payload)} articles)")

    generate_from_json_file(NEWS_JSON, INDEX_HTML)
    print(f"Wrote {INDEX_HTML}")


if __name__ == "__main__":
    main()
