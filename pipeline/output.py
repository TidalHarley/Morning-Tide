"""
AI Tides - 输出生成模块
生成 Markdown 报告和 JSON 数据
"""
import json
import os
import logging
import re
from datetime import datetime
from typing import Optional

from .models import DailyReport, ContentItem
from .audio.rewrite import rewrite_audio_text
from .audio.tts import generate_daily_audio
from .config import config

logger = logging.getLogger(__name__)


class OutputGenerator:
    """输出生成器"""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or config.output_dir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _format_tags(self, tags: list) -> str:
        """格式化标签"""
        if not tags:
            return ""
        return " ".join([f"`{tag}`" for tag in tags])

    def _normalize_title(self, title: str) -> str:
        text = (title or "").lower().strip()
        text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _is_official_source(self, item: ContentItem) -> bool:
        if item.is_whitelist:
            return True
        if not item.url:
            return False
        try:
            from urllib.parse import urlparse

            domain = urlparse(item.url).netloc.lower()
        except Exception:
            domain = ""
        if not domain:
            return False
        for wl_domain in config.whitelist_domains:
            normalized = (wl_domain or "").strip().lower()
            if not normalized:
                continue
            if domain == normalized or domain.endswith(f".{normalized}"):
                return True
        return False

    def _build_signal_reasons(self, item: ContentItem, stats: dict) -> list:
        reasons = []
        # 来源权威
        if self._is_official_source(item):
            reasons.append("来源权威：官方/白名单")
        else:
            reasons.append(f"来源：{item.source_name or 'Unknown'}")

        # 跨源重复
        title_key = self._normalize_title(item.title or "")
        cross_map = stats.get("news_title_source_counts", {}) if isinstance(stats, dict) else {}
        if title_key and title_key in cross_map:
            reasons.append(f"跨源重复：{cross_map[title_key]} 个来源")
        else:
            reasons.append("跨源重复：1 个来源")

        # 模型评分依据
        if item.l2_reason:
            reasons.append(f"模型评分：{item.l2_score}/10，理由：{item.l2_reason}")
        else:
            reasons.append(f"模型评分：{item.l2_score}/10")

        # 引用/热度
        reasons.append(f"热度：{item.score} / 评论 {item.comments_count}")
        return reasons

    def _safe_image_url(self, url: str) -> str:
        value = (url or "").strip()
        if value.lower().startswith(("http://", "https://")):
            return value
        if value.startswith("/"):
            return value
        return ""
    
    def generate_markdown(self, report: DailyReport) -> str:
        """生成 Markdown 格式报告"""
        
        intro_zh = report.introduction_zh or report.introduction
        longform_zh = report.longform_script_zh or report.longform_script

        md = f"""# 🌊 AI Tides Daily Report
## {report.date}

> *Signal over Noise - 穿越喧嚣，直抵本质*

---

## 📝 今日综述

{intro_zh}

---

## 🎙️ 播客长文稿

{longform_zh or "（未生成）"}

---

## 📚 精选论文 ({len(report.papers)} 篇)

"""
        
        for i, paper in enumerate(report.papers, 1):
            tags = self._format_tags(paper.tags)
            summary = paper.summary_zh or ((paper.abstract[:150] + "...") if paper.abstract else (paper.title_zh or paper.title))
            authors = ", ".join(paper.authors[:3]) if paper.authors else "Unknown"
            display_title = paper.title_zh or paper.title
            
            md += f"""### {i}. {display_title}

{tags}

**来源:** {paper.source_name} | **作者:** {authors}

{summary}

🔗 [阅读原文]({paper.url})

---

"""
        
        md += f"""
## 📰 行业新闻 ({len(report.news)} 条)

"""
        
        for i, news in enumerate(report.news, 1):
            tags = self._format_tags(news.tags)
            summary = news.summary_zh or news.abstract or news.title
            display_title = news.title_zh or news.title
            
            md += f"""### {i}. {display_title}

{tags}

**来源:** {news.source_name}

{summary}

🔗 [阅读原文]({news.url})

---

"""
        
        # 添加统计信息
        stats = report.stats
        md += f"""
## 📊 Pipeline 统计

| 阶段 | 论文 | 新闻 |
|------|------|------|
| 摄取 | {stats.get('total_papers_ingested', 'N/A')} | {stats.get('total_news_ingested', 'N/A')} |
| L1 通过 | {stats.get('l1_papers_passed', 'N/A')} | {stats.get('l1_news_passed', 'N/A')} |
| L2 评分 | {stats.get('l2_papers_scored', 'N/A')} | {stats.get('l2_news_scored', 'N/A')} |
| L3 入选 | {stats.get('l3_papers_selected', 'N/A')} | {stats.get('l3_news_selected', 'N/A')} |

---

## 🧭 RSS 来源条数

"""
        rss_counts = stats.get("rss_source_counts", {})
        if isinstance(rss_counts, dict) and rss_counts:
            md += "| RSS 来源 | 条数 |\n|------|------|\n"
            for name, count in rss_counts.items():
                md += f"| {name} | {count} |\n"
        else:
            md += "暂无 RSS 来源统计。\n"

        md += f"""

*Generated by AI Tides Pipeline at {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC*
"""
        
        return md

    def generate_news_sources_markdown(self, report: DailyReport) -> str:
        stats = report.stats or {}
        counts = stats.get("news_source_counts", {})
        rss_counts = stats.get("rss_source_counts", {})
        lines = [
            "# 新闻来源统计",
            f"日期: {report.date}",
            "",
            "| 来源 | 数量 |",
            "|------|------|",
        ]
        if isinstance(counts, dict) and counts:
            for name, count in counts.items():
                lines.append(f"| {name} | {count} |")
        else:
            lines.append("| 无 | 0 |")
        lines.append("")

        lines.append("## RSS 来源条数")
        lines.append("")
        lines.append("| RSS 来源 | 数量 |")
        lines.append("|---------|------|")
        if isinstance(rss_counts, dict) and rss_counts:
            for name, count in rss_counts.items():
                lines.append(f"| {name} | {count} |")
        else:
            lines.append("| 无 | 0 |")
        lines.append("")
        return "\n".join(lines)
    
    def generate_json_for_frontend(self, report: DailyReport) -> dict:
        """生成前端所需的 JSON 数据"""
        
        def item_to_dict(item: ContentItem) -> dict:
            title_zh = item.title_zh or item.title
            title_en = item.title_en or item.title
            summary_zh = item.summary_zh or (item.abstract[:200] if item.abstract else item.title)
            summary_en = item.summary_en or (item.abstract[:200] if item.abstract else item.title)
            return {
                "id": item.id,
                "title": title_zh,
                "titleZh": title_zh,
                "titleEn": title_en,
                "url": item.url,
                "type": item.content_type.value,
                "source": item.source_name,
                "summary": summary_zh,
                "summaryZh": summary_zh,
                "summaryEn": summary_en,
                "fullText": item.full_text or "",
                "imageUrl": self._safe_image_url(item.image_url),
                "tags": item.tags,
                "paperCategory": item.paper_category or "",
                "signalReasons": self._build_signal_reasons(item, report.stats),
                "score": item.l2_combined_score,
                "publishedAt": item.published_at.isoformat() if item.published_at else None,
                "authors": item.authors
            }
        
        return {
            "date": report.date,
            "generatedAt": report.generated_at.isoformat(),
            "introduction": report.introduction_zh or report.introduction,
            "introductionZh": report.introduction_zh or report.introduction,
            "introductionEn": report.introduction_en or report.introduction,
            "longformScript": report.longform_script_zh or report.longform_script or "",
            "longformScriptZh": report.longform_script_zh or report.longform_script or "",
            "longformScriptEn": report.longform_script_en or "",
            "audioUrl": report.audio_url or "",
            "papers": [item_to_dict(p) for p in report.papers],
            "news": [item_to_dict(n) for n in report.news],
            "stats": report.stats
        }
    
    def save_report(self, report: DailyReport) -> dict:
        """保存报告到文件"""
        
        date_str = report.date
        
        # 保存 Markdown
        md_content = self.generate_markdown(report)
        md_path = os.path.join(self.output_dir, f"report_{date_str}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.info(f"[Output] Markdown 报告已保存: {md_path}")

        # 保存新闻来源统计
        sources_md = self.generate_news_sources_markdown(report)
        sources_path = os.path.join(self.output_dir, f"news_sources_{date_str}.md")
        with open(sources_path, "w", encoding="utf-8") as f:
            f.write(sources_md)
        logger.info(f"[Output] 新闻来源统计已保存: {sources_path}")
        
        # 生成播客音频（可选）
        audio_text = report.longform_script_zh or report.longform_script or report.introduction_zh or report.introduction
        audio_text = rewrite_audio_text(audio_text)
        audio_url = generate_daily_audio(audio_text, report.date)
        if audio_url:
            report.audio_url = audio_url

        # 保存 JSON (用于存档)
        json_data = self.generate_json_for_frontend(report)
        json_path = os.path.join(self.output_dir, f"report_{date_str}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        logger.info(f"[Output] JSON 报告已保存: {json_path}")
        
        # 保存到前端数据目录
        frontend_path = config.data_json_path
        frontend_dir = os.path.dirname(frontend_path)
        if os.path.exists(frontend_dir):
            with open(frontend_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            logger.info(f"[Output] 前端数据已更新: {frontend_path}")

        # 保存到 public reports 目录（用于前端日期切换）
        public_reports_dir = config.public_reports_dir
        if public_reports_dir:
            os.makedirs(public_reports_dir, exist_ok=True)
            public_report_path = os.path.join(public_reports_dir, f"report_{date_str}.json")
            with open(public_report_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            logger.info(f"[Output] Public 报告已保存: {public_report_path}")
        
        # 保存历史记录 (追加模式)
        history_path = os.path.join(self.output_dir, "history.json")
        history = []
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except:
                history = []
        
        # 添加今日记录摘要
        history_entry = {
            "date": date_str,
            "papers_count": len(report.papers),
            "news_count": len(report.news),
            "top_paper": (report.papers[0].title_zh or report.papers[0].title) if report.papers else None,
            "top_news": (report.news[0].title_zh or report.news[0].title) if report.news else None
        }
        
        # 避免重复
        history = [h for h in history if h["date"] != date_str]
        history.insert(0, history_entry)
        history = history[:30]  # 只保留最近30天
        
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        # 同步 history 到 public 目录
        public_history_path = config.public_history_path
        if public_history_path:
            public_history_dir = os.path.dirname(public_history_path)
            if public_history_dir:
                os.makedirs(public_history_dir, exist_ok=True)
            with open(public_history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            logger.info(f"[Output] Public history 已更新: {public_history_path}")
        
        output_paths = {
            "markdown_path": md_path,
            "json_path": json_path,
            "frontend_path": frontend_path if os.path.exists(frontend_dir) else None,
            "news_sources_path": sources_path,
        }

        # 生成每日简报长图（中/英双语 PNG）
        if config.briefing_enabled:
            try:
                from .briefing import generate_briefing_images
                briefing_paths = generate_briefing_images(report)
                output_paths.update(briefing_paths)
            except Exception as e:
                logger.warning(f"[Briefing] 简报图片生成失败（不影响其他输出）: {e}")

        return output_paths
