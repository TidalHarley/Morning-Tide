"""
AI Tides - L1 启发式过滤器
Cost: $0 - 纯 Python 规则过滤

这个模块实现了 Pipeline 的第一级过滤，使用纯 Python 规则进行快速筛选。
目的是在调用昂贵的 AI API 之前，先过滤掉明显不符合要求的内容。
"""
import logging  # 用于记录日志，追踪过滤过程
import re  # 正则表达式库，用于关键词匹配
from typing import List, Tuple  # 类型提示，List 表示列表，Tuple 表示元组
from urllib.parse import urlparse  # URL 解析工具，用于提取域名

from ..models import ContentItem, ContentType, SourceType  # ..表示上一级目录
from ..config import config  # 导入配置（关键词列表、阈值等）

# 创建日志记录器，用于输出过滤过程的详细信息
logger = logging.getLogger(__name__)


class HeuristicFilter:
    """
    L1 启发式过滤器类
    
    功能：
    - 关键词匹配：检查内容是否包含 AI 相关关键词
    - 热度阈值：根据社区评分（HN score、HF upvotes）过滤
    - 白名单直通：官方博客等可信来源直接通过
    
    设计理念：
    这是一个"快速失败"的过滤器，优先过滤掉不符合条件的内容，
    减少后续 AI API 调用的成本。
    """
    
    def __init__(self):
        """
        初始化过滤器
        
        在这里预编译正则表达式，避免在每次过滤时重复编译，提高性能。
        """
        # 步骤 1: 构建关键词正则表达式模式
        # 将配置中的所有 AI 关键词用 "|" 连接，形成 "关键词1|关键词2|关键词3" 的模式
        # 例如: "AI|LLM|GPT|Transformer|..."
        keywords_pattern = "|".join(
            re.escape(kw) for kw in config.ai_keywords  # re.escape 转义特殊字符，避免正则错误
        )
        # 步骤 2: 编译正则表达式（不区分大小写）
        # re.IGNORECASE 表示匹配时不区分大小写
        # 例如: "AI" 可以匹配 "ai", "Ai", "aI"
        # 预编译后可以重复使用，性能更好
        self.keyword_regex = re.compile(keywords_pattern, re.IGNORECASE)
        
        # 步骤 3: 从配置中获取噪音关键词（强噪音 + 中文强噪音）
        # 强噪音：命中就过滤，直接拒绝低质量内容
        # 合并英文和中文的强噪音关键词
        all_hard_noise = config.hard_noise_keywords + config.hard_noise_keywords_zh
        
        # 步骤 4: 编译强噪音关键词正则表达式
        # 使用 "|" 连接所有强噪音关键词，用于检测内容中是否包含强噪音
        # 如果匹配到任何一个强噪音关键词，直接过滤
        self.hard_noise_regex = re.compile(
            "|".join(re.escape(kw) for kw in all_hard_noise),
            re.IGNORECASE
        )
        
        # 步骤 5: 编译噪音正则表达式模式
        # 这些正则用于匹配常见的标题公式（如 "Top 10 ways", "Ultimate guide"）
        # 预编译所有正则模式，提高匹配性能
        self.noise_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in config.noise_regex
        ]
    
    def _check_keywords(self, item: ContentItem) -> bool:
        """
        检查内容是否包含 AI 相关关键词
        
        参数:
            item: ContentItem 对象，包含标题和摘要
        
        返回:
            bool: True 表示包含关键词(通过), False 表示不包含（过滤）
        
        示例:
            >>> item = ContentItem(title="GPT-5: A New Breakthrough", ...)
            >>> filter._check_keywords(item)
            True  # 因为包含 "GPT" 关键词
            
            >>> item = ContentItem(title="How to Cook Pasta", ...)
            >>> filter._check_keywords(item)
            False  # 不包含任何 AI 关键词
        """
        # 将标题和摘要合并成一个文本字符串
        # item.abstract or '' 表示如果摘要为空，则使用空字符串
        text = f"{item.title} {item.abstract or ''}"
        
        # 使用预编译的正则表达式搜索文本
        # search() 返回 Match 对象（找到）或 None（未找到）
        # bool() 将结果转换为 True/False
        return bool(self.keyword_regex.search(text))
    
    def _check_not_noise(self, item: ContentItem) -> bool:
        """
        检查内容是否不是低质量噪音内容
        
        过滤策略（按优先级）：
        1. 强噪音关键词：一旦匹配到任何一个强噪音关键词，直接过滤
        2. 正则模式匹配：匹配到标题公式模式（如 "Top 10 ways"），直接过滤
        
        参数:
            item: ContentItem 对象
        
        返回:
            bool: True 表示不是噪音(通过), False 表示是噪音（过滤）
        
        示例:
            >>> item = ContentItem(title="Introduction to AI Tutorial for Beginners", ...)
            >>> filter._check_not_noise(item)
            False  # 包含强噪音词 "Introduction", "Tutorial", "Beginners"
            
            >>> item = ContentItem(title="Top 10 Ways to Learn AI", ...)
            >>> filter._check_not_noise(item)
            False  # 匹配正则模式 "Top 10 ways"
            
            >>> item = ContentItem(title="SOTA Model Achieves Breakthrough", ...)
            >>> filter._check_not_noise(item)
            True  # 不包含任何强噪音关键词或模式
        """
        # 合并标题和摘要（也包含 URL，因为营销链接可能包含噪音词）
        text = f"{item.title} {item.url or ''} {item.abstract or ''}".lower()
        
        # 检查 1: 强噪音关键词匹配
        # 如果匹配到任何一个强噪音关键词，直接返回 False（过滤）
        if self.hard_noise_regex.search(text):
            return False
        
        # 检查 2: 正则模式匹配
        # 检查是否匹配常见的标题公式模式
        # 例如: "Top 10 ways", "Ultimate guide", "Checklist" 等
        for pattern in self.noise_patterns:
            if pattern.search(text):
                return False
        
        # 所有检查都通过，不是噪音内容
        return True
    
    def _check_score_threshold(self, item: ContentItem) -> bool:
        """
        检查内容的社区热度是否达到阈值
        
        不同来源有不同的评分机制：
        - HuggingFace Papers: upvotes(点赞数)
        - arXiv Papers: 无评分，默认通过
        - Hacker News: score(分数)
        - RSS Feeds(official blog): 无评分，默认通过
        
        参数:
            item: ContentItem 对象，包含 score 和 source_type
        
        返回:
            bool: True 表示热度达标(通过), False 表示热度不足（过滤）
        
        示例:
            >>> # HuggingFace 论文, score=80, 阈值=5
            >>> item = ContentItem(score=80, source_type=SourceType.HUGGINGFACE, ...)
            >>> filter._check_score_threshold(item)
            True  # 80 >= 5, 通过
            
            >>> # Hacker News, score=5, 阈值=10
            >>> item = ContentItem(score=5, source_type=SourceType.HACKERNEWS, ...)
            >>> filter._check_score_threshold(item)
            False  # 5 < 10, 不通过
            
            >>> # arXiv 论文, 无评分
            >>> item = ContentItem(score=0, source_type=SourceType.ARXIV, ...)
            >>> filter._check_score_threshold(item)
            True  # arXiv 默认通过
        """
        # 判断内容类型：论文还是新闻
        if item.content_type == ContentType.PAPER:
            # 论文类型：检查来源
            # arXiv 论文没有社区评分机制，所以默认通过
            # 这样可以确保重要的新论文不会被遗漏
            if item.source_type.value == "arxiv":
                return True
            
            # HuggingFace 论文：检查 upvotes 是否达到阈值
            # config.min_hf_upvotes 默认值为 5
            # 例如: score=10 >= 5，通过；score=3 < 5，不通过
            return item.score >= config.min_hf_upvotes
        
        # 新闻类型：检查来源
        if item.content_type == ContentType.NEWS:
            # RSS Feed 通常没有评分机制，默认通过
            # 因为 RSS 来源通常是官方博客，质量有保障
            if item.source_type.value == "rss":
                return True

            # Reddit：使用独立阈值
            if item.source_type.value == "reddit":
                return item.score >= config.reddit_min_upvotes

            # GitHub Trending：默认通过（已在采集时过滤）
            if item.source_type.value == "github":
                return True
            
            # Hacker News：检查 score 是否达到阈值
            # config.min_hn_score 默认值为 10
            # 例如: score=15 >= 10，通过；score=8 < 10，不通过
            return item.score >= config.min_hn_score
        
        # 其他未知类型，默认通过（避免误过滤）
        return True
    
    def _check_whitelist(self, item: ContentItem) -> bool:
        """
        检查内容是否来自白名单域名
        
        白名单来源（如 OpenAI、Anthropic 官方博客）直接通过 L1 和 L2,
        直接进入 L3 精炼阶段，因为这些来源的内容质量有保障。
        
        参数:
            item: ContentItem 对象，包含 url 和 is_whitelist 标志
        
        返回:
            bool: True 表示是白名单(直通),False 表示不是（需要正常过滤）
        
        示例:
            >>> # 已标记为白名单
            >>> item = ContentItem(is_whitelist=True, url="https://openai.com/blog/...")
            >>> filter._check_whitelist(item)
            True
            
            >>> # URL 匹配白名单域名
            >>> item = ContentItem(url="https://blog.anthropic.com/news", ...)
            >>> filter._check_whitelist(item)
            True  # "anthropic.com" 在白名单中
            
            >>> # 普通来源
            >>> item = ContentItem(url="https://example.com/news", ...)
            >>> filter._check_whitelist(item)
            False
        """
        # 如果已经标记为白名单，直接返回 True
        # 这个标志可能在数据摄取阶段就已经设置
        if item.is_whitelist:
            return True
        
        # 如果 URL 存在，检查域名是否在白名单中
        if item.url:
            # urlparse() 解析 URL，提取域名部分
            # 例如: "https://openai.com/blog/gpt-5" -> "openai.com"
            # .lower() 转换为小写，确保匹配不区分大小写
            domain = urlparse(item.url).netloc.lower()
            
            # 遍历配置中的白名单域名列表
            # config.whitelist_domains 包含: ["openai.com", "anthropic.com", ...]
            for wl_domain in config.whitelist_domains:
                normalized = (wl_domain or "").strip().lower()
                if not normalized:
                    continue
                # 精确域名或子域后缀匹配（避免子串误命中）
                # 例如: "blog.openai.com" 匹配 "openai.com"
                if domain == normalized or domain.endswith(f".{normalized}"):
                    return True
        
        # 不匹配任何白名单条件，返回 False
        return False
    
    def filter_papers(self, papers: List[ContentItem]) -> Tuple[List[ContentItem], List[ContentItem]]:
        """
        过滤论文列表
        
        过滤流程（按顺序执行）：
        1. 白名单检查 → 如果通过，直接加入白名单列表，跳过后续检查
        2. 关键词检查 → 必须包含 AI 相关关键词
        3. 噪音过滤 → 不能包含过多低质量标识词
        4. 热度检查 → 社区评分必须达到阈值
        
        参数:
            papers: 待过滤的论文列表
        
        返回:
            Tuple[List[ContentItem], List[ContentItem]]: 
            - 第一个列表：通过正常过滤流程的论文
            - 第二个列表：白名单直通的论文
        
        示例:
            >>> papers = [
            ...     ContentItem(title="GPT-5: Breakthrough", score=100, ...),  # 正常通过
            ...     ContentItem(title="OpenAI Blog Post", url="openai.com/...", ...),  # 白名单
            ...     ContentItem(title="Random Topic", score=1, ...)  # 被过滤
            ... ]
            >>> passed, whitelist = filter.filter_papers(papers)
            >>> len(passed)
            1  # 只有第一个通过正常过滤
            >>> len(whitelist)
            1  # 第二个是白名单
        """
        # 初始化两个列表：
        # passed: 通过正常过滤流程的论文
        # whitelist_fast_track: 白名单直通的论文（跳过 L1/L2，直接进入 L3）
        passed = []
        whitelist_fast_track = []
        
        # 遍历每篇论文
        for paper in papers:
            # 步骤 1: 检查白名单（优先级最高）
            # 白名单内容直接通过，不需要进行后续检查
            if self._check_whitelist(paper):
                # 标记为白名单
                paper.is_whitelist = True
                # 标记已通过 L1（虽然跳过了检查，但标记为通过）
                paper.l1_passed = True
                # 加入白名单列表
                whitelist_fast_track.append(paper)
                # 跳过后续检查，处理下一篇
                continue
            
            # 步骤 2: 关键词检查
            # 如果标题和摘要中不包含任何 AI 相关关键词，则过滤掉
            if not self._check_keywords(paper):
                continue  # 跳过这篇论文，不加入任何列表
            
            # 步骤 3: 噪音过滤
            # 如果包含过多低质量标识词（如 "tutorial", "beginner"），则过滤掉
            if not self._check_not_noise(paper):
                continue  # 跳过这篇论文
            
            # 步骤 4: 热度检查
            # 检查社区评分（upvotes/score）是否达到阈值
            if not self._check_score_threshold(paper):
                continue  # 跳过这篇论文
            
            # 所有检查都通过，标记为已通过 L1
            paper.l1_passed = True
            # 加入通过列表，进入 L2 AI 打分阶段
            passed.append(paper)
        
        # 记录过滤结果日志
        # 格式: "[L1-Papers] 100 -> 25 通过, 5 白名单直通"
        logger.info(
            f"[L1-Papers] {len(papers)} -> {len(passed)} 通过, "
            f"{len(whitelist_fast_track)} 白名单直通"
        )
        
        # 返回两个列表：正常通过的 + 白名单直通的
        return passed, whitelist_fast_track
    
    def filter_news(self, news: List[ContentItem]) -> Tuple[List[ContentItem], List[ContentItem]]:
        """
        过滤新闻列表
        
        过滤流程与 filter_papers() 完全相同，但针对新闻类型。
        主要区别在于热度阈值的判断逻辑(HN score vs HF upvotes)。
        
        参数:
            news: 待过滤的新闻列表
        
        返回:
            Tuple[List[ContentItem], List[ContentItem]]: 
            - 第一个列表：通过正常过滤流程的新闻
            - 第二个列表：白名单直通的新闻
        
        示例:
            >>> news = [
            ...     ContentItem(title="Anthropic Releases Claude 4", url="anthropic.com/...", ...),  # 白名单
            ...     ContentItem(title="AI Breakthrough News", score=50, ...),  # 正常通过
            ...     ContentItem(title="Random Tech News", score=3, ...)  # 被过滤（分数太低）
            ... ]
            >>> passed, whitelist = filter.filter_news(news)
            >>> len(passed)
            1
            >>> len(whitelist)
            1
        """
        # 初始化两个列表
        passed = []
        whitelist_fast_track = []
        
        # 遍历每条新闻
        for item in news:
            # 步骤 1: 检查白名单
            # 官方博客等可信来源直接通过
            if self._check_whitelist(item):
                item.is_whitelist = True
                item.l1_passed = True
                whitelist_fast_track.append(item)
                continue
            
            # 步骤 2: 关键词检查
            # 必须包含 AI 相关关键词
            if not self._check_keywords(item):
                continue
            
            # 步骤 3: 噪音过滤
            # 过滤掉低质量内容（教程、入门指南等）
            if not self._check_not_noise(item):
                continue
            
            # 步骤 4: 热度检查
            # HN 新闻需要 score >= 10，RSS 默认通过
            if not self._check_score_threshold(item):
                continue
            
            # 所有检查通过
            item.l1_passed = True
            passed.append(item)
        
        # 记录过滤结果日志
        logger.info(
            f"[L1-News] {len(news)} -> {len(passed)} 通过, "
            f"{len(whitelist_fast_track)} 白名单直通"
        )
        
        # 返回两个列表
        return passed, whitelist_fast_track
    
    def run(
        self, 
        papers: List[ContentItem], 
        news: List[ContentItem]
    ) -> dict:
        """
        运行完整的 L1 过滤流程
        这是对外的主要接口，同时处理论文和新闻，返回分类后的结果。
        结果会被传递给 L2 AI 打分器。
        
        参数:
            papers: 待过滤的论文列表
            news: 待过滤的新闻列表
        
        返回:
            dict: 包含四个列表的字典
            {
                "papers_l2": 通过正常过滤的论文(进入 L2)
                "papers_whitelist": 白名单直通的论文(跳过 L2, 进入 L3)
                "news_l2": 通过正常过滤的新闻(进入 L2)
                "news_whitelist": 白名单直通的新闻(跳过 L2, 进入 L3)
            }
        
        示例:
            >>> filter = HeuristicFilter()
            >>> papers = [ContentItem(...), ...]
            >>> news = [ContentItem(...), ...]
            >>> result = filter.run(papers, news)
            >>> result["papers_l2"]
            [ContentItem(...), ...]  # 正常通过的论文
            >>> result["papers_whitelist"]
            [ContentItem(...), ...]  # 白名单论文
        """
        # 分别过滤论文和新闻
        # filter_papers() 返回 (正常通过列表, 白名单列表)
        papers_passed, papers_whitelist = self.filter_papers(papers)
        # filter_news() 返回 (正常通过列表, 白名单列表)
        news_passed, news_whitelist = self.filter_news(news)

        # L1 论文统计：三类总数 + 来源拆分
        l1_papers = papers_passed + papers_whitelist
        categories = getattr(config, "paper_categories", None) or [
            "General AI",
            "Computer Vision",
            "Robotics",
        ]
        category_counts = {category: 0 for category in categories}
        for item in l1_papers:
            category = item.paper_category or "General AI"
            if category in category_counts:
                category_counts[category] += 1

        hf_papers = [p for p in l1_papers if p.source_type == SourceType.HUGGINGFACE]
        arxiv_papers = [p for p in l1_papers if p.source_type == SourceType.ARXIV]

        def _format_titles(items: List[ContentItem], limit: int = 25) -> str:
            titles = [it.title for it in items if it.title]
            if len(titles) <= limit:
                return " | ".join(titles)
            shown = " | ".join(titles[:limit])
            return f"{shown} ... (还有 {len(titles) - limit} 条)"

        logger.info(
            "[L1-Papers] 三类合计: %s | General AI=%s, Computer Vision=%s, Robotics=%s",
            len(l1_papers),
            category_counts.get("General AI", 0),
            category_counts.get("Computer Vision", 0),
            category_counts.get("Robotics", 0),
        )
        logger.info(
            "[L1-Papers] 来源拆分: HuggingFace=%s, arXiv=%s",
            len(hf_papers),
            len(arxiv_papers),
        )
        if hf_papers:
            logger.info("[L1-Papers] HuggingFace: %s", _format_titles(hf_papers))
        if arxiv_papers:
            logger.info("[L1-Papers] arXiv: %s", _format_titles(arxiv_papers))
        
        # 返回结构化的结果字典
        # 这个字典会被传递给 L2 AI 打分器
        return {
            "papers_l2": papers_passed,           # 论文：进入 L2 打分
            "papers_whitelist": papers_whitelist, # 论文：跳过 L2，进入 L3
            "news_l2": news_passed,                # 新闻：进入 L2 打分
            "news_whitelist": news_whitelist      # 新闻：跳过 L2，进入 L3
        }
