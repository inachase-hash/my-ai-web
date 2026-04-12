"""RSS feed URLs and per-source ranking weights (higher = more trusted / prominent)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FeedSource:
    url: str
    name: str
    weight: float


# HTML listing (see artificial_analysis.py); site has no stable public RSS at /feed.
ARTIFICIAL_ANALYSIS_LISTING_URL = "https://artificialanalysis.ai/articles"
ARTIFICIAL_ANALYSIS_NAME = "Artificial Analysis"
ARTIFICIAL_ANALYSIS_WEIGHT = 1.08

FEEDS: tuple[FeedSource, ...] = (
    FeedSource(
        # Official site feed; FeedBurner often returns HTML/errors to non-browser clients (XML parse fails).
        url="https://www.oreilly.com/radar/feed/",
        name="O'Reilly Radar",
        weight=1.0,
    ),
    FeedSource(
        url="https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        name="The Verge (AI)",
        weight=1.1,
    ),
    FeedSource(
        url="https://techcrunch.com/tag/artificial-intelligence/feed/",
        name="TechCrunch (AI)",
        weight=1.15,
    ),
    FeedSource(
        url="https://huggingface.co/blog/feed.xml",
        name="Hugging Face Blog",
        weight=1.05,
    ),
)
