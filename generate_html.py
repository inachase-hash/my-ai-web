"""Build a static, mobile-friendly HTML page from news.json."""

from __future__ import annotations

import html
import json
from pathlib import Path


def _trim_summary(text: str, max_len: int = 220) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _attr(value: str) -> str:
    """Escape a string for use in HTML attribute values."""
    return html.escape(value, quote=True)


def generate_html(news: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cards: list[str] = []
    for item in news:
        raw_link = item.get("link") or ""
        raw_title = item.get("title") or ""
        raw_source = item.get("source") or ""
        href = _attr(raw_link) if raw_link else "#"
        data_link = _attr(raw_link)
        data_title = _attr(raw_title)
        data_source = _attr(raw_source)

        title_disp = html.escape(raw_title)
        link = href
        source = html.escape(raw_source)
        raw_date = item.get("date") or ""
        date_attr = _attr(raw_date)
        date_disp = html.escape(raw_date) if raw_date else "—"
        summary_raw = item.get("summary") or ""
        summary = html.escape(_trim_summary(summary_raw))

        cards.append(
            f"""    <article class="card" data-link="{data_link}" data-title="{data_title}" data-source="{data_source}">
      <div class="card-inner">
        <button type="button" class="star-btn" aria-pressed="false" aria-label="Add to favorites">☆</button>
        <div class="card-content">
          <h2 class="title"><a href="{link}" rel="noopener noreferrer">{title_disp}</a></h2>
          <p class="meta"><span class="source">{source}</span><span class="sep">·</span><time datetime="{date_attr}">{date_disp}</time></p>
          <p class="summary">{summary}</p>
        </div>
      </div>
    </article>"""
        )

    if cards:
        cards_html = '<div id="feed">\n' + "\n".join(cards) + "\n    </div>"
    else:
        cards_html = '    <div id="feed">\n    <p class="empty">No articles yet.</p>\n    </div>'

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI News — Aggregated</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="wrap">
    <header>
      <h1>AI News</h1>
      <p class="sub">Top stories from RSS — ranked by recency and source.</p>
    </header>
    <main>
    <section class="favorites-section" aria-labelledby="favorites-heading">
      <h2 class="section-heading" id="favorites-heading">Favorites</h2>
      <p class="sync-status" id="github-sync-status" hidden></p>
      <details class="sync-panel">
        <summary>Cross-device sync (GitHub)</summary>
        <p class="sync-panel-help" id="github-token-status">Add a token below to sync <code>favorites.json</code> in your repo. Stored only in this browser — not on GitHub in the site files.</p>
        <div class="sync-panel-row">
          <input type="password" id="github-token-input" class="sync-token-input" autocomplete="off" placeholder="Fine-grained or classic PAT" aria-label="GitHub personal access token">
          <button type="button" class="sync-btn" id="github-token-save">Save &amp; sync</button>
          <button type="button" class="sync-btn sync-btn-secondary" id="github-token-clear">Remove token</button>
        </div>
      </details>
      <p class="favorites-empty" id="favorites-empty">No favorites yet. Star an article below.</p>
      <div id="favorites-list" class="favorites-list"></div>
    </section>
    <section class="feed-section" aria-labelledby="latest-heading">
      <h2 class="section-heading" id="latest-heading">Latest</h2>
{cards_html}
    </section>
    </main>
    <footer>Favorites in localStorage; optional GitHub sync via the panel above (token never committed). RSS refreshes when you run <code>main.py</code>.</footer>
  </div>
  <script src="app.js" defer></script>
</body>
</html>
"""
    output_path.write_text(doc, encoding="utf-8")


def generate_from_json_file(json_path: Path, output_path: Path) -> None:
    raw = json_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("news.json must contain a JSON array")
    news = [x for x in data if isinstance(x, dict)]
    generate_html(news, output_path)
