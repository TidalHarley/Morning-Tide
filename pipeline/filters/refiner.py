"""
AI Tides - L3 深度精炼器
使用 Qwen3 Max 进行最终筛选和内容生成
"""
import logging
import json
from typing import List, Optional, Tuple
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
from threading import BoundedSemaphore
import hashlib

from openai import OpenAI

from ..models import ContentItem, ContentType, DailyReport
from ..config import config

logger = logging.getLogger(__name__)


class Refiner:
    """
    L3 深度精炼器
    - 最终筛选 Top 10
    - 生成中文摘要
    - 撰写每日综述
    - 自动打标签
    """
    
    # 预定义标签库
    TAG_LIBRARY = {
        # 技术领域
        "LLM": ["llm", "language model", "gpt", "claude", "gemini", "llama", "大语言模型"],
        "Vision": ["vision", "image", "视觉", "图像", "cv", "computer vision"],
        "Multimodal": ["multimodal", "多模态", "vlm", "vision-language"],
        "Agent": ["agent", "智能体", "agentic", "tool use", "function calling"],
        "Robotics": ["robot", "机器人", "embodied", "manipulation", "具身"],
        "Diffusion": ["diffusion", "stable diffusion", "扩散", "生成"],
        "Audio": ["audio", "speech", "音频", "语音", "tts", "asr"],
        "3D": ["3d", "nerf", "gaussian", "三维"],
        
        # 技术方法
        "Training": ["training", "fine-tuning", "rlhf", "dpo", "sft", "训练"],
        "Inference": ["inference", "推理加速", "quantization", "量化"],
        "RAG": ["rag", "retrieval", "检索增强"],
        "Reasoning": ["reasoning", "chain-of-thought", "推理", "cot"],
        
        # 来源分类
        "Industry": ["openai", "anthropic", "google", "meta", "microsoft", "发布"],
        "Research": ["research", "paper", "arxiv", "论文", "研究"],
        "Open Source": ["open source", "开源", "github", "huggingface"],
        "Benchmark": ["benchmark", "evaluation", "评测", "leaderboard"],
    }

    
    def __init__(self):
        if not config.dashscope_api_key:
            logger.warning("[L3] 未设置 DASHSCOPE_API_KEY, 将使用简化输出")
            self.client = None
            self._semaphore = None
        else:
            self.client = OpenAI(
                api_key=config.dashscope_api_key,
                base_url=config.dashscope_base_url,
                timeout=config.qwen_timeout_seconds,
            )
            self._semaphore = BoundedSemaphore(max(1, config.l3_max_concurrency))
    
    def _auto_tag(self, item: ContentItem) -> List[str]:
        """基于启发式规则自动打标签"""
        tags = []
        text = f"{item.title} {item.abstract or ''}".lower()
        
        for tag, keywords in self.TAG_LIBRARY.items():
            for kw in keywords:
                if kw.lower() in text:
                    if tag not in tags:
                        tags.append(tag)
                    break
        
        # 限制标签数量
        return tags[:4]

    def _paper_category(self, item: ContentItem) -> str:
        """仅使用 arXiv 原始分类，不做任何额外分类"""
        return item.paper_category or "General AI"

    def _select_papers_by_category(
        self,
        papers_candidates: List[ContentItem],
        selected_ids: set,
    ) -> List[ContentItem]:
        categories = getattr(config, "paper_categories", None) or [
            "General AI",
            "Computer Vision",
            "Robotics",
        ]
        per_category = int(getattr(config, "l3_paper_category_target", 6))
        if not categories:
            return self._select_papers_with_targets(papers_candidates, selected_ids)

        sorted_candidates = sorted(
            papers_candidates, key=lambda x: x.l2_combined_score, reverse=True
        )

        buckets = {category: [] for category in categories}
        chosen = []

        for item in sorted_candidates:
            category = self._paper_category(item)
            if category not in buckets:
                category = "General AI"
            if len(buckets[category]) >= per_category:
                continue
            buckets[category].append(item)
            chosen.append(item)

        total_target = per_category * len(categories)
        return chosen[:total_target]
    
    def _build_selection_prompt(
        self, 
        papers: List[ContentItem], 
        news: List[ContentItem]
    ) -> str:
        """构建最终筛选 prompt"""
        
        def format_items(items: List[ContentItem], label: str) -> str:
            text = f"\n### {label}\n"
            for i, item in enumerate(items, 1):
                abstract = (item.abstract or "无摘要")[:200]
                full_text = (item.full_text or "")[:800]
                text += f"""
[{i}] ID: {item.id}
标题: {item.title}
摘要: {abstract}
正文(节选): {full_text if full_text else "无"}
来源: {item.source_name} | L2得分: {item.l2_combined_score}
---"""
            return text
        
        papers_text = format_items(papers, "论文候选")
        news_text = format_items(news, "新闻候选")
        
        prompt = f"""你是 AI 全球日报的首席主编, 负责每日 AI 情报的最终筛选。你的筛选情况将决定整个日报的存亡

## 任务
从以下候选内容中，为读者精选出最值得关注的内容：
- 从论文中选出最多 {config.l3_papers_target} 篇
- 从新闻中选出最多 {config.l3_news_target} 条

## 选择标准
1. **影响力**: 对 AI 行业有重大影响, 能够代表今天AI领域最核心的进展. 影响力是第一要务, 其他标准都是次要的.
2. **创新性**: 代表技术突破或新方向
3. **时效性**: 今日最值得关注的动态
4. **多样性**: 尽量覆盖不同领域，但是影响力和权威性仍然是第一要务
5. **新闻筛选硬性条件**: 只有当你能基于标题/摘要清晰回答"新闻关于什么、重要性在哪里、对AI领域的意义、对普通人意味着什么"时，才允许入选新闻列表，否则不要选。
6. **反空泛要求**: 如果只能给出空泛理由（如“值得关注/意义重大/影响深远”），不要选入新闻列表。

## 候选内容
{papers_text}
{news_text}

## 输出要求
请返回严格的 JSON 格式（不要有其他文字）：
{{
  "selected_paper_ids": ["id1", "id2", ...],
  "selected_news_ids": ["id1", "id2", ...],
  "daily_introduction_zh": "中文综述，180~260字，新闻记者语气，不空泛",
  "daily_introduction_en": "English introduction, 120-180 words, concise and natural"
}}"""
        
        return prompt

    def _select_news_with_target(
        self, news_candidates: List[ContentItem], selected_ids: set
    ) -> List[ContentItem]:
        selected = [item for item in news_candidates if item.id in selected_ids]
        selected_ids_set = {item.id for item in selected}
        for item in news_candidates:
            if len(selected) >= config.l3_news_target:
                break
            if item.id not in selected_ids_set:
                selected.append(item)
                selected_ids_set.add(item.id)
        return selected[: config.l3_news_target]

    def _select_papers_with_targets(
        self, papers_candidates: List[ContentItem], selected_ids: set
    ) -> List[ContentItem]:
        hf = [p for p in papers_candidates if p.source_type.value == "huggingface"]
        arxiv = [p for p in papers_candidates if p.source_type.value == "arxiv"]

        def pick(pool: List[ContentItem], limit: int) -> List[ContentItem]:
            chosen = [p for p in pool if p.id in selected_ids]
            chosen_ids = {p.id for p in chosen}
            for item in pool:
                if len(chosen) >= limit:
                    break
                if item.id not in chosen_ids:
                    chosen.append(item)
                    chosen_ids.add(item.id)
            return chosen[:limit]

        selected_hf = pick(hf, config.l3_hf_papers_target)
        selected_arxiv = pick(arxiv, config.l3_arxiv_papers_target)
        selected = selected_hf + selected_arxiv

        if len(selected) < config.l3_papers_target:
            selected_ids_set = {item.id for item in selected}
            for item in papers_candidates:
                if len(selected) >= config.l3_papers_target:
                    break
                if item.id not in selected_ids_set:
                    selected.append(item)
                    selected_ids_set.add(item.id)
        return selected[: config.l3_papers_target]
    

    def _build_summary_prompt(self, items: List[ContentItem]) -> str:
        """构建摘要生成 prompt"""
        
        items_text = ""
        for item in items:
            abstract = item.abstract or "无摘要"
            full_text = item.full_text or ""
            items_text += f"""
[ID: {item.id}]
类型: {"新闻" if item.content_type == ContentType.NEWS else "论文"}
标题: {item.title}
摘要: {abstract}
正文(节选): {full_text if full_text else "无"}
---"""
        
        prompt = f"""你是一位顶级 AI 科技编辑，请为以下 {len(items)} 条内容生成高质量中英双语摘要与新闻标题。

{items_text}

## 质量要求
1. **准确**：不添加原文没有的信息，不夸大、不虚构。
2. **完整叙述**：输出是一段连贯的完整中文句子，不要碎片化罗列。
3. **可读性**：专业、简洁、可读性强，避免模板化套话。
4. **克制长度**：在保证信息完整的前提下尽量简短，避免冗余。

### 新闻摘要额外要求（只对类型=新闻生效）
- 产出**一段完整中文句子**，不分点、不换行，语气像专业科技编辑。
- 必须覆盖四个维度：**主要内容**、**重要性**、**对 AI 领域的意义**、**对普通人的影响/可采取的行动**。
- 要具体、信息密度高，避免空泛词（如“引发关注”“意义重大”），要写出**事件主体、动作、结果/影响**。
- 字数建议 200~300 字；若信息不足，可用更少字但仍需覆盖四个维度。
- 可以对关键信息加粗，但不要模板化标注“关于/重要性”等固定词。

### 新闻标题要求
- 仅对新闻生成 `title_zh`，要求像新闻标题：简洁、有动词、12~24 字。有一些中文不好翻译的词使用英文即可，比如说ai领域的一些公司和专有名词
- 论文 `title_zh` 置空字符串。

### 论文摘要要求
- 必须包含**主要内容**、**关键点**、**为什么重要**三部分，但写成一段通顺话，不要分点。
- 信息密度要高，尽量包含方法/实验/指标/结论/应用中的可用细节。

## 输出格式
- 返回严格的 JSON 格式：
[
  {{
    "id": "内容ID",
    "summary_zh": "中文摘要",
    "summary_en": "English summary",
    "title_zh": "新闻标题(仅新闻)",
    "title_en": "English headline (news only)"
  }},
  ...
]"""
        
        return prompt

    def _build_longform_prompt(
        self, news_items: List[ContentItem], introduction: str, language: str = "zh"
    ) -> str:
        """构建播客长文稿 prompt（基于当日全部新闻）"""
        items_text = ""
        for i, item in enumerate(news_items, 1):
            if language == "en":
                summary = item.summary_en or item.abstract or item.title
                title = item.title_en or item.title
                items_text += f"""
[{i}] Title: {title}
Source: {item.source_name}
Summary: {summary}
URL: {item.url}
---"""
            else:
                summary = item.summary_zh or item.abstract or item.title
                title = item.title_zh or item.title
                items_text += f"""
[{i}] 标题: {title}
来源: {item.source_name}
摘要: {summary}
链接: {item.url}
---"""

        if language == "en":
            return f"""You are the editor-in-chief of an AI tech podcast. Based on the news below, write an English long-form script that can be directly read as an audio briefing.

## Goals
1. Help listeners understand today's key AI developments in 5-8 minutes.
2. Keep a natural editorial tone, concise and professional.
3. Organize ideas into coherent paragraphs, not bullet dumps.

## Structure
1) Opening (1 paragraph): today's macro trend.
2) Main body (3-5 paragraphs): each paragraph covers a major theme with representative examples.
3) Insights & advice (1 paragraph): what to watch next, risks, opportunities.
4) Closing (1 paragraph): brief wrap-up.

## Existing introduction (reference only)
{introduction or "(none)"}

## News material
{items_text}

## Constraints
- 900-1300 words in English.
- Avoid generic filler and repetitive AI phrases.
- Output only the final script body, no extra notes."""

        return f"""你是一位资深 AI 科技播客的主编，请基于以下新闻素材生成一篇“可直接用于音频播客”的中文长文稿。

## 写作目标
1. 让听众在 5~8 分钟内清楚理解今天 AI 领域发生了什么。
2. 语气自然、克制、有编辑感，避免 AI 腔和模板话术。
3. 结构清晰、自然分段，避免列表化堆砌。

## 写作结构（必须遵守）
1) 开场（1段）：用几句简短的话概括今日整体趋势。
2) 主体（3~5段）：每段聚焦一个主题或事件群，不要逐条复述；用“归纳+代表案例”的方式写。
3) 观察与建议（1段）：告诉听众如何理解今天的变化/风险/机会。
4) 收尾（1段）:简短收束，不要口号式。

## 已有综述（供参考，不要照抄）
{introduction or "（无）"}

## 新闻素材（当天全部新闻）
{items_text}

## 文字约束
- 全文 1600~2000 字（中文字数）。
- 不要出现“本文/本文将/综上/总之”等模板话。
- 不要像新闻通稿，语气要像播客主持人的口播稿。
- 适当加入过渡句，让段落衔接自然。

请直接输出文稿正文，不要加标题或额外说明。"""

    def _is_valid_news_summary(self, summary: str) -> bool:
        if not summary:
            return False
        return len(summary.strip()) >= 60

    def _chunk_items(self, items: List[ContentItem], size: int) -> List[List[ContentItem]]:
        if size <= 0:
            return [items]
        return [items[i:i + size] for i in range(0, len(items), size)]
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_model(self, prompt: str, *, tag: str) -> str:
        """调用 Qwen Max API"""
        if not self.client:
            return "{}"

        prompt_preview = prompt.replace("\n", " ")[:500]
        prompt_hash = hashlib.md5(prompt.encode("utf-8")).hexdigest()[:10]

        try:
            with self._semaphore:
                response = self.client.chat.completions.create(
                    model=config.qwen_l3_model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=4000
                )
            return response.choices[0].message.content
        except Exception as exc:
            logger.error(
                "[L3] 请求失败 | tag=%s | model=%s | prompt_chars=%s | prompt_hash=%s | preview=%s | err=%s",
                tag,
                config.qwen_l3_model,
                len(prompt),
                prompt_hash,
                prompt_preview,
                exc,
            )
            raise
    
    def _parse_json(self, response: str) -> dict:
        """解析 JSON 响应"""
        try:
            response = response.strip()
            
            # 处理 markdown 代码块
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"[L3] JSON 解析失败: {e}")
            return {}
    
    def _fallback_selection(
        self,
        papers: List[ContentItem],
        news: List[ContentItem]
    ) -> Tuple[List[ContentItem], List[ContentItem], str, str]:
        """备用选择方案（无 API 时使用）"""
        
        # 直接按 L2 分数取 Top N（满足前端展示需求）
        # 论文：按类别优中选优（每类 6 篇）
        selected_papers = self._select_papers_by_category(papers, set())
        selected_news = self._select_news_with_target(news, set())
        
        # 生成简单的综述
        paper_titles = [p.title[:30] for p in selected_papers[:3]]
        news_titles = [n.title[:30] for n in selected_news[:3]]
        
        introduction_zh = (
            f"今日 AI 动态：论文方面关注 {', '.join(paper_titles)} 等研究；"
            f"行业新闻涵盖 {', '.join(news_titles)} 等内容。"
        )
        introduction_en = (
            f"Today's AI highlights: key papers include {', '.join(paper_titles)}; "
            f"industry news covers {', '.join(news_titles)}."
        )

        return selected_papers, selected_news, introduction_zh, introduction_en
    
    def _fallback_summary(self, item: ContentItem) -> str:
        """备用摘要生成"""
        if item.content_type == ContentType.NEWS:
            about = (item.abstract or item.title or "")[:80]
            importance = "该事件带来新的技术/监管/产品变化"
            ai_impact = "将影响AI模型能力、成本或应用边界"
            public_impact = "普通人可能在工具可用性、价格或隐私体验上感知变化"
            return (
                f"{about}，{importance}，并将改变AI领域的{ai_impact}，"
                f"同时意味着{public_impact}。"
            )
        summary = item.abstract[:120] + "..." if item.abstract else item.title
        return (
            f"主要内容：{summary}；"
            f"关键点：{item.title[:60]}；"
            f"为什么重要：这是近期 AI 领域值得关注的进展。"
        )

    def _fallback_summary_en(self, item: ContentItem) -> str:
        if item.content_type == ContentType.NEWS:
            about = (item.abstract or item.title or "")[:120]
            return (
                f"{about}. This matters because it may reshape AI capability, cost, "
                "or deployment choices, and can affect how end users use AI tools."
            )
        summary = (item.abstract[:150] + "...") if item.abstract else item.title
        return (
            f"Main point: {summary}. Key takeaway: {item.title[:80]}. "
            "Why it matters: this is a notable AI development to track."
        )
    
    def run(
        self,
        papers_l3: List[ContentItem],
        news_l3: List[ContentItem]
    ) -> DailyReport:
        """
        运行 L3 精炼
        返回最终的每日报告
        """
        logger.info(f"[L3] 开始精炼 - 论文: {len(papers_l3)}, 新闻: {len(news_l3)}")
        
        # 先为候选论文打标签（用于展示与辅助）
        for item in papers_l3:
            if not item.tags:
                item.tags = self._auto_tag(item)

        selected_papers = []
        selected_news = []
        introduction_zh = ""
        introduction_en = ""
        longform_script_zh = ""
        longform_script_en = ""
        
        if self.client:
            # Step 0: 论文分类已在 L2 完成（按 arXiv 类别），此处仅兜底
            for item in papers_l3:
                if not item.paper_category:
                    item.paper_category = "General AI"
            # Step 1: 最终筛选
            try:
                selection_prompt = self._build_selection_prompt(papers_l3, news_l3)
                selection_response = self._call_model(selection_prompt, tag="selection")
                selection_data = self._parse_json(selection_response)
            except Exception:
                logger.error("[L3] 选择阶段失败，使用备用选择")
                selected_papers, selected_news, introduction_zh, introduction_en = self._fallback_selection(
                    papers_l3, news_l3
                )
            else:
                selected_news_ids = set(selection_data.get("selected_news_ids", []))
                introduction_zh = (
                    selection_data.get("daily_introduction_zh")
                    or selection_data.get("daily_introduction")
                    or ""
                )
                introduction_en = (
                    selection_data.get("daily_introduction_en")
                    or ""
                )
                
                # 论文：L3 按类别优中选优（每类 6 篇）
                selected_papers = self._select_papers_by_category(papers_l3, set())
                selected_news = self._select_news_with_target(news_l3, selected_news_ids)
                
                for paper in selected_papers:
                    paper.l3_selected = True
                for news_item in selected_news:
                    news_item.l3_selected = True
            
            # Step 2: 生成中文摘要（分批）
            all_selected = selected_papers + selected_news
            if all_selected:
                summary_map_zh = {}
                summary_map_en = {}
                title_map_zh = {}
                title_map_en = {}
                batches = self._chunk_items(all_selected, config.l3_summary_batch_size)
                for batch in batches:
                    try:
                        summary_prompt = self._build_summary_prompt(batch)
                        summary_response = self._call_model(
                            summary_prompt,
                            tag=f"summary items={len(batch)}",
                        )
                        summaries_data = self._parse_json(summary_response)
                        if isinstance(summaries_data, list):
                            summary_map_zh.update(
                                {
                                    s.get("id"): s.get("summary_zh") or s.get("summary")
                                    for s in summaries_data
                                    if isinstance(s, dict)
                                }
                            )
                            summary_map_en.update(
                                {
                                    s.get("id"): s.get("summary_en")
                                    for s in summaries_data
                                    if isinstance(s, dict)
                                }
                            )
                            title_map_zh.update(
                                {
                                    s.get("id"): s.get("title_zh")
                                    for s in summaries_data
                                    if isinstance(s, dict)
                                }
                            )
                            title_map_en.update(
                                {
                                    s.get("id"): s.get("title_en")
                                    for s in summaries_data
                                    if isinstance(s, dict)
                                }
                            )
                    except Exception:
                        logger.error("[L3] 摘要批次失败，已回退该批次")
                        for item in batch:
                            summary_map_zh.setdefault(item.id, self._fallback_summary(item))
                            summary_map_en.setdefault(item.id, self._fallback_summary_en(item))
                
                for item in all_selected:
                    summary_zh = summary_map_zh.get(item.id) or self._fallback_summary(item)
                    summary_en = summary_map_en.get(item.id) or self._fallback_summary_en(item)
                    item.summary_zh = summary_zh
                    item.summary_en = summary_en
                    title_zh = title_map_zh.get(item.id)
                    title_en = title_map_en.get(item.id)
                    if (
                        item.content_type == ContentType.NEWS
                        and isinstance(title_zh, str)
                        and title_zh.strip()
                    ):
                        item.title_zh = title_zh.strip()
                    if (
                        item.content_type == ContentType.NEWS
                        and isinstance(title_en, str)
                        and title_en.strip()
                    ):
                        item.title_en = title_en.strip()
            
            if selected_news:
                for news_item in selected_news:
                    if not self._is_valid_news_summary(news_item.summary_zh or ""):
                        news_item.summary_zh = self._fallback_summary(news_item)
                    if not self._is_valid_news_summary(news_item.summary_en or ""):
                        news_item.summary_en = self._fallback_summary_en(news_item)
                    if not (news_item.title_zh or "").strip():
                        news_item.title_zh = news_item.title
                    if not (news_item.title_en or "").strip():
                        news_item.title_en = news_item.title

            # Step 2.5: 生成播客长文稿（基于当日新闻）
            if selected_news:
                try:
                    longform_prompt_zh = self._build_longform_prompt(
                        selected_news, introduction_zh, language="zh"
                    )
                    longform_script_zh = (
                        self._call_model(longform_prompt_zh, tag="longform_zh") or ""
                    ).strip()

                    longform_prompt_en = self._build_longform_prompt(
                        selected_news, introduction_en or introduction_zh, language="en"
                    )
                    longform_script_en = (
                        self._call_model(longform_prompt_en, tag="longform_en") or ""
                    ).strip()
                except Exception:
                    logger.error("[L3] 长文稿生成失败，使用简化文稿")
                    longform_script_zh = introduction_zh or "今日 AI 领域有多条重要进展，建议关注核心发布与趋势变化。"
                    longform_script_en = introduction_en or "Today's AI landscape includes several important developments worth tracking."
        else:
            # 无 API 时使用备用方案
            selected_papers, selected_news, introduction_zh, introduction_en = self._fallback_selection(
                papers_l3, news_l3
            )
            for paper in selected_papers:
                paper.l3_selected = True
                paper.summary_zh = self._fallback_summary(paper)
                paper.summary_en = self._fallback_summary_en(paper)
            
            for news_item in selected_news:
                news_item.l3_selected = True
                news_item.summary_zh = self._fallback_summary(news_item)
                news_item.summary_en = self._fallback_summary_en(news_item)
                news_item.title_zh = news_item.title_zh or news_item.title
                news_item.title_en = news_item.title_en or news_item.title
            longform_script_zh = introduction_zh
            longform_script_en = introduction_en
        
        # Step 3: 自动打标签
        for item in selected_papers + selected_news:
            item.tags = self._auto_tag(item)
        
        # 构建报告
        today = datetime.now()
        report = DailyReport(
            date=today.strftime("%Y-%m-%d"),
            generated_at=today,
            introduction=introduction_zh or "今日 AI 领域动态汇总。",
            introduction_zh=introduction_zh or "今日 AI 领域动态汇总。",
            introduction_en=introduction_en or "Today's AI developments at a glance.",
            longform_script=longform_script_zh or "",
            longform_script_zh=longform_script_zh or "",
            longform_script_en=longform_script_en or "",
            papers=selected_papers,
            news=selected_news,
            stats={
                "total_papers_ingested": 0,  # 稍后填充
                "total_news_ingested": 0,
                "l1_papers_passed": 0,
                "l1_news_passed": 0,
                "l2_papers_scored": len(papers_l3),
                "l2_news_scored": len(news_l3),
                "l3_papers_selected": len(selected_papers),
                "l3_news_selected": len(selected_news)
            }
        )
        
        logger.info(
            f"[L3] 精炼完成 - 最终选出 {len(selected_papers)} 篇论文, "
            f"{len(selected_news)} 条新闻"
        )
        
        return report
