"""
AI Tides - 去重模块
包含 URL 去重与语义去重
"""
import logging
from typing import List, Optional
from urllib.parse import urlparse, parse_qsl, urlunparse

from ..models import ContentItem
from ..config import config

logger = logging.getLogger(__name__)

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "ref_src",
    "ref_url",
    "source",
    "spm",
}


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        query = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS
        ]
        cleaned = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            path=parsed.path.rstrip("/"),
            query="&".join([f"{k}={v}" for k, v in query]),
            fragment="",
        )
        return urlunparse(cleaned)
    except Exception:
        return url


class Deduplicator:
    """去重器"""

    def deduplicate_by_url(self, items: List[ContentItem]) -> List[ContentItem]:
        if not items:
            return []
        seen = {}
        result = []
        for item in items:
            norm_url = _normalize_url(item.url or "")
            key = norm_url or f"title::{item.title.strip().lower()}"
            if key in seen:
                continue
            seen[key] = True
            result.append(item)
        logger.info(f"[Dedup] URL 去重: {len(items)} -> {len(result)}")
        return result

    def deduplicate_semantic(self, items: List[ContentItem]) -> List[ContentItem]:
        if not items or len(items) < 2:
            return items
        if not config.semantic_dedup_enabled:
            return items

        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
        except Exception as e:
            logger.warning(f"[Dedup] 未安装 sentence-transformers，跳过语义去重: {e}")
            return items

        candidates = items[: config.semantic_dedup_max_items]
        texts = [
            f"{item.title}. {item.abstract or ''}".strip()
            for item in candidates
        ]

        try:
            model = SentenceTransformer("all-MiniLM-L6-v2")
            embeddings = model.encode(texts, normalize_embeddings=True)
        except Exception as e:
            logger.warning(f"[Dedup] 语义向量生成失败，跳过语义去重: {e}")
            return items

        kept_indices: List[int] = []
        kept_embeddings = []

        def rank(item: ContentItem) -> float:
            return (item.l2_combined_score or 0.0) * 2 + (item.score or 0.0)

        for idx, emb in enumerate(embeddings):
            is_duplicate = False
            for kept_idx, kept_emb in zip(kept_indices, kept_embeddings):
                similarity = float(np.dot(emb, kept_emb))
                if similarity >= config.semantic_dedup_threshold:
                    if rank(candidates[idx]) > rank(candidates[kept_idx]):
                        replace_pos = kept_indices.index(kept_idx)
                        kept_indices[replace_pos] = idx
                        kept_embeddings[replace_pos] = emb
                    is_duplicate = True
                    break
            if not is_duplicate:
                kept_indices.append(idx)
                kept_embeddings.append(emb)

        deduped = [candidates[i] for i in kept_indices]
        remainder = items[config.semantic_dedup_max_items :]
        result = deduped + remainder
        logger.info(f"[Dedup] 语义去重: {len(items)} -> {len(result)}")
        return result
