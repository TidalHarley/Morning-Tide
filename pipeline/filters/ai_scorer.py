"""
AI Tides - L2 AI 打分器
使用 Qwen Flash 对内容进行打分
"""
import logging
import json
from urllib.parse import urlparse
from typing import List, Optional, Dict
from tenacity import retry, stop_after_attempt, wait_exponential

from openai import OpenAI

from ..models import ContentItem, ContentType, SourceType
from ..config import config

logger = logging.getLogger(__name__)


class AIScorer:
    """
    L2 AI 打分器
    使用 Qwen Flash 模型进行批量打分
    """
    
    def __init__(self):
        if not config.dashscope_api_key:
            logger.warning("[L2] 未设置 DASHSCOPE_API_KEY, 将使用启发式评分")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=config.dashscope_api_key,
                base_url=config.dashscope_base_url,
            )
    
    def _build_scoring_prompt(self, items: List[ContentItem], content_type: ContentType) -> str:
        """构建批量打分 prompt"""
        
        type_desc = "AI 论文" if content_type == ContentType.PAPER else "AI 新闻"
        
        items_text = ""
        for i, item in enumerate(items, 1):
            abstract = (item.abstract or "无摘要")[:300]
            full_text = (item.full_text or "")
            full_text_snippet = full_text[:1200] if full_text else ""
            items_text += f"""
            [{i}] ID: {item.id}
            标题: {item.title}
            摘要: {abstract}
            全文(如有): {full_text_snippet if full_text_snippet else "无"}
            来源: {item.source_name}
            ---"""
        
        prompt = f"""你是一位拥有全球视野的 AI 科技主编。请以"全球影响力"和"行业变革性"为核心标准，对以下 {len(items)} 条{type_desc}进行评分。

                评分标准 (0-10分):
                - 10分 (Historic): 改变 AI 历史进程的里程碑事件（如 GPT-4 发布、Sora 发布、Transformer 论文）。
                - 9分 (Strategic): 具有全球产业影响力的重大发布、顶级实验室的核心突破、各国国家级 AI 政策。
                - 7-8分 (Impactful): 显著提升现有技术水平的 SOTA 工作、主流科技媒体头条报道、知名独角兽的大额融资或产品发布。
                - 5-6分 (Relevant): 扎实的研究进展、有一定实用价值的开源项目、常规行业资讯。
                - 3-4分 (Niche): 过于细分领域的改进、影响力受限的小型工具、普通的观点文章。
                - 0-2分 (Noise): 纯营销、低质量教程、标题党、重复信息。

                核心准则:
                1. **格局要大**: 优先筛选能影响未来 6-12 个月行业走向的内容。
                2. **去伪存真**: 警惕营销炒作，识别真正的技术干货。
                3. **全球视野**: 关注全球范围内的顶尖动态，不局限于单一地区。

                待评内容:
                {items_text}

                请严格按照以下 JSON 格式返回评分结果（不要添加任何其他文字）:
                [
                {{"id": "内容ID", "score": 分数, "reason": "一两句话的评分理由"}},
                ...
                ]"""
        
        return prompt
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))  # 好吧, 从计网里找到的点子, 指数回退
    def _call_model(self, prompt: str) -> str:
        """调用 Qwen API"""
        if not self.client:
            return "[]"
        
        response = self.client.chat.completions.create(
            model=config.qwen_l2_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    
    def _parse_scores(self, response: str, items: List[ContentItem]) -> Dict[str, dict]:
        """解析 GLM 返回的评分"""
        scores: Dict[str, dict] = {}
        
        # 创建 ID 到 item 的映射
        id_to_item = {item.id: item for item in items}
        
        try:
            # 尝试提取 JSON
            response = response.strip()
            
            # 处理可能的 markdown 代码块
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            data = json.loads(response)
            
            for item in data:
                item_id = item.get("id", "")
                score = item.get("score", 5)
                reason = item.get("reason", "")
                
                # 确保分数在有效范围
                score = max(0, min(10, int(score)))
                scores[item_id] = {"score": score, "reason": reason}
                
        except json.JSONDecodeError as e:
            logger.error(f"[L2] JSON 解析失败: {e}")
            # 使用默认分数
            for item in items:
                scores[item.id] = {"score": 5, "reason": "解析失败，使用默认评分"}
        
        return scores
    
    def _heuristic_score(self, item: ContentItem) -> float:
        """启发式评分 (备用方案, incomplete)"""
        score = 5.0
        
        text = f"{item.title} {item.abstract or ''}".lower()
        
        # 高价值关键词
        high_value = ["sota", "breakthrough", "state-of-the-art", "novel", "first", 
                      "gpt-5", "claude", "gemini", "突破", "创新"]
        for kw in high_value:
            if kw in text:
                score += 1.5
        
        # 大厂关键词
        big_tech = ["openai", "anthropic", "deepmind", "meta ai", "google research"]
        for kw in big_tech:
            if kw in text:
                score += 1.0
        
        # 低价值关键词
        low_value = ["tutorial", "beginner", "introduction", "survey", "review"]
        for kw in low_value:
            if kw in text:
                score -= 1.0
        
        return max(0, min(10, score))

    def _is_vague_reason(self, reason: str) -> bool:
        if not reason:
            return True
        text = reason.strip().lower()
        vague_phrases = [
            "值得关注",
            "引发关注",
            "具有意义",
            "很重要",
            "影响深远",
            "潜力巨大",
            "意义重大",
            "有望改变",
            "interesting",
            "notable",
            "significant",
            "important",
            "impactful",
        ]
        return any(p in text for p in vague_phrases)

    def _is_strong_news(self, item: ContentItem) -> bool:
        if item.l2_score < config.l2_news_min_score:
            return False
        reason = (item.l2_reason or "").strip()
        if len(reason) < config.l2_news_min_reason_len:
            return False
        if self._is_vague_reason(reason):
            return False
        return True

    def _select_papers_by_category(self, papers: List[ContentItem]) -> List[ContentItem]:
        categories = getattr(config, "paper_categories", None) or [
            "General AI",
            "Computer Vision",
            "Robotics",
        ]
        max_per_category = int(getattr(config, "l2_paper_category_max", 18))
        if not categories:
            return papers[: config.l2_papers_limit]

        sorted_candidates = sorted(papers, key=lambda x: x.l2_combined_score, reverse=True)
        buckets = {category: [] for category in categories}
        chosen = []

        for item in sorted_candidates:
            category = item.paper_category or "General AI"
            if category not in buckets:
                category = "General AI"
            if len(buckets[category]) >= max_per_category:
                continue
            buckets[category].append(item)
            chosen.append(item)

        return chosen
    
    def _calculate_combined_score(
        self, 
        item: ContentItem, 
        ai_score: float,
        max_social_score: int = 500
    ) -> float:
        """
        计算综合得分
        公式: AI分数 * 0.6 + 社区热度 * 0.4 + 来源加权
        """
        # 来源加权
        source_bonus = 0.0
        if hasattr(config, "source_weights") and isinstance(config.source_weights, dict):
            for source_key, weight in config.source_weights.items():
                s_name = (item.source_name or "").lower()
                s_url = (item.url or "").lower()
                key = source_key.lower()
                if key in s_name or key in s_url:
                    source_bonus = max(source_bonus, weight)

        # 官方来源偏置（新闻）
        official_bias = 0.0
        if item.content_type == ContentType.NEWS:
            is_official = self._is_official_source(item)
            if is_official:
                official_bias = float(getattr(config, "official_news_bonus", 0.0) or 0.0)
            else:
                official_bias = float(getattr(config, "non_official_news_penalty", 0.0) or 0.0)

        # arXiv 论文：忽略“社区热度/白名单”，只用 ai_score + source_bonus
        # （ingestion 阶段的 item.score 可能是关键词命中数，仅用于 L1，不得进入 L2 综合分）
        if item.content_type == ContentType.PAPER and item.source_type == SourceType.ARXIV:
            return round(float(ai_score) + float(source_bonus), 2)

        # 归一化社区分数到 0-10
        normalized_social = min(10, (item.score / max_social_score) * 10)
        # 白名单加分
        whitelist_bonus = 2.0 if item.is_whitelist else 0.0

        combined = (
            ai_score * 0.6
            + normalized_social * 0.4
            + whitelist_bonus
            + source_bonus
            + official_bias
        )
        return round(combined, 2)

    def _is_official_source(self, item: ContentItem) -> bool:
        if item.is_whitelist:
            return True
        if not item.url:
            return False
        domain = urlparse(item.url).netloc.lower()
        if not domain:
            return False
        for wl_domain in config.whitelist_domains:
            if wl_domain in domain:
                return True
        return False
    
    def score_batch(
        self, 
        items: List[ContentItem],
        content_type: ContentType,
        batch_size: int = 10
    ) -> List[ContentItem]:
        """批量打分"""
        
        if not items:
            return []
        
        all_scored = []
        
        # 分批处理
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            logger.info(f"[L2] 正在打分批次 {i//batch_size + 1}, 共 {len(batch)} 条")
            
            if self.client:
                # 调用 Qwen 打分
                prompt = self._build_scoring_prompt(batch, content_type)
                response = self._call_model(prompt)
                scores = self._parse_scores(response, batch)
            else:
                # 使用启发式打分
                scores = {item.id: {"score": self._heuristic_score(item), "reason": "启发式评分"} for item in batch}
            
            # 计算综合得分
            for item in batch:
                entry = scores.get(item.id, {"score": 5, "reason": ""})
                ai_score = entry.get("score", 5)
                item.l2_score = ai_score
                item.l2_reason = entry.get("reason") or ""
                item.l2_combined_score = self._calculate_combined_score(item, ai_score)
                all_scored.append(item)
        
        return all_scored
    
    def run(
        self,
        papers_l2: List[ContentItem],
        papers_whitelist: List[ContentItem],
        news_l2: List[ContentItem],
        news_whitelist: List[ContentItem]
    ) -> dict:
        """
        运行 L2 打分
        """
        # 对论文打分
        scored_papers = self.score_batch(papers_l2, ContentType.PAPER)
        
        # 对新闻打分
        scored_news = self.score_batch(news_l2, ContentType.NEWS)
        
        # 白名单内容也需要打分（用于排序）
        scored_papers_wl = self.score_batch(papers_whitelist, ContentType.PAPER)
        scored_news_wl = self.score_batch(news_whitelist, ContentType.NEWS)
        
        # 合并并排序
        all_papers = scored_papers + scored_papers_wl
        all_news = scored_news + scored_news_wl

        # 论文分类：仅使用 arXiv 原始分类，非 arXiv 来源归入 General AI
        for item in all_papers:
            if not item.paper_category:
                item.paper_category = "General AI"
        
        all_papers.sort(key=lambda x: x.l2_combined_score, reverse=True)
        all_news.sort(key=lambda x: x.l2_combined_score, reverse=True)

        # 新闻质量门槛：剔除理由过弱/评分过低的条目
        strong_news = [n for n in all_news if self._is_strong_news(n)]
        if strong_news:
            all_news = strong_news

        # 选取 Top N（论文按分类配额）
        top_papers = self._select_papers_by_category(all_papers)
        top_news = all_news[:config.l2_news_limit]
        
        logger.info(
            f"[L2] 论文: {len(all_papers)} -> Top {len(top_papers)}, "
            f"新闻: {len(all_news)} -> Top {len(top_news)}"
        )
        
        return {
            "papers_l3": top_papers,
            "news_l3": top_news,
            # 提供给主流程做“L2 后语义去重 -> 再取 Top”
            "news_l3_all": all_news,
        }
