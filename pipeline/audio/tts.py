"""
Audio generation for daily podcast briefing.
"""
import logging
import os
from html import escape
from typing import Optional

import requests
from openai import OpenAI

from ..config import config

logger = logging.getLogger(__name__)


def _get_openai_client() -> Optional[OpenAI]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def generate_daily_audio(text: str, date_str: str) -> Optional[str]:
    if not config.audio_enabled:
        return None
    provider = (config.audio_provider or "").lower()

    content = (text or "").strip()
    if not content:
        return None

    if len(content) > config.audio_max_chars:
        content = content[: config.audio_max_chars]

    output_dir = config.audio_output_dir
    os.makedirs(output_dir, exist_ok=True)
    filename = f"daily_briefing_{date_str}.{config.audio_format}"
    file_path = os.path.join(output_dir, filename)
    if os.path.exists(file_path):
        return f"{config.audio_public_url_prefix}/{filename}"

    try:
        if provider == "openai":
            client = _get_openai_client()
            if not client:
                logger.warning("[Audio] 未设置 OPENAI_API_KEY，跳过音频生成")
                return None
            response = client.audio.speech.create(
                model=config.audio_model,
                voice=config.audio_voice,
                input=content,
                format=config.audio_format,
            )
            audio_bytes = getattr(response, "content", None)
            if audio_bytes is None and hasattr(response, "read"):
                audio_bytes = response.read()
        elif provider == "ms_ra_forwarder":
            base_url = (config.audio_tts_base_url or "").strip()
            if not base_url:
                logger.warning("[Audio] 未设置 AI_TIDES_TTS_BASE_URL，跳过音频生成")
                return None
            voice = (config.audio_voice or "zh-CN-YunxiNeural").strip()
            ssml = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN"><voice name="{escape(voice)}">{escape(content)}</voice></speak>'
            url = f"{base_url.rstrip('/')}/api/ra"
            params = {"format": config.audio_tts_ra_format}
            headers = {"Content-Type": "text/plain"}
            token = (config.audio_tts_token or "").strip()
            if token:
                params["token"] = token
                headers["Authorization"] = f"Bearer {token}"
            resp = requests.post(url, params=params, data=ssml.encode("utf-8"), headers=headers, timeout=60)
            if resp.status_code >= 400:
                logger.error("[Audio] TTS 失败: %s %s", resp.status_code, resp.text[:200])
                return None
            audio_bytes = resp.content
        else:
            logger.warning("[Audio] 未识别的音频提供商: %s", config.audio_provider)
            return None

        if not audio_bytes:
            logger.warning("[Audio] 音频生成返回空内容")
            return None
        with open(file_path, "wb") as f:
            f.write(audio_bytes)
        return f"{config.audio_public_url_prefix}/{filename}"
    except Exception as exc:
        logger.error("[Audio] 音频生成失败: %s", exc)
        return None
