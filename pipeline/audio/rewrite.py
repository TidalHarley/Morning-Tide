"""
Rewrite longform script into deep interview podcast style.
"""
import logging
import os
from typing import Optional

from openai import OpenAI

from ..config import config

logger = logging.getLogger(__name__)


def _get_qwen_client() -> Optional[OpenAI]:
    api_key = (config.dashscope_api_key or "").strip()
    if not api_key:
        return None
    base_url = (config.dashscope_base_url or "").strip()
    return OpenAI(api_key=api_key, base_url=base_url)


def _build_rewrite_prompt(text: str) -> str:
    return f"""请把下面这段播客长文稿改写为“深度访谈式播客”的口播文本。

要求：
1) 语言自然、克制、有深度；避免 AI 腔和模板话术。
2) 使用“主持人”一人说话的形式，不要过度戏剧化。
3) 保留原文的事实信息与结构逻辑，可适度重组顺序以增强听感。
4) 不要列表化，整个播客要自然一体化，不要有明显的枚举感，要加标题或小标题。
5) 不要出现 Markdown、引号样式标注或多余说明。

原文如下：
{text}
"""


def rewrite_audio_text(text: str) -> str:
    if not config.audio_rewrite_enabled:
        return text

    content = (text or "").strip()
    if not content:
        return content

    if len(content) > config.audio_rewrite_max_chars:
        content = content[: config.audio_rewrite_max_chars]

    client = _get_qwen_client()
    if not client:
        logger.warning("[AudioRewrite] 未设置 DASHSCOPE_API_KEY，跳过改写")
        return content

    model = (config.audio_rewrite_model or "").strip() or config.qwen_l3_model
    prompt = _build_rewrite_prompt(content)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=4000,
        )
        rewritten = response.choices[0].message.content or ""
        rewritten = rewritten.strip()
        return rewritten or content
    except Exception as exc:
        logger.error("[AudioRewrite] 改写失败: %s", exc)
        return content
