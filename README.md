# AI News Aggregator

A small Python tool that pulls AI-related headlines from several RSS feeds, removes near-duplicate titles, ranks items by recency and source weight, then writes `data/news.json` and a static `output/index.html`.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

This will:

1. Fetch all configured feeds (failures are logged; other feeds still run).
2. Normalize entries and drop duplicates (exact normalized title + fuzzy title match).
3. Rank by recency (exponential decay) and source weight, keep the top 20.
4. Save `data/news.json`.
5. Generate `output/index.html` (links to `output/styles.css` and `output/app.js`).

Open `output/index.html` in a browser to view the page. **Favorites** (star on each article) are saved in **localStorage** in your browser and persist across refreshes; keep `app.js` and `styles.css` next to `index.html` so relative URLs work.

## Project layout

- `main.py` — entrypoint.
- `rss_sources.py` — feed URLs, display names, and weights.
- `utils.py` — fetch, parse, dedupe, rank.
- `generate_html.py` — JSON → static HTML.
- `data/news.json` — latest article list (overwritten each run).
- `output/index.html` — rendered page (overwritten each run).
- `output/styles.css` — page styles (not overwritten by `main.py`).
- `output/app.js` — favorites UI (localStorage; not overwritten by `main.py`).
- `output/github-config.example.js` — template for optional GitHub sync (copy to `github-config.local.js`).

### Optional: sync favorites to GitHub

Favorites stay in **localStorage** first. To mirror them to `favorites.json` in repo [`inachase-hash/my-ai-web`](https://github.com/inachase-hash/my-ai-web):

1. Copy `output/github-config.example.js` to `output/github-config.local.js` (this path is listed in `.gitignore`).
2. Set `window.__GITHUB_FAVORITES_TOKEN__` to a fine-scoped PAT (`repo` scope for that repository). **Do not commit the token.** If a token was ever pasted into chat or committed, **revoke it in GitHub** and create a new one.
3. Open the page over **HTTPS** (e.g. GitHub Pages). The GitHub REST API may fail from `file://` or some origins (**CORS**); if sync fails, the UI falls back to local-only and shows a short status under Favorites.

## Requirements

- Python 3.9+ recommended (uses built-in type hints like `list[str]` / `tuple[...]`).
