"""
AI Tides Ingestion Module - 数据摄取模块
"""
from .papers import fetch_huggingface_papers, fetch_arxiv_papers, fetch_all_papers
from .news import (
    fetch_hackernews,
    fetch_rss_feeds,
    fetch_reddit,
    fetch_github_trending,
    fetch_all_news,
)

__all__ = [
    "fetch_huggingface_papers",
    "fetch_arxiv_papers", 
    "fetch_all_papers",
    "fetch_hackernews",
    "fetch_rss_feeds",
    "fetch_reddit",
    "fetch_github_trending",
    "fetch_all_news"
]
