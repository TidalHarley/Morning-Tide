"""
AI Tides - 调试工具
提供本地调试和测试功能
"""
import logging
import json
import argparse
from datetime import datetime, timedelta, timezone
from typing import List

from pipeline.models import ContentItem, ContentType, SourceType
from pipeline.filters import HeuristicFilter, AIScorer, Refiner
from pipeline.output import OutputGenerator
from pipeline.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def create_mock_data() -> tuple[List[ContentItem], List[ContentItem]]:
    """创建模拟数据用于测试"""
    
    now = datetime.now(timezone.utc)
    
    # 模拟论文
    mock_papers = [
        ContentItem(
            id="mock_paper_1",
            title="GPT-5: A Revolutionary Large Language Model",
            url="https://example.com/paper1",
            content_type=ContentType.PAPER,
            source_type=SourceType.ARXIV,
            source_name="arXiv",
            abstract="This paper introduces GPT-5, a state-of-the-art language model with breakthrough capabilities.",
            authors=["OpenAI Research"],
            published_at=now - timedelta(hours=12),
            score=150
        ),
        ContentItem(
            id="mock_paper_2",
            title="Novel Transformer Architecture for Vision Tasks",
            url="https://example.com/paper2",
            content_type=ContentType.PAPER,
            source_type=SourceType.HUGGINGFACE,
            source_name="HuggingFace",
            abstract="We propose a new transformer architecture that achieves SOTA results on vision benchmarks.",
            authors=["DeepMind"],
            published_at=now - timedelta(hours=6),
            score=80
        ),
        ContentItem(
            id="mock_paper_3",
            title="Introduction to Machine Learning Tutorial",
            url="https://example.com/paper3",
            content_type=ContentType.PAPER,
            source_type=SourceType.ARXIV,
            source_name="arXiv",
            abstract="A beginner-friendly tutorial on machine learning basics.",
            authors=["Unknown"],
            published_at=now - timedelta(hours=3),
            score=5
        ),
    ]
    
    # 模拟新闻
    mock_news = [
        ContentItem(
            id="mock_news_1",
            title="OpenAI Announces GPT-5 Release",
            url="https://openai.com/blog/gpt-5",
            content_type=ContentType.NEWS,
            source_type=SourceType.RSS,
            source_name="OpenAI Blog",
            abstract="OpenAI has released GPT-5, their most advanced language model yet.",
            authors=[],
            published_at=now - timedelta(hours=8),
            score=500,
            is_whitelist=True
        ),
        ContentItem(
            id="mock_news_2",
            title="Anthropic Releases Claude 4 with Enhanced Reasoning",
            url="https://anthropic.com/news/claude-4",
            content_type=ContentType.NEWS,
            source_type=SourceType.RSS,
            source_name="Anthropic",
            abstract="Claude 4 introduces new reasoning capabilities.",
            authors=[],
            published_at=now - timedelta(hours=4),
            score=300,
            is_whitelist=True
        ),
        ContentItem(
            id="mock_news_3",
            title="How to Use ChatGPT: A Beginner's Guide",
            url="https://example.com/tutorial",
            content_type=ContentType.NEWS,
            source_type=SourceType.HACKERNEWS,
            source_name="Hacker News",
            abstract="Learn how to use ChatGPT with this simple tutorial.",
            authors=[],
            published_at=now - timedelta(hours=2),
            score=15
        ),
    ]
    
    return mock_papers, mock_news


def test_l1_filter():
    """测试 L1 启发式过滤"""
    logger.info("=" * 60)
    logger.info("🧪 测试 L1 启发式过滤")
    logger.info("=" * 60)
    
    papers, news = create_mock_data()
    
    filter_obj = HeuristicFilter()
    result = filter_obj.run(papers, news)
    
    logger.info(f"\n论文 L2: {len(result['papers_l2'])}")
    logger.info(f"论文白名单: {len(result['papers_whitelist'])}")
    logger.info(f"新闻 L2: {len(result['news_l2'])}")
    logger.info(f"新闻白名单: {len(result['news_whitelist'])}")
    
    return result


