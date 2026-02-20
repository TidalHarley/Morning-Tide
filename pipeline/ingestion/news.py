"""
AI Tides - 新闻数据摄取
数据源: Hacker News, RSS Feeds
"""
import logging
import requests
import os
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import feedparser
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urlparse, urljoin, parse_qsl, urlencode, urlunparse, quote_plus
import time
import re
import html as _html
from tenacity import retry, stop_after_attempt, wait_exponential
from ..models import ContentItem, ContentType, SourceType
from ..config import config

logger = logging.getLogger(__name__)

_IMAGE_CACHE: dict = {}
_IMAGE_SEARCH_CACHE: dict = {}
_WEB_SEARCH_CACHE: dict = {}
_SESSION: Optional[requests.Session] = None
_IMAGE_SESSION: Optional[requests.Session] = None
_IMAGE_VALIDATE_CACHE: dict = {}
_BAD_IMAGE_HOSTS: set = set()
_USED_IMAGE_URLS: dict = {}


def _compile_hn_keyword_patterns(keywords: List[str]) -> List[tuple]:
    """将 HN 关键词编译为整词匹配模式，降低子串误命中。"""
    patterns: List[tuple] = []
    for raw in keywords or []:
        kw = (raw or "").strip().lower()
        if not kw:
            continue
        escaped = re.escape(kw)
        if re.search(r"[a-z0-9]", kw):
            # 使用字母数字边界，避免 ai 命中 paid / ml 命中 html
            pattern = re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)
        else:
            pattern = re.compile(escaped, re.IGNORECASE)
        patterns.append((kw, pattern))
    return patterns


def _match_hn_keywords(text: str, compiled_patterns: List[tuple]) -> set:
    matched = set()
    haystack = (text or "").lower()
    if not haystack:
        return matched
    for kw, pattern in compiled_patterns:
        if pattern.search(haystack):
            matched.add(kw)
    return matched


def _normalize_image_url(image_url: str, base_url: str) -> str:
    image_url = _html.unescape((image_url or "").strip())
    if not image_url:
        return ""
    if image_url.startswith("//"):
        image_url = "https:" + image_url
    if image_url and not image_url.lower().startswith(("http://", "https://")):
        image_url = urljoin(base_url, image_url)
    return image_url.strip()


def _boost_image_resolution(url: str) -> List[str]:
    """
    尝试基于常见参数提升图片分辨率（只追加候选，不强制）。
    例如 ?w=300&h=200 -> ?w=1200&h=630
    """
    if not url:
        return []
    try:
        parsed = urlparse(url)
        boosted_candidates: List[str] = []

        # 1) WordPress-style filename: xxx-300x200.jpg -> xxx.jpg
        try:
            if re.search(r"-\d{2,5}x\d{2,5}\.(jpg|jpeg|png|webp|gif|avif)$", parsed.path, re.IGNORECASE):
                cleaned_path = re.sub(
                    r"-\d{2,5}x\d{2,5}(?=\.(jpg|jpeg|png|webp|gif|avif)$)",
                    "",
                    parsed.path,
                    flags=re.IGNORECASE,
                )
                cleaned = urlunparse(parsed._replace(path=cleaned_path))
                if cleaned and cleaned != url:
                    boosted_candidates.append(cleaned)
        except Exception:
            pass

        # 2) Query-based resizing (imgix/wp/cdn)
        if not parsed.query:
            return boosted_candidates
        params = parse_qsl(parsed.query, keep_blank_values=True)
        if not params:
            return boosted_candidates
        updated = False
        new_params = []
        for key, value in params:
            lk = key.lower()
            if lk in {"w", "width", "imgw"}:
                try:
                    if int(value) < 1000:
                        new_params.append((key, "1200"))
                        updated = True
                        continue
                except Exception:
                    pass
            if lk in {"h", "height", "imgh"}:
                try:
                    if int(value) < 600:
                        new_params.append((key, "630"))
                        updated = True
                        continue
                except Exception:
                    pass
            if lk in {"q", "quality"}:
                # Bump quality a bit if it's very low
                try:
                    if int(value) < 70:
                        new_params.append((key, "85"))
                        updated = True
                        continue
                except Exception:
                    pass
            if lk in {"resize", "size"}:
                if "," in value:
                    new_params.append((key, "1200,630"))
                    updated = True
                    continue
                if "x" in value:
                    new_params.append((key, "1200x630"))
                    updated = True
                    continue
            new_params.append((key, value))
        if not updated:
            return boosted_candidates
        new_query = urlencode(new_params, doseq=True)
        boosted = urlunparse(parsed._replace(query=new_query))
        if boosted == url:
            return boosted_candidates
        boosted_candidates.append(boosted)
        return boosted_candidates
    except Exception:
        return []


def _pick_best_srcset(srcset: str) -> str:
    """
    Parse srcset and pick the largest candidate.
    Supports `... 1200w` or `... 2x` descriptors.
    """
    if not srcset:
        return ""
    candidates = []
    for raw in [p.strip() for p in srcset.split(",") if p.strip()]:
        parts = raw.split()
        url = (parts[0] or "").strip()
        desc = (parts[1] if len(parts) > 1 else "").strip().lower()
        score = 0.0
        if desc.endswith("w"):
            try:
                score = float(desc[:-1])
            except Exception:
                score = 0.0
        elif desc.endswith("x"):
            try:
                score = float(desc[:-1]) * 1000.0
            except Exception:
                score = 0.0
        candidates.append((score, url))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1] if candidates else ""


