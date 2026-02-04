"""
AI Tides Data Models - 数据模型定义
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ContentType(str, Enum):
    """内容类型"""
    PAPER = "paper"
    NEWS = "news"


class SourceType(str, Enum):
    """来源类型"""
    HUGGINGFACE = "huggingface"
    ARXIV = "arxiv"
    HACKERNEWS = "hackernews"
    RSS = "rss"
    REDDIT = "reddit"
    GITHUB = "github"


class ContentItem(BaseModel):
    """统一的内容项模型"""
    id: str
    title: str
    title_zh: Optional[str] = None  # 新闻可用的中文标题
    url: str
    content_type: ContentType
    source_type: SourceType
    source_name: str
    
    # 摘要和内容
    abstract: Optional[str] = None
    full_text: Optional[str] = None  # 新闻全文/正文（抓取或来自源）
    image_url: Optional[str] = None
    
    # 元数据
    authors: List[str] = Field(default_factory=list)
    published_at: Optional[datetime] = None
    
    # 社区指标
    score: int = 0              # HN分数 / HF upvotes
    comments_count: int = 0
    
    # Pipeline 处理状态
    is_whitelist: bool = False  # 是否白名单直通
    l1_passed: bool = False     # L1 通过
    l2_score: float = 0.0       # L2 GLM 打分
    l2_reason: Optional[str] = None  # L2 评分理由
    l2_combined_score: float = 0.0  # L2 综合得分
    l3_selected: bool = False   # L3 最终入选
    
    # L3 AI 生成内容
    summary_zh: Optional[str] = None  # 中文摘要
    tags: List[str] = Field(default_factory=list)
    paper_category: Optional[str] = None  # 论文分类（用于前端分区）


class DailyReport(BaseModel):
    """每日报告模型"""
    date: str
    generated_at: datetime
    introduction: str  # 每日综述
    longform_script: Optional[str] = None  # 长文稿（用于播客）
    audio_url: Optional[str] = None  # 播客音频 URL
    
    # 入选内容
    papers: List[ContentItem] = Field(default_factory=list)
    news: List[ContentItem] = Field(default_factory=list)
    
    # Pipeline 统计
    stats: dict = Field(default_factory=dict)


class GLMScoreResponse(BaseModel):
    """GLM 打分响应"""
    id: str
    score: int
    reason: str


class GLMSummaryResponse(BaseModel):
    """GLM 摘要响应"""
    id: str
    summary: str
    tags: List[str]
    selected: bool