def test_l2_scorer():
    """测试 L2 AI 打分"""
    logger.info("=" * 60)
    logger.info("🧪 测试 L2 AI 打分")
    logger.info("=" * 60)
    
    papers, news = create_mock_data()
    
    # 先过 L1
    filter_obj = HeuristicFilter()
    l1_result = filter_obj.run(papers, news)
    
    # 再打分
    scorer = AIScorer()
    l2_result = scorer.run(
        papers_l2=l1_result["papers_l2"],
        papers_whitelist=l1_result["papers_whitelist"],
        news_l2=l1_result["news_l2"],
        news_whitelist=l1_result["news_whitelist"]
    )
    
    logger.info(f"\n论文 L3 候选: {len(l2_result['papers_l3'])}")
    for paper in l2_result['papers_l3']:
        logger.info(f"  - {paper.title[:50]}... (分数: {paper.l2_combined_score})")
    
    logger.info(f"\n新闻 L3 候选: {len(l2_result['news_l3'])}")
    for news_item in l2_result['news_l3']:
        logger.info(f"  - {news_item.title[:50]}... (分数: {news_item.l2_combined_score})")
    
    return l2_result


def test_full_pipeline(mock: bool = False):
    """测试完整 Pipeline"""
    logger.info("=" * 60)
    logger.info("🧪 测试完整 Pipeline")
    logger.info("=" * 60)
    
    if mock:
        logger.info("使用模拟数据")
        papers, news = create_mock_data()
    else:
        logger.info("使用真实数据")
        from pipeline.ingestion import fetch_all_papers, fetch_all_news
        papers = fetch_all_papers()
        news = fetch_all_news()
    
    # L1
    filter_obj = HeuristicFilter()
    l1_result = filter_obj.run(papers, news)
    
    # L2
    scorer = AIScorer()
    l2_result = scorer.run(
        papers_l2=l1_result["papers_l2"],
        papers_whitelist=l1_result["papers_whitelist"],
        news_l2=l1_result["news_l2"],
        news_whitelist=l1_result["news_whitelist"]
    )
    
    # L3
    refiner = Refiner()
    report = refiner.run(
        papers_l3=l2_result["papers_l3"],
        news_l3=l2_result["news_l3"]
    )
    
    # 输出
    output_gen = OutputGenerator()
    output_paths = output_gen.save_report(report)
    
    logger.info("\n✅ 测试完成!")
    logger.info(f"输出文件: {output_paths}")
    
    return report


def test_ingestion():
    """测试数据摄取"""
    logger.info("=" * 60)
    logger.info("🧪 测试数据摄取")
    logger.info("=" * 60)
    
    from pipeline.ingestion import fetch_all_papers, fetch_all_news
    
    logger.info("获取论文...")
    papers = fetch_all_papers()
    logger.info(f"✅ 获取到 {len(papers)} 篇论文")
    
    logger.info("\n获取新闻...")
    news = fetch_all_news()
    logger.info(f"✅ 获取到 {len(news)} 条新闻")
    
    # 显示前几条
    if papers:
        logger.info("\n前3篇论文:")
        for i, paper in enumerate(papers[:3], 1):
            logger.info(f"  {i}. {paper.title[:60]}...")
    
    if news:
        logger.info("\n前3条新闻:")
        for i, news_item in enumerate(news[:3], 1):
            logger.info(f"  {i}. {news_item.title[:60]}...")
    
    return papers, news


def main():
    parser = argparse.ArgumentParser(description="AI Tides 调试工具")
    parser.add_argument(
        "mode",
        choices=["l1", "l2", "full", "ingestion", "mock"],
        help="测试模式: l1=测试L1过滤, l2=测试L2打分, full=完整pipeline, ingestion=数据摄取, mock=使用模拟数据"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="开启调试模式（更详细的日志）"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        if args.mode == "l1":
            test_l1_filter()
        elif args.mode == "l2":
            test_l2_scorer()
        elif args.mode == "full":
            test_full_pipeline(mock=False)
        elif args.mode == "mock":
            test_full_pipeline(mock=True)
        elif args.mode == "ingestion":
            test_ingestion()
        
        return 0
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