def _parse_image_dimensions(data: bytes) -> Optional[tuple]:
    """
    Minimal image header parser (PNG/JPEG/GIF/WebP).
    Returns (width, height) if detected.
    """
    if not data or len(data) < 16:
        return None
    # PNG
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        try:
            w = int.from_bytes(data[16:20], "big")
            h = int.from_bytes(data[20:24], "big")
            return (w, h)
        except Exception:
            return None
    # GIF
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        try:
            w = int.from_bytes(data[6:8], "little")
            h = int.from_bytes(data[8:10], "little")
            return (w, h)
        except Exception:
            return None
    # WebP (RIFF....WEBP)
    if data.startswith(b"RIFF") and len(data) >= 16 and data[8:12] == b"WEBP":
        # VP8X chunk (extended) is easiest
        try:
            idx = data.find(b"VP8X")
            if idx != -1 and len(data) >= idx + 14:
                # width-1 and height-1 are 24-bit little-endian starting at +8 and +11
                w = 1 + int.from_bytes(data[idx + 8 : idx + 11], "little")
                h = 1 + int.from_bytes(data[idx + 11 : idx + 14], "little")
                return (w, h)
        except Exception:
            pass
        return None
    # JPEG: scan markers for SOF
    if data.startswith(b"\xff\xd8"):
        i = 2
        try:
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                # SOF markers: C0,C1,C2,C3,C5,C6,C7,C9,CA,CB,CD,CE,CF
                if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                    # segment length at i+2..i+3, then: precision(1), height(2), width(2)
                    h = int.from_bytes(data[i + 5 : i + 7], "big")
                    w = int.from_bytes(data[i + 7 : i + 9], "big")
                    return (w, h)
                # skip markers without length
                if marker in {0xD8, 0xD9}:
                    i += 2
                    continue
                if i + 4 >= len(data):
                    break
                seg_len = int.from_bytes(data[i + 2 : i + 4], "big")
                if seg_len < 2:
                    break
                i += 2 + seg_len
        except Exception:
            return None
    return None


def _detect_valid_proxy() -> Optional[str]:
    """检测有效的代理地址（常见端口）"""
    common_ports = [7890, 7891, 1080, 10809, 10808, 8080, 8118, 9090, 33210]
    for port in common_ports:
        proxy_url = f"http://127.0.0.1:{port}"
        try:
            resp = requests.get(
                "https://www.google.com",
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=5,
                verify=False,
            )
            if resp.status_code < 500:
                logger.info("[HTTP] 自动检测到有效代理: %s", proxy_url)
                return proxy_url
        except Exception:
            continue
    return None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is not None:
        return _SESSION
    
    # 抑制 SSL 警告（关闭 SSL 校验时）
    if not config.requests_verify_ssl and config.suppress_insecure_warnings:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    session = requests.Session()
    
    # 代理配置
    if not config.requests_use_proxy:
        logger.info("[HTTP] 已禁用代理（trust_env=False）")
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
    else:
        # 检查环境变量中的代理是否有效（端口 9 是无效的）
        env_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        if env_proxy and (":9" in env_proxy.split("/")[-1] or env_proxy.endswith(":9")):
            logger.warning("[HTTP] 检测到无效代理端口 %s，尝试自动检测...", env_proxy)
            valid_proxy = _detect_valid_proxy()
            if valid_proxy:
                session.proxies = {"http": valid_proxy, "https": valid_proxy}
                session.trust_env = False  # 不使用环境变量中的无效代理
            else:
                logger.warning("[HTTP] 未找到有效代理，将直连（可能失败）")
                session.trust_env = False
                session.proxies = {"http": None, "https": None}
        else:
            session.trust_env = True
    
    # 重试机制（针对瞬时网络错误）
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    _SESSION = session
    return _SESSION


