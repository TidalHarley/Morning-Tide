"""
AI Tides - 每日简报长图生成模块
将当日精选新闻渲染为精美 PNG 长图（中/英双语），用于社交媒体传播。

技术路线: Jinja2 渲染 HTML → Playwright 无头 Chromium 截图 → PNG
"""
import asyncio
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from .config import config
from .models import ContentItem, DailyReport

logger = logging.getLogger(__name__)

# ── 模板目录 ──────────────────────────────────────────────────────
TEMPLATE_DIR = Path(__file__).parent / "templates"

# ── 月份名 ────────────────────────────────────────────────────────
MONTH_EN = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_ZH = [
    "", "一月", "二月", "三月", "四月", "五月", "六月",
    "七月", "八月", "九月", "十月", "十一月", "十二月",
]
WEEKDAY_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAY_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _parse_date(date_str: str) -> datetime:
    """将 YYYY-MM-DD 解析为 datetime 对象。"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return datetime.now()


def _relative_time(published_at: Optional[datetime], lang: str) -> str:
    """生成人类可读的相对时间（如 '3h ago' / '3小时前'）。"""
    if not published_at:
        return ""
    try:
        now = datetime.now(published_at.tzinfo) if published_at.tzinfo else datetime.now()
        delta = now - published_at
        hours = int(delta.total_seconds() / 3600)
        if hours < 1:
            return "刚刚" if lang == "zh" else "just now"
        if hours < 24:
            return f"{hours}小时前" if lang == "zh" else f"{hours}h ago"
        days = hours // 24
        if days == 1:
            return "昨天" if lang == "zh" else "yesterday"
        return f"{days}天前" if lang == "zh" else f"{days}d ago"
    except Exception:
        return ""


def _normalize_for_dedup(title: str) -> str:
    """将标题转为小写并去除标点空格，用于去重比较。"""
    text = (title or "").lower().strip()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", text)
    return text


def _is_valid_image_url(url: Optional[str]) -> bool:
    """检查图片 URL 是否可用于显示。"""
    if not url:
        return False
    url = url.strip()
    if url.startswith(("http://", "https://")):
        return True
    return False


def _prepare_news_items(
    report: DailyReport, lang: str, max_items: int
) -> List[dict]:
    """
    从 report 中提取新闻并按影响力排序，去重后返回模板所需的 dict 列表。
    只取前 max_items 条。包含图片 URL 和完整摘要。
    """
    news = sorted(report.news, key=lambda n: n.l2_combined_score, reverse=True)

    # 按标题去重（保留分数最高的那条）
    seen_titles: set = set()
    deduped: List[ContentItem] = []
    for item in news:
        norm = _normalize_for_dedup(item.title)
        if norm and norm in seen_titles:
            continue
        seen_titles.add(norm)
        deduped.append(item)
    news = deduped[:max_items]

    items = []
    for item in news:
        title = (item.title_zh or item.title) if lang == "zh" else (item.title_en or item.title)
        summary = (item.summary_zh or item.abstract or "") if lang == "zh" else (item.summary_en or item.abstract or "")

        # 允许较长摘要以保证内容可读性
        # Hero 条目允许更长，但一般也做合理截断
        max_len = 220
        if len(summary) > max_len:
            summary = summary[:max_len - 3].rstrip(".,;，。；ﾠ ") + "..."

        # 图片 URL
        image_url = item.image_url or ""
        if not _is_valid_image_url(image_url):
            image_url = ""

        items.append({
            "title": title,
            "summary": summary,
            "image": image_url,
            "tags": (item.tags or [])[:3],
            "source": item.source_name or "",
            "time": _relative_time(item.published_at, lang),
        })
    return items


def _render_html(report: DailyReport, lang: str) -> str:
    """使用 Jinja2 渲染简报 HTML。"""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    template = env.get_template("briefing.html")

    dt = _parse_date(report.date)
    weekday = WEEKDAY_ZH[dt.weekday()] if lang == "zh" else WEEKDAY_EN[dt.weekday()]

    if lang == "zh":
        subtitle = "AI 每日简报"
        powered_by = "由 AI Tides 智能聚合驱动"
        top_stories_label = "今日要闻"
        date_full = f"{dt.year} 年 {dt.month} 月 {dt.day} 日 · {weekday}"
        intro = report.introduction_zh or report.introduction or ""
    else:
        subtitle = "AI Daily Briefing"
        powered_by = "Powered by AI Tides"
        top_stories_label = "Top Stories"
        date_full = f"{MONTH_EN[dt.month]} {dt.day}, {dt.year} · {weekday}"
        # 仅使用英文版简介；如果没有则留空（不回退到中文）
        intro = report.introduction_en or ""

    # 简介合理截取
    if len(intro) > 200:
        intro = intro[:197].rstrip(".,;，。；") + "..."

    news_items = _prepare_news_items(report, lang, config.briefing_max_news)

    return template.render(
        lang=lang,
        subtitle=subtitle,
        date_full=date_full,
        introduction=intro,
        top_stories_label=top_stories_label,
        news=news_items,
        site_url=config.briefing_site_url or "",
        powered_by=powered_by,
    )


async def _screenshot_html(html: str, output_path: str, width: int = 1080) -> str:
    """使用 Playwright 将 HTML 截图为 PNG。等待远程图片和字体加载完成。"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": width, "height": 800},
            device_scale_factor=2,  # 2x 高清输出
        )
        page = await context.new_page()

        # 设置内容并等待网络空闲（字体 + 远程图片）
        await page.set_content(html, wait_until="networkidle")
        # 额外等待确保所有图片渲染完毕
        await page.wait_for_timeout(2500)

        # 再次等待所有 <img> 元素加载完成
        await page.evaluate("""
            () => Promise.all(
                Array.from(document.images)
                    .filter(img => !img.complete)
                    .map(img => new Promise((resolve) => {
                        img.onload = img.onerror = resolve;
                    }))
            )
        """)
        await page.wait_for_timeout(500)

        # 获取实际内容高度并调整 viewport
        body_height = await page.evaluate("document.body.scrollHeight")
        await page.set_viewport_size({"width": width, "height": body_height})
        await page.wait_for_timeout(300)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        await page.screenshot(path=output_path, full_page=True, type="png")

        await context.close()
        await browser.close()

    logger.info(f"[Briefing] 截图已保存: {output_path}")
    return output_path


