# AI News Aggregator

A small Python tool that pulls AI-related headlines from several RSS feeds, removes near-duplicate titles, ranks items by recency and source weight, then writes `data/news.json` and a static site under **`docs/`** (GitHub Pages–friendly).

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
5. Generate `docs/index.html` (links to `docs/styles.css` and `docs/app.js`).

Open `docs/index.html` in a browser, or use **GitHub Pages** with the **`/docs`** folder on `main` so the site updates whenever you push after `main.py`.

**Favorites** use **localStorage**; keep `app.js` and `styles.css` next to `index.html` in `docs/`.

## Project layout

- `main.py` — entrypoint (writes into `docs/`).
- `rss_sources.py` — feed URLs, display names, and weights.
- `utils.py` — fetch, parse, dedupe, rank.
- `generate_html.py` — JSON → static HTML.
- `data/news.json` — latest article list (overwritten each run).
- `docs/index.html` — rendered page (overwritten each run).
- `docs/styles.css` — page styles (not overwritten by `main.py`).
- `docs/app.js` — favorites UI (localStorage + optional GitHub sync; not overwritten by `main.py`).
- `docs/github-config.example.js` — optional local token template (copy to `github-config.local.js` for file-based dev only).

### Optional: sync favorites to GitHub (`favorites.json`)

Favorites stay in **localStorage**; the app can also read/write [`favorites.json`](https://github.com/inachase-hash/my-ai-web/blob/main/favorites.json) in your repo via the GitHub API.

**On GitHub Pages** (or any HTTPS URL): open **Favorites → “Cross-device sync (GitHub)”**, paste a **personal access token**, click **Save & sync**. The token is stored **only in that browser** (localStorage), not in your repo.

Create a token with permission to update that repo (**classic:** `repo`, or **fine-grained:** Contents read/write on `my-ai-web` only). **Never commit a PAT.** If one was ever exposed, revoke it and make a new token.

Opening the page as a local **`file://`** file may still hit **CORS** limits on the GitHub API; use the HTTPS site for sync.

## Requirements

- Python 3.9+ recommended (uses built-in type hints like `list[str]` / `tuple[...]`).