def _get_image_session() -> requests.Session:
    """
    图片相关请求专用 Session：
    - 不做 urllib3 Retry（避免卡死）
    - 复用与主 Session 一致的代理设置
    """
    global _IMAGE_SESSION
    if _IMAGE_SESSION is not None:
        return _IMAGE_SESSION

    if not config.requests_verify_ssl and config.suppress_insecure_warnings:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    s = requests.Session()

    # 复制主 Session 的代理策略（不要触发带重试的 adapter）
    base = _get_session()
    try:
        s.trust_env = base.trust_env
        s.proxies = getattr(base, "proxies", {}) or {}
    except Exception:
        pass

    no_retry = Retry(
        total=0,
        connect=0,
        read=0,
        redirect=0,
        status=0,
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=no_retry, pool_connections=10, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    _IMAGE_SESSION = s
    return _IMAGE_SESSION


def _looks_like_bad_image(image_url: str) -> bool:
    """尽量过滤掉 favicon / logo / sprite / data-uri 等“非主图”候选。"""
    u = (image_url or "").strip()
    if not u:
        return True
    lower = u.lower()
    if lower.startswith("data:"):
        return True
    if lower.endswith(".svg"):
        return True
    bad_tokens = [
        "favicon", "apple-touch-icon", "siteicon", "icon",
        "sprite", "spacer", "blank", "pixel", "1x1",
        "logo", "brandmark",
        "loading", "placeholder", "default", "noimage", "no-image", "no_image", "missing",
    ]
    return any(tok in lower for tok in bad_tokens)


def _image_dedup_key(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".lower()
    except Exception:
        return (url or "").split("?")[0].strip().lower()


def _is_duplicate_image_for_origin(image_url: str, origin_url: str) -> bool:
    """只对“跨域来源图片”去重，避免同题媒体通用图重复."""
    key = _image_dedup_key(image_url)
    if not key:
        return False
    try:
        origin_host = urlparse(origin_url).netloc.lower() if origin_url else ""
        image_host = urlparse(image_url).netloc.lower()
    except Exception:
        origin_host = ""
        image_host = ""
    # 同域（可能是官方文章）允许重复
    if origin_host and image_host and origin_host == image_host:
        return False
    return _USED_IMAGE_URLS.get(key, 0) > 0


def _mark_image_used(image_url: str) -> None:
    key = _image_dedup_key(image_url)
    if not key:
        return
    _USED_IMAGE_URLS[key] = _USED_IMAGE_URLS.get(key, 0) + 1


def _is_probably_image_url(url: str) -> bool:
    lower = (url or "").lower()
    return any(ext in lower for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"]) or "images" in lower


def _validate_remote_image(url: str, timeout_seconds: float = 6.0) -> bool:
    """
    轻量校验：尽量避免选到 HTML、超小文件、被拦截的资源。
    注意：部分站点不支持 HEAD；失败时退回 GET(stream) 快速探测。
    """
    headers = {
        "User-Agent": config.reddit_user_agent,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    }
    if not url or url.startswith("/"):
        return False
    if url in _IMAGE_VALIDATE_CACHE:
        return bool(_IMAGE_VALIDATE_CACHE[url])

    host = ""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        host = ""
    if host and host in _BAD_IMAGE_HOSTS:
        _IMAGE_VALIDATE_CACHE[url] = False
        return False

    session = _get_image_session()
    try:
        r = session.head(
            url,
            headers=headers,
            timeout=timeout_seconds,
            allow_redirects=True,
            verify=config.requests_verify_ssl,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"HEAD {r.status_code}")
        ctype = (r.headers.get("content-type") or "").lower()
        # 必须有 content-type 且包含 image
        if not ctype or "image" not in ctype:
            _IMAGE_VALIDATE_CACHE[url] = False
            return False
        clen = r.headers.get("content-length")
        if clen:
            try:
                if int(clen) < config.image_min_bytes:
                    _IMAGE_VALIDATE_CACHE[url] = False
                    return False
            except Exception:
                pass
        # Try lightweight dimension check (fetch only first bytes)
        try:
            range_headers = dict(headers)
            range_headers["Range"] = "bytes=0-65535"
            rr = session.get(
                url,
                headers=range_headers,
                timeout=min(timeout_seconds, 6.0),
                allow_redirects=True,
                stream=True,
                verify=config.requests_verify_ssl,
            )
            chunk = b""
            for part in rr.iter_content(chunk_size=8192):
                if not part:
                    break
                chunk += part
                if len(chunk) >= 65536:
                    break
            dims = _parse_image_dimensions(chunk[:65536])
            if dims:
                w, h = dims
                if w < config.image_min_width or h < config.image_min_height:
                    _IMAGE_VALIDATE_CACHE[url] = False
                    return False
        except Exception:
            pass

        _IMAGE_VALIDATE_CACHE[url] = True
        return True
    except Exception:
        try:
            r = session.get(
                url,
                headers=headers,
                timeout=timeout_seconds,
                allow_redirects=True,
                stream=True,
                verify=config.requests_verify_ssl,
            )
            if r.status_code >= 400:
                _IMAGE_VALIDATE_CACHE[url] = False
                return False
            ctype = (r.headers.get("content-type") or "").lower()
            # 必须有 content-type 且包含 image
            if not ctype or "image" not in ctype:
                _IMAGE_VALIDATE_CACHE[url] = False
                return False
            clen = r.headers.get("content-length")
            if clen:
                try:
                    if int(clen) < config.image_min_bytes:
                        _IMAGE_VALIDATE_CACHE[url] = False
                        return False
                except Exception:
                    pass
            # Try lightweight dimension check (fetch only first bytes)
            try:
                chunk = b""
                for part in r.iter_content(chunk_size=8192):
                    if not part:
                        break
                    chunk += part
                    if len(chunk) >= 65536:
                        break
                dims = _parse_image_dimensions(chunk[:65536])
                if dims:
                    w, h = dims
                    if w < config.image_min_width or h < config.image_min_height:
                        _IMAGE_VALIDATE_CACHE[url] = False
                        return False
            except Exception:
                pass

            _IMAGE_VALIDATE_CACHE[url] = True
            return True
        except Exception as exc:
            msg = str(exc)
            # 连接被拒绝：快速拉黑该 host，避免后续反复尝试导致卡死
            if host and ("WinError 10061" in msg or "Connection refused" in msg or "actively refused" in msg):
                _BAD_IMAGE_HOSTS.add(host)
            _IMAGE_VALIDATE_CACHE[url] = False
            return False


def _extract_meta_image(html: str, base_url: str) -> Optional[str]:
    # Many sites put attributes in different order (content before property/name),
    # so regex-only matching is fragile. Prefer BeautifulSoup if available.
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "html.parser")
        candidates = []
        for meta in soup.find_all("meta"):
            key = (meta.get("property") or meta.get("name") or "").strip().lower()
            if key in ("og:image", "og:image:url", "og:image:secure_url", "twitter:image", "twitter:image:src"):
                content = (meta.get("content") or "").strip()
                if content:
                    candidates.append(content)

        for image_url in candidates:
            image_url = _html.unescape(image_url).strip()
            if not image_url:
                continue
            if image_url.startswith("//"):
                image_url = "https:" + image_url
            if image_url and not image_url.lower().startswith(("http://", "https://")):
                image_url = urljoin(base_url, image_url)
            return image_url
    except Exception:
        pass

    # Fallback regex: allow attribute order to vary using lookaheads.
    patterns = [
        r'<meta(?=[^>]+(?:property|name)=["\']og:image(?::secure_url|:url)?["\'])(?=[^>]+content=["\']([^"\']+)["\'])[^>]*>',
        r'<meta(?=[^>]+name=["\']twitter:image(?::src)?["\'])(?=[^>]+content=["\']([^"\']+)["\'])[^>]*>',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if not match:
            continue
        image_url = _html.unescape((match.group(1) or "").strip())
        if not image_url:
            continue
        if image_url.startswith("//"):
            image_url = "https:" + image_url
        if image_url and not image_url.lower().startswith(("http://", "https://")):
            return urljoin(base_url, image_url)
        return image_url
    return None


def _extract_first_image(html: str, base_url: str) -> Optional[str]:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        # fallback regex
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
        if not match:
            return None
        img_url = match.group(1).strip()
        if img_url and not img_url.lower().startswith(("http://", "https://")):
            return urljoin(base_url, img_url)
        return img_url

    soup = BeautifulSoup(html, "html.parser")
    # prefer article images first; but don't just take the first <img> (often a small thumb)
    for container in [soup.find("article"), soup.body, soup]:
        if not container:
            continue
        best_url = ""
        best_score = -1.0
        for img in container.find_all("img", limit=25):
            # Prefer real sources over placeholders / lazy-load attributes.
            img_url = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
                or img.get("data-original")
                or ""
            )
            if img.get("srcset"):
                picked = _pick_best_srcset(img.get("srcset") or "")
                if picked:
                    img_url = picked
            if not img_url:
                continue
            img_url = _html.unescape(img_url).strip()
            if img_url.startswith("data:"):
                continue
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            lowered = img_url.lower()
            if lowered.endswith(".svg") or "sprite" in lowered:
                continue
            if _looks_like_bad_image(img_url):
                continue

            # Score: prefer explicit large dimensions and srcset candidates
            score = 0.0
            try:
                w = int(img.get("width") or 0)
                h = int(img.get("height") or 0)
                score += min(w * h, 2_000_000) / 10_000.0
            except Exception:
                pass
            if img.get("srcset"):
                score += 50.0
            if "1200" in img_url or "2000" in img_url:
                score += 10.0

            if score > best_score:
                best_score = score
                best_url = img_url

        if best_url:
            if best_url and not best_url.lower().startswith(("http://", "https://")):
                return urljoin(base_url, best_url)
            return best_url
    return None


def _search_image_candidates(query: str) -> List[str]:
    if not query:
        return []
    if query in _IMAGE_SEARCH_CACHE:
        return _IMAGE_SEARCH_CACHE[query]
    headers = {
        "User-Agent": config.reddit_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    }
    candidates: List[str] = []
    session = _get_session()
    try:
        response = session.get(
            "https://www.bing.com/images/search",
            params={"q": query, "form": "HDRSC2"},
            headers=headers,
            timeout=15,
            verify=config.requests_verify_ssl,
        )
        response.raise_for_status()
        html = response.text[:300000]
        # Bing image results embed JSON in the "m" attribute; support multiple escaping variants.
        bing_patterns = [
            r'murl\\":\\"(.*?)\\"',
            r'"murl":"(.*?)"',
            r"'murl':'(.*?)'",
        ]
        for pattern in bing_patterns:
            for match in re.finditer(pattern, html, re.IGNORECASE):
                raw = (match.group(1) or "").strip()
                if not raw:
                    continue
                # Decode common escaped sequences in embedded JSON payload.
                raw = raw.replace("\\/", "/").replace("\\u002f", "/")
                raw = _html.unescape(raw).strip()
                if raw:
                    candidates.append(raw)
        # Fallback: grab img tags
        if not candidates:
            for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE):
                url = _html.unescape(match.group(1)).strip()
                if url:
                    candidates.append(url)
    except Exception:
        candidates = []
    # De-dup while preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        unique.append(c)
    _IMAGE_SEARCH_CACHE[query] = unique
    return unique


def _search_web_results(query: str) -> List[str]:
    if not query:
        return []
    cache_key = f"web::{query}"
    if cache_key in _WEB_SEARCH_CACHE:
        return _WEB_SEARCH_CACHE[cache_key]
    headers = {
        "User-Agent": config.reddit_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    }
    session = _get_session()
    results: List[str] = []
    try:
        response = session.get(
            "https://www.bing.com/search",
            params={"q": query},
            headers=headers,
            timeout=12,
            verify=config.requests_verify_ssl,
        )
        response.raise_for_status()
        html = response.text[:300000]
        for block in re.finditer(r'<li class="b_algo".*?</li>', html, re.IGNORECASE | re.DOTALL):
            snippet = block.group(0)
            match = re.search(r'<a[^>]+href=["\']([^"\']+)["\']', snippet, re.IGNORECASE)
            if not match:
                continue
            url = _html.unescape(match.group(1)).strip()
            if not url or not url.lower().startswith(("http://", "https://")):
                continue
            host = urlparse(url).netloc.lower()
            if not host or "bing.com" in host or "microsoft.com" in host:
                continue
            results.append(url)
    except Exception:
        results = []

    # De-dup while preserving order
    seen = set()
    unique = []
    for u in results:
        if u in seen:
            continue
        seen.add(u)
        unique.append(u)
    _WEB_SEARCH_CACHE[cache_key] = unique
    return unique


def _search_related_article_image(title: str, source_name: str, original_url: str) -> Optional[str]:
    """搜索同题新闻的其他媒体图片，只返回验证通过的图片"""
    if not title:
        return None
    queries = [title]
    if source_name:
        queries.append(f"{title} {source_name}")
    queries.append(f"{title} news")

    origin_host = urlparse(original_url).netloc.lower() if original_url else ""
    for q in queries:
        candidates = _search_web_results(q)
        for candidate_url in candidates[:6]:
            if candidate_url == original_url:
                continue
            host = urlparse(candidate_url).netloc.lower()
            if origin_host and host and origin_host == host:
                continue
            og = _fetch_og_image(candidate_url)
            if og and not _looks_like_bad_image(og):
                # 必须验证通过才返回
                if _validate_remote_image(og, timeout_seconds=3.0):
                    return og
    return None


def _extract_search_keywords(title: str) -> str:
    """从标题中提取搜索关键词"""
    if not title:
        return ""
    # 常见的 AI 相关关键词，保留这些
    ai_keywords = {
        "ai", "artificial intelligence", "machine learning", "ml", "llm",
        "gpt", "openai", "anthropic", "google", "meta", "microsoft", "nvidia",
        "deepmind", "robot", "robotics", "autonomous", "neural", "model",
        "chatgpt", "claude", "gemini", "copilot", "agent", "automation"
    }
    # 去除常见的停用词
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "under", "again", "further", "then", "once", "here",
        "there", "when", "where", "why", "how", "all", "each", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own",
        "same", "so", "than", "too", "very", "just", "and", "but", "if", "or",
        "because", "until", "while", "about", "against", "between", "into",
        "through", "during", "before", "after", "above", "below", "up", "down",
        "out", "off", "over", "under", "again", "further", "then", "once",
        "new", "says", "said", "report", "reports", "according", "now", "today"
    }
    words = title.lower().split()
    # 保留 AI 关键词和非停用词
    keywords = []
    for w in words:
        # 清理标点
        clean = "".join(c for c in w if c.isalnum())
        if not clean:
            continue
        if clean in ai_keywords or (clean not in stop_words and len(clean) > 2):
            keywords.append(clean)
    # 返回前 5 个关键词
    return " ".join(keywords[:5])


