"""
AI Tides - 论文数据摄取
数据源: HuggingFace Daily Papers, arXiv API
"""
import logging
import re
import requests
import os
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone, time
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import ContentItem, ContentType, SourceType
from ..config import config

logger = logging.getLogger(__name__)
_SESSION: Optional[requests.Session] = None


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
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    _SESSION = session
    return _SESSION

def _keyword_score(text: str, keywords: List[str]) -> int:
    if not text:
        return 0
    text_lower = text.lower()
    score = 0
    for kw in keywords:
        if not kw:
            continue
        if kw.lower() in text_lower:
            score += 1
    return score

def _get_papers_time_window() -> Optional[Tuple[datetime, datetime]]:
    """返回论文抓取时间窗口(UTC)。周末可选使用最近工作日。"""
    tz = ZoneInfo(config.papers_timezone)
    now_utc = datetime.now(timezone.utc)
    local_now = now_utc.astimezone(tz)
    if config.papers_skip_weekends and local_now.weekday() >= 5:
        fallback_date = local_now.date()
        while fallback_date.weekday() >= 5:
            fallback_date -= timedelta(days=1)
        start_local = datetime.combine(fallback_date, time.min, tzinfo=tz)
        end_local = datetime.combine(fallback_date, time.max, tzinfo=tz)
        logger.info(
            "[Papers] 周末使用最近工作日窗口（%s）",
            fallback_date.isoformat(),
        )
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

    window_mode = (config.papers_window_mode or "rolling").lower()
    if window_mode == "calendar":
        target_date = (local_now - timedelta(days=config.papers_freshness_days)).date()
        start_local = datetime.combine(target_date, time.min, tzinfo=tz)
        end_local = datetime.combine(target_date, time.max, tzinfo=tz)
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

    # rolling: 以当前时间为结束，回溯 N 天
    start_utc = now_utc - timedelta(days=config.papers_freshness_days)
    return start_utc, now_utc


