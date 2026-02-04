"""
AI Tides - 主程序入口
整合所有 Pipeline 阶段
"""
import logging
import sys
import os
from collections import defaultdict
import re
from datetime import datetime, timedelta, timezone

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.ingestion import fetch_all_papers, fetch_all_news
from pipeline.filters import HeuristicFilter, AIScorer, Refiner, Deduplicator
from pipeline.enrichment.fulltext import enrich_news_full_text
from pipeline.output import OutputGenerator
from pipeline.config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def run_pipeline(dry_run: bool = False):
    """运行完整的 AI Tides Pipeline"""
    
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("🌊 AI Tides Pipeline 启动")
    logger.info(f"📅 日期: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    stats = {}
    
    # ========================================
    # Phase 1: 数据摄取
    # ========================================
    logger.info("\n📥 Phase 1: 数据摄取...")
    
    # 获取论文
    logger.info("正在获取论文...")
    papers = fetch_all_papers()
    stats["total_papers_ingested"] = len(papers)
    
    # 获取新闻
    logger.info("正在获取新闻...")
    news = fetch_all_news()
    stats["total_news_ingested"] = len(news)

    def _normalize_title(title: str) -> str:
        text = (title or "").lower().strip()
        text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    source_counts = defaultdict(int)
    rss_counts = defaultdict(int)
    title_sources = defaultdict(set)
    for item in news:
        source_name = item.source_name or "Unknown"
        source_counts[source_name] += 1
        if getattr(item, "source_type", None) and item.source_type.value == "rss":
            rss_counts[source_name] += 1
        title_key = _normalize_title(item.title or "")
        if title_key:
            title_sources[title_key].add(source_name)

    stats["news_source_counts"] = dict(
        sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
    )
    stats["rss_source_counts"] = dict(
        sorted(rss_counts.items(), key=lambda x: x[1], reverse=True)
    )
    stats["news_title_source_counts"] = {
        k: len(v) for k, v in title_sources.items()
    }

    # 去重（URL）
    deduplicator = Deduplicator()
    papers = deduplicator.deduplicate_by_url(papers)
    news = deduplicator.deduplicate_by_url(news)
    stats["total_papers_deduped"] = len(papers)
    stats["total_news_deduped"] = len(news)
    
    logger.info(f"✅ 摄取完成 - 论文: {len(papers)}, 新闻: {len(news)}")

    # 最终兜底：严格保证“过去 24 小时内”的新闻才进入后续阶段
    # 说明：各 ingestion 已做 cutoff，但不同源可能时间字段缺失/解析异常，这里做统一硬约束。
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=config.hours_lookback)
    dropped_no_time = 0
    dropped_old = 0
    recent_news = []
    for item in news:
        published_at = getattr(item, "published_at", None)
        if not published_at:
            dropped_no_time += 1
            continue
        if published_at.tzinfo is None:
            # 避免 naive datetime 误判：默认按 UTC 处理
            published_at = published_at.replace(tzinfo=timezone.utc)
        if published_at < cutoff:
            dropped_old += 1
            continue
        recent_news.append(item)
    if dropped_no_time or dropped_old:
        logger.info(
            f"[Recency] 新闻时间窗口过滤({config.hours_lookback}h): "
            f"{len(news)} -> {len(recent_news)} (无时间: {dropped_no_time}, 过期: {dropped_old})"
        )
    news = recent_news
    stats["news_recent_filtered"] = len(news)

    # ========================================
    # Phase 1.5: 新闻全文抓取（供 L2/L3 使用）
    # ========================================
    logger.info("\n🧾 Phase 1.5: 新闻全文抓取...")
    news = enrich_news_full_text(news)
    
    # ========================================
    # Phase 2: 三级过滤漏斗
    # ========================================
    logger.info("\n🔍 Phase 2: 三级过滤漏斗...")
    
    # L1: 启发式过滤
    logger.info("\n[L1] 启发式过滤...")
    heuristic_filter = HeuristicFilter()
    l1_result = heuristic_filter.run(papers, news)
    
    stats["l1_papers_passed"] = len(l1_result["papers_l2"]) + len(l1_result["papers_whitelist"])
    stats["l1_news_passed"] = len(l1_result["news_l2"]) + len(l1_result["news_whitelist"])
    
    # L2: AI 打分
    logger.info("\n[L2] AI 智能打分...")
    ai_scorer = AIScorer()
    l2_result = ai_scorer.run(
        papers_l2=l1_result["papers_l2"],
        papers_whitelist=l1_result["papers_whitelist"],
        news_l2=l1_result["news_l2"],
        news_whitelist=l1_result["news_whitelist"]
    )

    # L2 后做新闻语义去重（使用 L2 综合分进行 rank），再取 Top news 进入 L3
    logger.info("\n[Dedup] L2 后新闻语义去重...")
    news_l3 = deduplicator.deduplicate_semantic(l2_result["news_l3_all"])
    news_l3.sort(key=lambda x: x.l2_combined_score, reverse=True)
    news_l3 = news_l3[: config.l2_news_limit]
    
    # L3: 深度精炼
    logger.info("\n[L3] 深度精炼...")
    refiner = Refiner()
    report = refiner.run(
        papers_l3=l2_result["papers_l3"],
        news_l3=news_l3
    )
    
    # 更新统计信息
    report.stats.update(stats)
    
    # ========================================
    # Phase 3: 输出生成
    # ========================================
    logger.info("\n📤 Phase 3: 生成输出...")
    
    output_generator = OutputGenerator()
    
    if not dry_run:
        output_paths = output_generator.save_report(report)
    else:
        logger.info("🔍 干运行模式：跳过文件保存")
        output_paths = {}
    
    # ========================================
    # 完成
    # ========================================
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "=" * 60)
    logger.info("🎉 Pipeline 执行完成!")
    logger.info(f"⏱️  耗时: {duration:.2f} 秒")
    logger.info(f"📊 最终结果: {len(report.papers)} 篇论文, {len(report.news)} 条新闻")
    logger.info("=" * 60)
    
    # 打印输出路径
    if output_paths:
        logger.info("\n📁 输出文件:")
        for key, path in output_paths.items():
            if path:
                logger.info(f"   {key}: {path}")
    
    # 打印精选内容预览
    if report.papers:
        logger.info("\n📚 精选论文预览:")
        for i, paper in enumerate(report.papers[:3], 1):
            logger.info(f"   {i}. {paper.title[:60]}...")
    
    if report.news:
        logger.info("\n📰 精选新闻预览:")
        for i, news_item in enumerate(report.news[:3], 1):
            logger.info(f"   {i}. {news_item.title[:60]}...")
    
    return report


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Tides Pipeline")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="开启调试模式（更详细的日志）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干运行模式（不保存输出）"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("调试模式已开启")
    
    try:
        report = run_pipeline(dry_run=args.dry_run)
        return 0
    except Exception as e:
        logger.error(f"❌ Pipeline 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