def _search_image_for_news(title: str, source_name: str = "") -> Optional[str]:
    """图片搜索，只返回验证通过的图片"""
    queries: List[str] = []
    primary = f"{title} {source_name}".strip()
    if primary:
        queries.append(primary)
    if title:
        queries.append(title.strip())
    keywords = _extract_search_keywords(title or "")
    if keywords:
        queries.append(f"{keywords} ai news".strip())

    # De-dup queries while preserving order
    dedup_queries: List[str] = []
    seen_q = set()
    for q in queries:
        if not q or q in seen_q:
            continue
        seen_q.add(q)
        dedup_queries.append(q)

    for q in dedup_queries[:3]:
        candidates = _search_image_candidates(q)
        # Strict pass first
        for c in candidates[:16]:
            if _looks_like_bad_image(c):
                continue
            if _validate_remote_image(c):
                return c

        # Lenient pass: some CDNs do not provide full headers/size but still render in browser.
        for c in candidates[:20]:
            if _looks_like_bad_image(c):
                continue
            try:
                session = _get_image_session()
                r = session.head(
                    c,
                    headers={"User-Agent": config.reddit_user_agent},
                    timeout=2.5,
                    allow_redirects=True,
                    verify=config.requests_verify_ssl,
                )
                if r.status_code < 400:
                    ctype = (r.headers.get("content-type") or "").lower()
                    if "image" in ctype:
                        return c
            except Exception:
                continue
    return None