def generate_briefing_images(report: DailyReport) -> Dict[str, str]:
    """
    为当日报告生成中/英双语简报长图。

    返回 dict: {"briefing_zh": path, "briefing_en": path}
    """
    if not report.news:
        logger.info("[Briefing] 今日无新闻，跳过简报生成")
        return {}

    date_str = report.date
    output_dir = config.output_dir
    public_dir = config.briefing_output_dir

    paths: Dict[str, str] = {}

    for lang in ("zh", "en"):
        html = _render_html(report, lang)

        # 保存到 pipeline/output/
        out_name = f"briefing_{lang}_{date_str}.png"
        out_path = os.path.join(output_dir, out_name)

        # 运行异步截图
        try:
            asyncio.run(_screenshot_html(html, out_path, config.briefing_width))
        except RuntimeError:
            # 如果已经有 event loop 在运行（例如 Jupyter 环境）
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_screenshot_html(html, out_path, config.briefing_width))

        paths[f"briefing_{lang}"] = out_path

        # 同步到 public 目录
        if public_dir:
            os.makedirs(public_dir, exist_ok=True)
            pub_path = os.path.join(public_dir, out_name)
            try:
                import shutil
                shutil.copy2(out_path, pub_path)
                logger.info(f"[Briefing] Public 副本已保存: {pub_path}")
            except Exception as e:
                logger.warning(f"[Briefing] 复制到 public 目录失败: {e}")

    return paths
