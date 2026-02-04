"""
AI Tides - Full text enrichment for news.

This module tries to fetch and extract readable article text from URLs so that
L2/L3 have enough context to judge importance and write summaries.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional
from urllib.parse import urlparse

import requests

from ..models import ContentItem, ContentType, SourceType

logger = logging.getLogger(__name__)


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Tides/1.0; +https://github.com/ai-tides)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _strip_html_to_text(html: str) -> str:
    if not html:
        return ""
    # Remove scripts/styles
    html = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", html)
    html = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", html)
    # Remove tags
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    # Decode basic entities
    html = (
        html.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    # Collapse whitespace
    html = re.sub(r"\s+", " ", html).strip()
    return html


def _extract_with_optional_libs(html: str, url: str) -> str:
    # Prefer trafilatura if installed.
    try:
        import trafilatura  # type: ignore

        extracted = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
        if extracted:
            return re.sub(r"\s+", " ", extracted).strip()
    except Exception:
        pass

    # Fall back to BeautifulSoup if installed.
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return re.sub(r"\s+", " ", text).strip()
    except Exception:
        pass

    return _strip_html_to_text(html)


def _should_fetch(item: ContentItem) -> bool:
    if item.content_type != ContentType.NEWS:
        return False
    if not item.url:
        return False
    # If we already have meaningful text, don't refetch.
    if item.full_text and len(item.full_text.strip()) >= 800:
        return False
    # GitHub trending is not an article; abstract is enough.
    if item.source_type == SourceType.GITHUB:
        return False
    return True


def enrich_news_full_text(
    news: List[ContentItem],
    *,
    max_items: int = 60,
    timeout: int = 25,
    max_chars: int = 12000,
) -> List[ContentItem]:
    """
    Enrich news items with `full_text`.

    - Only attempts for `ContentType.NEWS`.
    - Leaves existing `full_text` intact unless too short.
    - Best-effort: failures are logged and skipped.
    """
    if not news:
        return news

    attempted = 0
    enriched = 0

    for item in news:
        if attempted >= max_items:
            break
        if not _should_fetch(item):
            continue

        attempted += 1
        url = item.url
        try:
            # Avoid fetching internal HN item pages; they are mostly comments.
            host = urlparse(url).netloc.lower()
            if host.endswith("news.ycombinator.com"):
                continue

            resp = requests.get(url, headers=_DEFAULT_HEADERS, timeout=timeout)
            resp.raise_for_status()
            html = resp.text or ""

            text = _extract_with_optional_libs(html, url)
            if not text:
                continue

            # Keep the most useful portion.
            item.full_text = text[:max_chars]
            enriched += 1
        except Exception as exc:
            logger.debug("[FullText] fetch failed: %s | %s", url, exc)
            continue

    logger.info("[FullText] enriched %s/%s attempted (max %s)", enriched, attempted, max_items)
    return news