def _build_semantic_fallback_candidates(title: str, source_name: str = "") -> List[str]:
    """
    构造语义化兜底图片 URL（基于关键词）：
    - Unsplash Source：按关键词返回摄影图
    - Pollinations：按提示词生成 AI 相关图
    """
    keywords = _extract_search_keywords(title or "")
    parts = [p.strip() for p in [keywords, source_name, "AI technology"] if p and p.strip()]
    prompt = " ".join(parts[:4]).strip() or "AI technology news"
    encoded = quote_plus(prompt)
    seed = quote_plus((keywords or title or "ai-news")[:64].strip() or "ai-news")

    return [
        f"https://source.unsplash.com/1600x900/?{encoded}",
        f"https://image.pollinations.ai/prompt/{encoded}?width=1600&height=900&seed={seed}&nologo=true",
    ]


def _fetch_og_image(url: str) -> Optional[str]:
    if not url:
        return None
    if url in _IMAGE_CACHE:
        return _IMAGE_CACHE[url]
    try:
        headers = {
            "User-Agent": config.reddit_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        session = _get_session()
        response = session.get(
            url,
            headers=headers,
            timeout=20,
            allow_redirects=True,
            verify=config.requests_verify_ssl,
        )
        response.raise_for_status()
        # Some sites respond with non-HTML (pdf, etc.); skip those.
        ctype = (response.headers.get("content-type") or "").lower()
        if "text/html" not in ctype and "application/xhtml+xml" not in ctype:
            _IMAGE_CACHE[url] = None
            return None
        html = response.text[:350000]

        candidates: List[str] = []

        meta = _extract_meta_image(html, url)
        if meta:
            candidates.append(meta)

        # Some sites provide link rel=image_src or itemprop=image
        try:
            from bs4 import BeautifulSoup  # type: ignore

            soup = BeautifulSoup(html, "html.parser")
            link = soup.find("link", attrs={"rel": lambda v: v and "image_src" in str(v)})
            if link and link.get("href"):
                candidates.append(str(link.get("href")))
            meta_itemprop = soup.find("meta", attrs={"itemprop": "image"})
            if meta_itemprop and meta_itemprop.get("content"):
                candidates.append(str(meta_itemprop.get("content")))
        except Exception:
            pass

        first = _extract_first_image(html, url)
        if first:
            candidates.append(first)

        # Normalize + de-dup while keeping order
        normed: List[str] = []
        seen = set()
        for c in candidates:
            u = _normalize_image_url(c, url)
            if not u or u in seen:
                continue
            seen.add(u)
            normed.append(u)

        # Prefer candidates that "look like images" and pass a lightweight remote check.
        chosen: Optional[str] = None
        checks = 0
        for c in normed:
            if _looks_like_bad_image(c):
                continue
            if not _is_probably_image_url(c):
                # Still allow, but only after trying a couple of better-looking URLs.
                continue
            if _validate_remote_image(c):
                chosen = c
                break
            checks += 1
            if checks >= 2:
                break

        # Fallback: pick first non-bad candidate even if we can't validate it quickly.
        if not chosen:
            for c in normed:
                if not _looks_like_bad_image(c):
                    chosen = c
                    break

        _IMAGE_CACHE[url] = chosen
        return chosen
    except Exception as exc:
        logger.debug(f"[Image] 抓取失败: {url} | {exc}")
        _IMAGE_CACHE[url] = None
        return None


def _extract_reddit_image(post: dict) -> Optional[str]:
    if not post:
        return None
    # Prefer preview images when available
    preview = post.get("preview", {})
    images = preview.get("images") or []
    if images:
        source = images[0].get("source") or {}
        url = (source.get("url") or "").replace("&amp;", "&")
        if url:
            return url
    # Fallback to thumbnail if it looks like a URL
    thumb = (post.get("thumbnail") or "").strip()
    if thumb.startswith("http"):
        return thumb
    return None


def _extract_rss_image(entry) -> Optional[str]:
    try:
        if hasattr(entry, "media_content") and entry.media_content:
            for m in entry.media_content:
                url = (m.get("url") or "").strip()
                if url:
                    return url
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            for m in entry.media_thumbnail:
                url = (m.get("url") or "").strip()
                if url:
                    return url
        if hasattr(entry, "links") and entry.links:
            for link in entry.links:
                if (link.get("type") or "").startswith("image/") and link.get("href"):
                    return str(link.get("href")).strip()
        if hasattr(entry, "image") and entry.image:
            url = (entry.image.get("href") or entry.image.get("url") or "").strip()
            if url:
                return url
    except Exception:
        return None
    return None


def _resolve_image_url(
    title: str,
    url: str,
    source_name: str,
    image_url: Optional[str] = None,
) -> str:
    """
    确保最终图片可用：
    1) 优先使用已有图片
    2) 页面 OG/首图
    3) 搜索同题新闻的其他媒体图
    4) 图片搜索候选图
    5) 仍失败则使用占位图
    """
    # 每条新闻的图片获取最多花 6 秒，避免拖垮主流程
    # 对官方重要来源适当放宽时间（提高命中率）
    base_deadline = 6.0
    if (source_name or "").lower().startswith("openai"):
        base_deadline = 10.0
    if "openai.com" in (url or "").lower():
        base_deadline = max(base_deadline, 10.0)
    deadline = time.time() + base_deadline

    candidates: List[str] = []
    if image_url:
        candidates.append(image_url)
    if url:
        if time.time() < deadline:
            og = _fetch_og_image(url)
        else:
            og = None
        if og:
            candidates.append(og)
    if title:
        related = (
            _search_related_article_image(title, source_name, url)
            if time.time() < deadline
            else None
        )
        if related:
            candidates.append(related)
        searched = _search_image_for_news(title, source_name) if time.time() < deadline else None
        if searched:
            candidates.append(searched)

    expanded_candidates: List[str] = []
    for c in candidates:
        if not c:
            continue
        expanded_candidates.extend(_boost_image_resolution(c))
        expanded_candidates.append(c)

    # 第一轮：严格验证
    for c in expanded_candidates:
        if time.time() >= deadline:
            break
        normalized = _normalize_image_url(c, url or c)
        if not normalized or _looks_like_bad_image(normalized):
            continue
        if _is_duplicate_image_for_origin(normalized, url):
            continue
        # 图片校验用更短的超时，避免卡死
        if _validate_remote_image(normalized, timeout_seconds=3.0):
            _mark_image_used(normalized)
            return normalized

    # 第二轮：放宽验证（允许没有 content-length 的图片）
    for c in expanded_candidates:
        if time.time() >= deadline:
            break
        normalized = _normalize_image_url(c, url or c)
        if not normalized or _looks_like_bad_image(normalized):
            continue
        if _is_duplicate_image_for_origin(normalized, url):
            continue
        # 只要 URL 看起来像图片就尝试
        if _is_probably_image_url(normalized):
            # 快速检查：至少能访问且返回图片类型
            try:
                session = _get_image_session()
                r = session.head(
                    normalized,
                    headers={"User-Agent": config.reddit_user_agent},
                    timeout=2.0,
                    allow_redirects=True,
                    verify=config.requests_verify_ssl,
                )
                if r.status_code < 400:
                    ctype = (r.headers.get("content-type") or "").lower()
                    if "image" in ctype:
                        _mark_image_used(normalized)
                        return normalized
            except Exception:
                pass

    # 第三轮：最后努力 - 用标题关键词搜索通用图片（不限时）
    if title:
        # 提取关键词搜索
        keywords = _extract_search_keywords(title)
        if keywords:
            final_search = _search_image_for_news(keywords, "")
            if final_search and not _is_duplicate_image_for_origin(final_search, url):
                if _validate_remote_image(final_search, timeout_seconds=5.0):
                    _mark_image_used(final_search)
                    return final_search
        # 尝试更通用的搜索词
        generic_terms = ["AI technology", "artificial intelligence", "tech news"]
        for term in generic_terms:
            fallback = _search_image_for_news(f"{term} {(source_name or '').split()[0]}", "")
            if fallback and not _is_duplicate_image_for_origin(fallback, url):
                if _validate_remote_image(fallback, timeout_seconds=3.0):
                    _mark_image_used(fallback)
                    return fallback

    # 第四轮：语义化兜底图（关键词生成/检索），尽量避免无语义占位图。
    if title:
        for semantic_url in _build_semantic_fallback_candidates(title, source_name):
            if semantic_url and not _is_duplicate_image_for_origin(semantic_url, url):
                _mark_image_used(semantic_url)
                return semantic_url

    # 最终兜底：返回静态占位图，确保前端不会出现空图位。
    return (config.image_placeholder_url or "/placeholder.svg").strip()

def _is_whitelist_url(url: str) -> bool:
    if not url:
        return False
    domain = urlparse(url).netloc.lower()
    for wl_domain in config.whitelist_domains:
        normalized = (wl_domain or "").strip().lower()
        if not normalized:
            continue
        if domain == normalized or domain.endswith(f".{normalized}"):
            return True
    return False


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_hackernews() -> List[ContentItem]:
    """
    从 Hacker News 获取热门新闻
    API: https://hacker-news.firebaseio.com/v0/
    """
    news_items = []
    
    try:
        session = _get_session()
        story_ids: List[int] = []
        seen_story_ids = set()
        endpoints = config.hackernews_story_endpoints or ["topstories"]
        per_source_limit = max(1, int(config.hackernews_story_per_source))
        max_candidates = max(1, int(config.hackernews_story_max_candidates))

        for endpoint in endpoints:
            source = (endpoint or "").strip().lower()
            if not source:
                continue
            list_url = f"https://hacker-news.firebaseio.com/v0/{source}.json"
            try:
                response = session.get(list_url, timeout=60, verify=config.requests_verify_ssl)
                response.raise_for_status()
                ids = response.json()[:per_source_limit]
            except Exception as exc:
                logger.warning(f"[HackerNews] 拉取 {source} 失败: {exc}")
                continue

            for sid in ids:
                if sid in seen_story_ids:
                    continue
                seen_story_ids.add(sid)
                story_ids.append(sid)
                if len(story_ids) >= max_candidates:
                    break
            if len(story_ids) >= max_candidates:
                break

        logger.info(
            f"[HackerNews] 候选池: {len(story_ids)} 条, 来源={','.join(endpoints)}"
        )
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=config.hours_lookback)
        compiled_hn_keywords = _compile_hn_keyword_patterns(config.hackernews_keywords or [])
        strong_hn_keywords = {k.lower() for k in (config.hackernews_strong_keywords or [])}
        min_hn_hits = max(1, int(config.hackernews_min_keyword_hits))
        ingest_min_score = max(config.min_hn_score, int(config.hackernews_ingest_min_score))
        
        # 批量获取故事详情
        for story_id in story_ids:
            try:
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                item_response = session.get(item_url, timeout=10, verify=config.requests_verify_ssl)
                item_response.raise_for_status()
                item = item_response.json()
                
                if not item or item.get("type") != "story":
                    continue
                
                # 解析时间
                timestamp = item.get("time", 0)
                published_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                
                # 检查时间范围
                if published_at < cutoff:
                    continue
                
                # 获取 URL
                url = item.get("url", "")
                if not url:
                    url = f"https://news.ycombinator.com/item?id={story_id}"
                
                # 检查是否是白名单域名
                is_whitelist = _is_whitelist_url(url)

                # 热度 & 相关性过滤：避免 HN Top Stories 混入非 AI 新闻
                score = int(item.get("score", 0) or 0)
                if score < ingest_min_score and not is_whitelist:
                    continue
                title = item.get("title", "") or ""
                body_text = item.get("text", "") or ""
                # 仅使用标题+正文做相关性判断，避免 URL 子串干扰。
                match_text = f"{title} {body_text}".strip()
                matched_keywords = _match_hn_keywords(match_text, compiled_hn_keywords)
                strong_hits = matched_keywords & strong_hn_keywords
                if (not is_whitelist) and (len(matched_keywords) < min_hn_hits) and (not strong_hits):
                    continue
                
                image_url = _resolve_image_url(
                    title=title,
                    url=url,
                    source_name="Hacker News",
                )
                content_item = ContentItem(
                    id=f"hn_{story_id}",
                    title=item.get("title", ""),
                    url=url,
                    content_type=ContentType.NEWS,
                    source_type=SourceType.HACKERNEWS,
                    source_name="Hacker News",
                    abstract="",  # HN 没有摘要
                    image_url=image_url,
                    authors=[item.get("by", "")] if item.get("by") else [],
                    published_at=published_at,
                    score=score,
                    comments_count=item.get("descendants", 0),
                    is_whitelist=is_whitelist
                )
                news_items.append(content_item)
                
                # 适当延迟避免请求过快
                time.sleep(0.05)
                
            except Exception as e:
                logger.debug(f"[HackerNews] 获取故事 {story_id} 失败: {e}")
                continue
                
    except Exception as e:
        logger.error(f"[HackerNews] 获取失败: {e}")
    
    logger.info(f"[HackerNews] 最终获取 {len(news_items)} 条新闻")
    return news_items


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_reddit() -> List[ContentItem]:
    """从 Reddit 获取 AI 相关社区内容"""
    news_items: List[ContentItem] = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.hours_lookback)

    headers = {"User-Agent": config.reddit_user_agent}
    sort = config.reddit_sort
    limit = config.reddit_limit
    time_filter = "day" if sort == "top" else None

    for subreddit in config.reddit_subreddits:
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
        params = {"limit": limit}
        if time_filter:
            params["t"] = time_filter

        try:
            session = _get_session()
            response = session.get(
                url,
                headers=headers,
                params=params,
                timeout=60,
                verify=config.requests_verify_ssl,
            )
            response.raise_for_status()
            data = response.json()
            children = data.get("data", {}).get("children", [])

            for child in children:
                post = child.get("data", {})
                if not post:
                    continue

                created_utc = post.get("created_utc")
                if not created_utc:
                    continue
                published_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                if published_at < cutoff:
                    continue

                score = int(post.get("score", 0))
                if score < config.reddit_min_upvotes:
                    continue

                title = post.get("title", "")
                post_url = post.get("url") or ""
                if post.get("is_self") or not post_url:
                    post_url = f"https://www.reddit.com{post.get('permalink', '')}"

                abstract = (post.get("selftext") or "")[:500]
                full_text = (post.get("selftext") or "")[:12000]

                initial_image = _extract_reddit_image(post)
                image_url = _resolve_image_url(
                    title=title,
                    url=post_url,
                    source_name=f"r/{subreddit}",
                    image_url=initial_image,
                )
                content_item = ContentItem(
                    id=f"reddit_{post.get('id', '')}",
                    title=title,
                    url=post_url,
                    content_type=ContentType.NEWS,
                    source_type=SourceType.REDDIT,
                    source_name=f"r/{subreddit}",
                    abstract=abstract,
                    full_text=full_text,
                    image_url=image_url,
                    authors=[post.get("author", "")] if post.get("author") else [],
                    published_at=published_at,
                    score=score,
                    comments_count=int(post.get("num_comments", 0)),
                    is_whitelist=_is_whitelist_url(post_url),
                )
                news_items.append(content_item)

        except Exception as e:
            logger.error(f"[Reddit] {subreddit} 获取失败: {e}")
            continue

    logger.info(f"[Reddit] 总计获取 {len(news_items)} 条新闻")
    return news_items


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_github_trending() -> List[ContentItem]:
    """从 GitHub Trending 获取 AI 相关开源项目"""
    news_items: List[ContentItem] = []
    headers = {"User-Agent": config.reddit_user_agent}
    params = {"since": "daily"}

    try:
        session = _get_session()
        response = session.get(
            config.github_trending_url,
            headers=headers,
            params=params,
            timeout=60,
            verify=config.requests_verify_ssl,
        )
        response.raise_for_status()
        html = response.text

        try:
            from bs4 import BeautifulSoup
        except Exception as e:
            logger.warning(f"[GitHub] 未安装 beautifulsoup4，跳过: {e}")
            return []

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("article.Box-row")[: config.github_trending_limit]
        keywords = [kw.lower() for kw in config.github_trending_keywords]

        for row in rows:
            title_anchor = row.select_one("h2 a")
            if not title_anchor:
                continue
            repo_path = re.sub(r"\s+", "", title_anchor.get_text(strip=True))
            repo_url = f"https://github.com{title_anchor.get('href', '')}"
            description_el = row.select_one("p")
            description = description_el.get_text(strip=True) if description_el else ""

            text = f"{repo_path} {description}".lower()
            if not any(kw in text for kw in keywords):
                continue

            star_el = row.select_one("a[href$='/stargazers']")
            stars_text = star_el.get_text(strip=True) if star_el else "0"
            stars_text = stars_text.replace(",", "")
            try:
                stars = int(stars_text)
            except ValueError:
                stars = 0

            today = datetime.now(timezone.utc)

            image_url = _resolve_image_url(
                title=repo_path,
                url=repo_url,
                source_name="GitHub Trending",
            )
            content_item = ContentItem(
                id=f"github_{repo_path.replace('/', '_')}",
                title=repo_path,
                url=repo_url,
                content_type=ContentType.NEWS,
                source_type=SourceType.GITHUB,
                source_name="GitHub Trending",
                abstract=description[:500],
                image_url=image_url,
                authors=[],
                published_at=today,
                score=stars,
                comments_count=0,
                is_whitelist=_is_whitelist_url(repo_url),
            )
            news_items.append(content_item)

    except Exception as e:
        logger.error(f"[GitHub] 获取失败: {e}")

    logger.info(f"[GitHub] 总计获取 {len(news_items)} 条新闻")
    return news_items