def _parse_list_dates(html: str) -> List[datetime.date]:
    matches = re.finditer(
        r"<h3[^>]*>\s*([A-Za-z]{3},\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}).*?</h3>",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    dates = []
    for match in matches:
        date_str = match.group(1)
        try:
            dates.append(datetime.strptime(date_str, "%a, %d %b %Y").date())
        except ValueError:
            continue
    return dates


def _extract_ids_for_date(html: str, target_date: datetime.date) -> List[str]:
    h3_matches = list(
        re.finditer(
            r"<h3[^>]*>\s*([A-Za-z]{3},\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}).*?</h3>",
            html,
            re.IGNORECASE | re.DOTALL,
        )
    )
    if not h3_matches:
        return []

    collected: List[str] = []
    for idx, match in enumerate(h3_matches):
        date_str = match.group(1)
        try:
            date_value = datetime.strptime(date_str, "%a, %d %b %Y").date()
        except ValueError:
            continue
        if date_value != target_date:
            continue
        next_h3 = h3_matches[idx + 1].start() if idx + 1 < len(h3_matches) else None
        segment = html[match.end() : next_h3]
        ids = re.findall(r"arXiv:(\d{4}\.\d{5})(?:v\d+)?", segment)
        ids += re.findall(r"/abs/(\d{4}\.\d{5})(?:v\d+)?", segment)
        collected.extend(ids)

    return list(dict.fromkeys(collected))


def _select_announce_date(
    html: str, cutoff_start: datetime, cutoff_end: datetime
) -> Optional[datetime.date]:
    """选择最近的有效公告日期。
    
    arXiv 列表页显示的日期与实际 UTC 时间有偏差，为确保不遗漏任何类别的论文，
    我们大幅放宽时间窗口：向前扩展 1 天，向后扩展 2 天。
    """
    dates = _parse_list_dates(html)
    if not dates:
        logger.warning("[arXiv] 日期解析失败，HTML 中未找到日期")
        return None

    est = ZoneInfo("US/Eastern")
    # 大幅放宽窗口：向前 1 天，向后 2 天
    cutoff_start_date = cutoff_start.astimezone(est).date() - timedelta(days=1)
    cutoff_end_date = cutoff_end.astimezone(est).date() + timedelta(days=2)

    valid_dates = [d for d in dates if cutoff_start_date <= d <= cutoff_end_date]
    if not valid_dates:
        logger.warning("[arXiv] 页面日期 %s 不在扩展窗口 [%s, %s] 内", 
                      [d.isoformat() for d in dates[:3]], 
                      cutoff_start_date.isoformat(), 
                      cutoff_end_date.isoformat())
    return max(valid_dates) if valid_dates else None


def _fetch_arxiv_announced_ids(
    categories: List[str], time_window: Tuple[datetime, datetime]
) -> Tuple[Optional[datetime], List[str]]:
    """从 arXiv 列表页读取最近一次“公告日”的所有论文 ID。"""
    cutoff_start, cutoff_end = time_window
    all_ids: List[str] = []
    announce_at_utc: Optional[datetime] = None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    page_size = 50  # arXiv 列表页最大支持 100，用 50 更稳定

    for cat in categories:
        html = ""
        response = None
        announce_date = None
        # 优先使用 arxiv.org（数据更新更快），export.arxiv.org 作为备用
        primary_url = f"https://arxiv.org/list/{cat}/recent?skip=0&show={page_size}"
        fallback_url = f"http://export.arxiv.org/list/{cat}/recent?skip=0&show={page_size}"
        try:
            session = _get_session()
            response = session.get(
                primary_url,
                timeout=60,
                headers=headers,
                verify=config.requests_verify_ssl,
            )
            response.raise_for_status()
            html = response.text
        except Exception as exc:
            logger.warning("[arXiv] 主站获取失败 %s: %s，尝试备用站", cat, exc)
            try:
                session = _get_session()
                response = session.get(
                    fallback_url,
                    timeout=60,
                    headers=headers,
                    verify=config.requests_verify_ssl,
                )
                response.raise_for_status()
                html = response.text
            except Exception as fallback_exc:
                logger.warning("[arXiv] 列表页获取失败 %s: %s", cat, fallback_exc)
                continue

        announce_date = _select_announce_date(html, cutoff_start, cutoff_end)
        if not announce_date:
            est = ZoneInfo("US/Eastern")
            logger.info(
                "[arXiv] 列表日期不在窗口内 %s: %s -> %s",
                cat,
                cutoff_start.astimezone(est).date().isoformat(),
                cutoff_end.astimezone(est).date().isoformat(),
            )
            continue

        announce_local = datetime.combine(announce_date, time(0, 0), tzinfo=ZoneInfo("US/Eastern"))
        announce_utc = announce_local.astimezone(timezone.utc)
        if announce_utc and (announce_at_utc is None or announce_utc > announce_at_utc):
            announce_at_utc = announce_utc

        skip = 0
        while True:
            # 优先使用 arxiv.org
            primary_url = f"https://arxiv.org/list/{cat}/recent?skip={skip}&show={page_size}"
            fallback_url = f"http://export.arxiv.org/list/{cat}/recent?skip={skip}&show={page_size}"
            html = ""
            try:
                session = _get_session()
                response = session.get(
                    primary_url,
                    timeout=60,
                    headers=headers,
                    verify=config.requests_verify_ssl,
                )
                response.raise_for_status()
                html = response.text
            except Exception:
                try:
                    session = _get_session()
                    response = session.get(
                        fallback_url,
                        timeout=60,
                        headers=headers,
                        verify=config.requests_verify_ssl,
                    )
                    response.raise_for_status()
                    html = response.text
                except Exception:
                    break

            page_dates = _parse_list_dates(html)
            if not page_dates:
                break
            page_min = min(page_dates)
            page_max = max(page_dates)
            if announce_date > page_max:
                break

            ids = _extract_ids_for_date(html, announce_date)
            if ids:
                all_ids.extend(ids)

            if announce_date < page_min:
                skip += page_size
                continue
            if announce_date not in page_dates:
                break
            skip += page_size

    if not all_ids:
        return None, []

    # 去重与截断
    deduped = list(dict.fromkeys(all_ids))
    if config.arxiv_daily_limit and config.arxiv_daily_limit > 0:
        return announce_at_utc, deduped[: config.arxiv_daily_limit]
    return announce_at_utc, deduped


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_huggingface_papers() -> List[ContentItem]:
    """
    从 HuggingFace Daily Papers 获取论文
    API: https://huggingface.co/api/daily_papers
    """
    papers = []
    stats = {
        "total": 0,
        "added": 0,
        "skipped_old": 0,
        "missing_date": 0,
        "missing_paper": 0,
        "missing_id": 0,
        "date_parse_failed": 0,
        "skipped_weekend": 0,
    }
    
    try:
        # HuggingFace Daily Papers API（不做时间窗口限制）
        url = "https://huggingface.co/api/daily_papers"
        session = _get_session()
        response = session.get(url, timeout=60, verify=config.requests_verify_ssl)
        response.raise_for_status()
        
        data = response.json()
        stats["total"] = len(data)
        logger.info(f"[HuggingFace] 获取到 {len(data)} 篇论文")
        for idx, item in enumerate(data):
            paper = item.get("paper")
            if not isinstance(paper, dict):
                stats["missing_paper"] += 1
                continue

            paper_id = paper.get("id") or paper.get("arxivId") or paper.get("arxiv_id")
            if not paper_id:
                stats["missing_id"] += 1
                continue
            
            # 解析发布时间
            published_str = (
                paper.get("publishedAt")
                or paper.get("published_at")
                or paper.get("submittedAt")
                or paper.get("date")
                or ""
            )
            published_at = None
            if published_str:
                try:
                    published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except:
                    stats["date_parse_failed"] += 1
                    published_at = None
            if not published_at:
                stats["missing_date"] += 1
                continue
            if idx < 5:
                logger.info(
                    "[HuggingFace] 示例发布时间 %s | %s",
                    published_at.isoformat(),
                    paper_id,
                )
            
            content_item = ContentItem(
                id=f"hf_{paper_id}",
                title=paper.get("title", ""),
                url=f"https://huggingface.co/papers/{paper_id}",
                content_type=ContentType.PAPER,
                source_type=SourceType.HUGGINGFACE,
                source_name="HuggingFace Daily Papers",
                abstract=paper.get("summary", ""),
                authors=[a.get("name", "") for a in paper.get("authors", []) if a.get("name")],
                published_at=published_at,
                score=item.get("numUpvotes", 0),
                comments_count=item.get("numComments", 0),
                is_whitelist=True
            )
            papers.append(content_item)
            stats["added"] += 1

        if papers:
            papers = papers[: config.hf_daily_limit]
            stats["added"] = len(papers)

    except Exception as e:
        logger.error(f"[HuggingFace] 获取失败: {e}")
    
    logger.info(
        "[HuggingFace] 有效论文 %s | 旧数据 %s | 缺日期 %s | 无paper %s | 无ID %s | 时间解析失败 %s | 周末跳过 %s",
        stats["added"],
        stats["skipped_old"],
        stats["missing_date"],
        stats["missing_paper"],
        stats["missing_id"],
        stats["date_parse_failed"],
        stats["skipped_weekend"],
    )
    return papers


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_arxiv_papers() -> List[ContentItem]:
    """
    从 arXiv API 获取论文
    API: http://export.arxiv.org/api/query
    """
    papers = []
    stats = {
        "total": 0,
        "added": 0,
        "skipped_old": 0,
        "date_parse_failed": 0,
        "skipped_weekend": 0,
    }
    
    try:
        time_window = _get_papers_time_window()
        if time_window is None:
            stats["skipped_weekend"] = 1
            return papers
        cutoff_start, cutoff_end = time_window
        logger.info(
            "[arXiv] 时间窗口 UTC: %s -> %s",
            cutoff_start.isoformat(),
            cutoff_end.isoformat(),
        )

        announce_at, id_list = _fetch_arxiv_announced_ids(
            config.arxiv_categories, time_window
        )
        if not id_list:
            logger.info("[arXiv] 列表页未找到符合窗口的论文")
            return papers
        logger.info(
            "[arXiv] 使用列表公告日 %s，命中 %s 条",
            announce_at.isoformat() if announce_at else "unknown",
            len(id_list),
        )

        # arXiv API 参数（按 ID 列表分批获取元数据）
        url = "http://export.arxiv.org/api/query"
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        entries = []
        batch_size = 50
        for start in range(0, len(id_list), batch_size):
            batch_ids = id_list[start : start + batch_size]
            # arXiv API 默认只返回 10 条，需要显式指定 max_results
            params = {
                "id_list": ",".join(batch_ids),
                "start": 0,
                "max_results": len(batch_ids),
            }
            session = _get_session()
            response = session.get(
                url,
                params=params,
                timeout=60,
                verify=config.requests_verify_ssl,
            )
            response.raise_for_status()
            root = ET.fromstring(response.content)
            entries.extend(root.findall("atom:entry", namespace))
        stats["total"] = len(entries)
        logger.info(f"[arXiv] 获取到 {len(entries)} 篇论文")

        for idx, entry in enumerate(entries):
            # 解析基本信息
            arxiv_id = entry.find("atom:id", namespace).text.split("/abs/")[-1]
            title = entry.find("atom:title", namespace).text.strip().replace("\n", " ")
            
            # 获取摘要
            summary_elem = entry.find("atom:summary", namespace)
            abstract = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None else ""
            
            # 解析发布时间/更新时间（arXiv 列表日期更接近 updated）
            published_elem = entry.find("atom:published", namespace)
            updated_elem = entry.find("atom:updated", namespace)
            published_at = None
            updated_at = None
            if published_elem is not None and published_elem.text:
                try:
                    published_at = datetime.fromisoformat(
                        published_elem.text.replace("Z", "+00:00")
                    )
                except:
                    stats["date_parse_failed"] += 1
            if updated_elem is not None and updated_elem.text:
                try:
                    updated_at = datetime.fromisoformat(
                        updated_elem.text.replace("Z", "+00:00")
                    )
                except:
                    stats["date_parse_failed"] += 1
            effective_at = updated_at or published_at
            if not effective_at:
                continue
            
            if idx < 5:
                logger.info("[arXiv] 示例发布时间 %s | %s", effective_at.isoformat(), arxiv_id)
            # 已通过“列表公告日”筛选，不再按 published/updated 二次过滤
            
            # 获取作者
            authors = []
            for author in entry.findall("atom:author", namespace):
                name = author.find("atom:name", namespace)
                if name is not None:
                    authors.append(name.text)

            # 解析 arXiv 分类（按爬取类别分配）
            arxiv_primary = None
            try:
                for cat in entry.findall("atom:category", namespace):
                    term = cat.get("term")
                    if term in config.arxiv_categories:
                        arxiv_primary = term
                        break
            except Exception:
                arxiv_primary = None

            category_map = {
                "cs.AI": "General AI",
                "cs.CV": "Computer Vision",
                "cs.RO": "Robotics",
            }
            paper_category = category_map.get(arxiv_primary, "General AI")
            
            # 获取链接
            pdf_link = f"https://arxiv.org/pdf/{arxiv_id}"
            abs_link = f"https://arxiv.org/abs/{arxiv_id}"
            
            content_item = ContentItem(
                id=f"arxiv_{arxiv_id.replace('.', '_').replace('/', '_')}",
                title=title,
                url=abs_link,
                content_type=ContentType.PAPER,
                source_type=SourceType.ARXIV,
                source_name="arXiv",
                abstract=abstract,
                authors=authors[:3],  # 只保留前3位作者
                published_at=effective_at,
                score=_keyword_score(f"{title} {abstract}", config.ai_keywords),
                comments_count=0,
                paper_category=paper_category,
            )
            papers.append(content_item)
            stats["added"] += 1

    except Exception as e:
        logger.error(f"[arXiv] 获取失败: {e}")
    
    logger.info(
        "[arXiv] 有效论文 %s | 旧数据 %s | 时间解析失败 %s | 周末跳过 %s",
        stats["added"],
        stats["skipped_old"],
        stats["date_parse_failed"],
        stats["skipped_weekend"],
    )
    return papers


def fetch_all_papers() -> List[ContentItem]:
    """获取所有论文源的数据"""
    all_papers = []
    
    # HuggingFace
    hf_papers = fetch_huggingface_papers()
    all_papers.extend(hf_papers)
    
    # arXiv
    arxiv_papers = fetch_arxiv_papers()
    all_papers.extend(arxiv_papers)
    
    # 去重 (基于标题相似度简单去重)
    seen_titles = set()
    unique_papers = []
    for paper in all_papers:
        title_key = paper.title.lower()[:50]  # 用前50字符作为key
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_papers.append(paper)
    
    logger.info(f"[Papers] 总计获取 {len(unique_papers)} 篇去重后的论文")
    return unique_papers