def fetch_rss_feeds() -> List[ContentItem]:
    """
    从 RSS 源获取新闻
    """
    news_items = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.hours_lookback)
    
    for feed_config in config.rss_feeds:
        feed_name = feed_config["name"]
        feed_url = feed_config["url"]
        is_whitelist = feed_config.get("whitelist", False)
        
        try:
            logger.info(f"[RSS] 正在获取: {feed_name}")

            # feedparser.parse(url) will use urllib internally, which is prone to SSL EOF issues on some sites.
            # Fetch with requests (with UA + redirects) then parse the bytes.
            headers = {
                "User-Agent": config.reddit_user_agent,
                "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            }
            session = _get_session()
            resp = session.get(
                feed_url,
                headers=headers,
                timeout=60,
                allow_redirects=True,
                verify=config.requests_verify_ssl,
            )
            if resp.status_code == 404:
                logger.warning(f"[RSS] {feed_name} 返回 404，已跳过")
                continue
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"[RSS] {feed_name} 解析警告: {feed.bozo_exception}")
            
            entries = feed.entries[:50]  # 每个源最多50条
            
            for entry in entries:
                # 解析发布时间
                published_at = None
                
                # 尝试多种时间字段
                time_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
                for field in time_fields:
                    if hasattr(entry, field) and getattr(entry, field):
                        try:
                            time_struct = getattr(entry, field)
                            published_at = datetime(*time_struct[:6], tzinfo=timezone.utc)
                            break
                        except:
                            continue
                
                # 如果没有时间信息，跳过
                if not published_at:
                    continue
                
                # 检查时间范围
                if published_at < cutoff:
                    continue
                
                # 获取摘要
                abstract = ""
                if hasattr(entry, 'summary'):
                    # 清理 HTML 标签
                    abstract = entry.summary
                    import re
                    abstract = re.sub(r'<[^>]+>', '', abstract)
                    abstract = abstract[:500]  # 限制长度

                # 获取可能的全文（RSS 有些会提供 content 字段）
                full_text = ""
                try:
                    if hasattr(entry, "content") and entry.content:
                        value = entry.content[0].get("value") if entry.content else ""
                        if value:
                            full_text = re.sub(r"<[^>]+>", "", value)
                    if not full_text and hasattr(entry, "summary"):
                        full_text = re.sub(r"<[^>]+>", "", entry.summary or "")
                    full_text = re.sub(r"\s+", " ", full_text).strip()[:12000]
                except Exception:
                    full_text = ""
                
                # 获取链接
                url = entry.get('link', '')
                
                # 生成唯一 ID
                entry_id = entry.get('id', url)
                safe_id = str(hash(entry_id))[-10:]
                
                initial_image = _extract_rss_image(entry)
                image_url = _resolve_image_url(
                    title=entry.get("title", ""),
                    url=url,
                    source_name=feed_name,
                    image_url=initial_image,
                )
                content_item = ContentItem(
                    id=f"rss_{safe_id}",
                    title=entry.get('title', ''),
                    url=url,
                    content_type=ContentType.NEWS,
                    source_type=SourceType.RSS,
                    source_name=feed_name,
                    abstract=abstract,
                    full_text=full_text if full_text else None,
                    image_url=image_url,
                    authors=[entry.get('author', '')] if entry.get('author') else [],
                    published_at=published_at,
                    score=0,  # RSS 没有投票
                    comments_count=0,
                    is_whitelist=is_whitelist
                )
                news_items.append(content_item)
                
        except Exception as e:
            logger.error(f"[RSS] {feed_name} 获取失败: {e}")
            continue
    
    logger.info(f"[RSS] 总计获取 {len(news_items)} 条新闻")
    return news_items


def fetch_all_news() -> List[ContentItem]:
    """获取所有新闻源的数据"""
    all_news = []
    
    # Hacker News
    hn_news = fetch_hackernews()
    all_news.extend(hn_news)
    
    # Reddit
    reddit_news = fetch_reddit()
    all_news.extend(reddit_news)

    # GitHub Trending
    github_news = fetch_github_trending()
    all_news.extend(github_news)

    # RSS Feeds
    rss_news = fetch_rss_feeds()
    all_news.extend(rss_news)

    logger.info(f"[News] 总计获取 {len(all_news)} 条新闻")
    return all_news

"""
$env:HTTPS_PROXY = "http://127.0.0.1:7897"
$env:HTTP_PROXY = "http://127.0.0.1:7897"
python pipeline/main.py
"""