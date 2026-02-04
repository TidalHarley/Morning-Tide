"""
AI Tides Configuration - 配置文件
"""
import os
from datetime import datetime, timedelta
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class Config(BaseModel):
    """Pipeline 配置"""
    
    # API Keys
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # 网络请求配置
    # SSL 校验默认关闭（避免本地代理拦截 TLS 导致 SSLEOFError）
    # 代理默认开启（中国大陆访问国外网站通常需要代理）
    requests_verify_ssl: bool = _get_bool_env("AI_TIDES_VERIFY_SSL", False)
    requests_use_proxy: bool = _get_bool_env("AI_TIDES_USE_PROXY", True)
    suppress_insecure_warnings: bool = _get_bool_env("AI_TIDES_SUPPRESS_INSECURE_WARNINGS", True)

    # 图片占位图（当抓取失败时使用）
    image_placeholder_url: str = "/placeholder.svg"
    # 图片最小大小（字节），过小图片通常模糊或为图标
    image_min_bytes: int = int(os.getenv("AI_TIDES_IMAGE_MIN_BYTES", "5000"))
    # 图片最小分辨率（像素），过小图片通常会显得模糊
    image_min_width: int = int(os.getenv("AI_TIDES_IMAGE_MIN_WIDTH", "420"))
    image_min_height: int = int(os.getenv("AI_TIDES_IMAGE_MIN_HEIGHT", "240"))

    # 音频生成配置（播客）
    audio_enabled: bool = _get_bool_env("AI_TIDES_AUDIO_ENABLED", False)
    audio_provider: str = os.getenv("AI_TIDES_AUDIO_PROVIDER", "openai")
    audio_model: str = os.getenv("AI_TIDES_AUDIO_MODEL", "tts-1")
    audio_voice: str = os.getenv("AI_TIDES_AUDIO_VOICE", "alloy")
    audio_format: str = os.getenv("AI_TIDES_AUDIO_FORMAT", "mp3")
    audio_output_dir: str = os.getenv("AI_TIDES_AUDIO_OUTPUT_DIR", "public/audio")
    audio_public_url_prefix: str = os.getenv("AI_TIDES_AUDIO_URL_PREFIX", "/audio")
    audio_max_chars: int = int(os.getenv("AI_TIDES_AUDIO_MAX_CHARS", "4000"))
    audio_rewrite_enabled: bool = _get_bool_env("AI_TIDES_AUDIO_REWRITE_ENABLED", False)
    audio_rewrite_model: str = os.getenv("AI_TIDES_AUDIO_REWRITE_MODEL", "")
    audio_rewrite_max_chars: int = int(os.getenv("AI_TIDES_AUDIO_REWRITE_MAX_CHARS", "5000"))
    audio_tts_base_url: str = os.getenv("AI_TIDES_TTS_BASE_URL", "")
    audio_tts_token: str = os.getenv("AI_TIDES_TTS_TOKEN", "")
    audio_tts_ra_format: str = os.getenv(
        "AI_TIDES_TTS_RA_FORMAT", "audio-16khz-128kbitrate-mono-mp3"
    )
    
    # 数据源配置
    # arXiv 类别（只关注核心 AI 三类）
    arxiv_categories: List[str] = ["cs.AI", "cs.CV", "cs.RO"]
    hours_lookback: int = 24  # 回溯时间（小时），考虑时区差异用24小时
    # 论文抓取时效控制（固定：滚动24小时 + 周末跳过）
    papers_freshness_days: int = 1
    papers_window_mode: str = "rolling"
    papers_timezone: str = "Asia/Shanghai"
    papers_skip_weekends: bool = True
    # 当 48 小时内论文为空时，自动放宽到更长窗口
    hf_relax_hours_when_empty: int = 168   
    arxiv_relax_hours_when_empty: int = 168
    # 放宽窗口时最多保留的论文数量（避免数据爆炸）
    relax_max_papers: int = 30
    
    # L1 启发式过滤配置
    ai_keywords: List[str] = [
    # ===== General / Foundation =====
    "AI", "Artificial Intelligence", "人工智能",
    "AGI", "ASI",
    "Foundation Model", "Base Model", "Frontier Model",
    "Large Language Model", "LLM", "Language Model",
    "Multimodal", "Multimodal Model", "VLM", "Vision-Language Model",
    "Generative AI", "GenAI", "生成式AI",
    "Reasoning Model", "推理模型", "Deep Reasoning",
    "Scaling Law", "scaling laws", "compute-optimal",
    "Emergent Abilities", "emergence",
    "SOTA", "State of the Art", "Benchmark", "Leaderboard",
    "Pretraining", "Pre-trained", "预训练",
    "Fine-tuning", "Finetuning", "微调",
    "Instruction Tuning", "指令微调",
    "In-Context Learning", "ICL", "Few-shot", "Zero-shot",
    "Prompting", "Prompt Engineering", "提示工程",

    # ===== Architectures / Model families =====
    "Transformer", "Decoder-only", "Encoder-Decoder", "Encoder-only",
    "Attention", "Self-Attention", "Cross-Attention",
    "Multi-Head Attention", "MHA",
    "Positional Encoding", "RoPE", "ALiBi",
    "MoE", "Mixture of Experts", "Sparse MoE", "Dense Model",
    "Router", "Expert Parallel", "Gating",
    "RNN", "LSTM", "GRU",
    "CNN", "ConvNet",
    "ViT", "Vision Transformer",
    "CLIP", "SigLIP", "DINO", "DINOv2",
    "Q-Former", "Perceiver", "Perceiver IO",
    "State Space Model", "SSM", "Mamba",
    "RWKV",
    "Diffusion Model", "Diffusion", "扩散模型",
    "DiT", "Diffusion Transformer",
    "Flow Matching", "Rectified Flow", "Consistency Model",
    "Autoregressive", "AR", "Non-autoregressive", "NAR",
    "MaskGIT", "VQ-VAE", "VAE",
    "GAN",
    "NeRF", "3D Gaussian Splatting", "3DGS",
    "World Model", "Latent World Model",

    # ===== Training objectives / losses =====
    "Cross Entropy", "Negative Log-Likelihood", "NLL",
    "Next Token Prediction", "Causal LM",
    "Masked LM", "MLM",
    "Contrastive Learning", "InfoNCE",
    "Denoising", "Score Matching",
    "KL Divergence", "KLD",
    "Triplet Loss",
    "Distillation", "Knowledge Distillation",
    "Self-Distillation",
    "Curriculum Learning",

    # ===== Alignment / Preference learning =====
    "Alignment", "AI Alignment", "对齐",
    "RLHF", "Reinforcement Learning from Human Feedback",
    "RLAIF", "Reinforcement Learning from AI Feedback",
    "Preference Learning", "Preference Dataset",
    "Reward Model", "RM",
    "DPO", "Direct Preference Optimization",
    "IPO", "Implicit Preference Optimization",
    "KTO", "Kahneman-Tversky Optimization",
    "ORPO",
    "PPO", "Proximal Policy Optimization",
    "GRPO",
    "SFT", "Supervised Fine-Tuning",
    "Constitutional AI", "Safety Tuning",
    "Red Teaming", "红队",
    "Guardrail", "Safety Filter", "Content Policy",
    "Toxicity", "Bias", "Fairness", "Harmlessness",
    "Interpretability", "Mechanistic Interpretability", "可解释性",
    "Model Editing", "RAG-as-guard", "Refusal", "Jailbreak",

    # ===== Inference / decoding / long context =====
    "Inference", "Decoding",
    "Greedy Decoding", "Beam Search",
    "Top-k", "Top-p", "Nucleus Sampling", "Temperature",
    "Speculative Decoding", "Draft Model",
    "KV Cache", "PagedAttention",
    "FlashAttention", "FlashAttention-2", "FlashAttention-3",
    "Long Context", "Context Window",
    "RoPE Scaling", "NTK scaling",
    "Sliding Window Attention",
    "Retrieval-Augmented Generation", "RAG",
    "Tool Use", "Function Calling", "Structured Output", "JSON mode",

    # ===== Data / Tokenization =====
    "Tokenizer", "BPE", "SentencePiece", "Unigram LM",
    "Vocabulary", "Token", "Subword",
    "Data Curation", "Data Filtering", "Deduplication",
    "Data Contamination", "Leakage",
    "Synthetic Data", "Self-Instruct",
    "Mixture of Data", "Data Mixture",
    "WebDataset", "Parquet",
    "Instruction Data", "Chat Data",
    "Preference Data",

    # ===== Efficient training / PEFT / quantization =====
    "PEFT", "Parameter-Efficient Fine-Tuning",
    "LoRA", "QLoRA", "DoRA",
    "Adapters", "Adapter Tuning",
    "Prefix Tuning", "Prompt Tuning", "P-Tuning", "P-Tuning v2",
    "BitFit",
    "Gradient Checkpointing",
    "Mixed Precision", "FP16", "BF16", "TF32",
    "Quantization", "INT8", "INT4", "NF4",
    "GPTQ", "AWQ", "SmoothQuant",
    "Pruning", "Sparsity",
    "FSDP", "Fully Sharded Data Parallel",
    "DeepSpeed", "ZeRO", "ZeRO-2", "ZeRO-3",
    "DDP", "Data Parallel",
    "Tensor Parallel", "Pipeline Parallel",
    "Megatron-LM",

    # ===== Agents / planning / tool-augmented =====
    "Agent", "AI Agent", "智能体",
    "Toolformer", "ReAct", "Plan-and-Execute",
    "Chain-of-Thought", "CoT",
    "Self-Consistency",
    "Reflection", "Verifier", "Critic", "Reranking",
    "Multi-Agent", "Swarm",
    "Memory", "Episodic Memory",
    "Autonomous Agent",
    "Browser Agent", "Code Agent",
    "Workflow", "Orchestration",

    # ===== Multimodal (vision/audio/video) =====
    "Multimodal LLM", "MLLM",
    "Image Captioning", "VQA", "Visual Reasoning",
    "OCR", "Document AI",
    "Grounding", "Referring Expression",
    "Segmentation", "Detection",
    "Video Understanding", "Video-Language Model",
    "Text-to-Image", "Text-to-Video", "Image-to-Video",
    "Text-to-Speech", "TTS",
    "Speech-to-Text", "ASR",
    "Audio-Language Model",
    "Diffusion Policy",

    # ===== Robotics / Embodied AI =====
    "Robot", "Robotics", "机器人",
    "Embodied AI", "具身智能",
    "Navigation", "VLN", "Vision-Language Navigation",
    "VLN-CE", "Sim2Sim", "Sim2Real", "Domain Adaptation",
    "Imitation Learning", "IL", "Behavior Cloning", "BC",
    "Reinforcement Learning", "RL",
    "Offline RL", "Online RL",
    "Reward Shaping",
    "SLAM", "NeRF-SLAM",
    "Scene Graph", "Topological Map",
    "Waypoint Prediction",
    "Policy", "Controller",
    "Manipulation", "Grasping",
    "Human-Robot Interaction", "HRI",

    # ===== Evaluation / benchmarks =====
    "Evals", "Evaluation Harness",
    "LLM-as-a-Judge",
    "MMLU", "GSM8K", "BBH", "ARC",
    "HumanEval", "MBPP",
    "SWE-bench",
    "MT-Bench", "Chatbot Arena",
    "Needle-in-a-Haystack", "RULER",
    "Hallucination", "事实幻觉",
    "Calibration",
    "Robustness", "OOD", "Out-of-Distribution",

    # ===== Security / safety / attacks =====
    "Prompt Injection", "Jailbreak",
    "Data Poisoning", "Backdoor",
    "Model Stealing", "Extraction Attack",
    "Adversarial Example",
    "PII", "Privacy", "Differential Privacy",
    "Watermarking", "Content Provenance",

    # ===== Major model/product names (optional but useful in keyword filtering) =====
    "GPT", "ChatGPT",
    "Claude",
    "Gemini",
    "Llama", "LLaMA",
    "Mistral",
    "Qwen",
    "o1", "o3",
    "Stable Diffusion", "SDXL",
    "DALL-E", "Sora",
]
    
    # 白名单域名 - 直通 L3
    whitelist_domains: List[str] = [
    # --- Top industry AI labs (official domains) ---
    "openai.com",          # OpenAI :contentReference[oaicite:0]{index=0}
    "anthropic.com",       # Anthropic :contentReference[oaicite:1]{index=1}
    "claude.ai",           # Anthropic Claude product site :contentReference[oaicite:2]{index=2}
    "deepmind.google",     # Google DeepMind :contentReference[oaicite:3]{index=3}
    "google.com",          # Google Research / Gemini / etc.
    "research.google",     # Google Research (often used)
    "ai.google",           # Google AI (often used)

    "microsoft.com",       # Microsoft Research :contentReference[oaicite:4]{index=4}

    "ai.meta.com",         # Meta AI (official research portal)
    "meta.com",
    "nvidia.com",          # NVIDIA Research
    "amazon.science",      # Amazon Science
    "apple.com",           # Apple ML Research (publishes papers/blog)
    "ibm.com",             # IBM Research
    "intel.com",           # Intel Labs
    "samsung.com",         # Samsung Research
    "huawei.com",          # Huawei research portals
    "noahlab.ai",          # Huawei Noah's Ark Lab
    "damo.alibaba.com",    # DAMO Academy
    "bytedance.com",       # ByteDance research portals

    # --- Top academic AI labs (selected, high-signal) ---
    "mit.edu",             # MIT CSAIL etc.
    "stanford.edu",        # Stanford AI Lab etc.
    "berkeley.edu",        # BAIR etc.
    "cmu.edu"             # CMU (Robotics Institute / ML)
]
    
    # ===== L1 噪音过滤配置 =====
    # 强噪音：命中就过滤（建议用于 title + url + 摘要的 hard filter）
    # 这些关键词一旦出现，直接过滤掉内容
    hard_noise_keywords: List[str] = [
    # 教程/入门/教学
    "tutorial", "beginner", "beginners", "introduction", "introduction to",
    "getting started", "quickstart", "quick start", "start here",
    "how to", "step by step", "hands-on", "walkthrough", "guide for",
    "for dummies", "101", "basics", "fundamentals", "crash course",

    # 卖课/培训/认证
    "course", "bootcamp", "training", "certification", "certificate",
    "curriculum", "syllabus", "lesson", "lecture", "workshop",

    # 强营销/引流
    "free", "limited time", "act now", "urgent", "guarantee", "buy now",
    "discount", "coupon", "deal", "offer", "promo", "promotion",
    "subscribe", "newsletter", "webinar", "sign up", "register",
    "affiliate", "sponsored",

    # 标题党/点击诱饵
    "ultimate guide", "complete guide", "everything you need to know",
    "top", "best", "must read", "hacks", "tips and tricks",
    "secrets", "templates", "checklist", "cheat sheet",
    ]
    
    # 弱噪音：命中扣分
    # 这些关键词出现时会降低评分，但不直接过滤
    soft_noise_keywords: List[str] = [
    "resources", "awesome", "curated", "toolbox", "tools list",
    "comparison", "vs", "alternatives", "pricing", "reviews",
    "roadmap", "career", "interview", "resume", "salary",
    "summary", "explained", "explainer", "what is", "why",
    ]
    
    # 中文强噪音（命中就过滤）
    hard_noise_keywords_zh: List[str] = [
    # 教程/入门
    "教程", "入门", "新手", "小白", "初学者", "零基础", "从零", "快速上手", "手把手",
    "一步一步", "实战", "指南", "带你", "教你", "如何", "怎么",

    # 卖课/培训/认证
    "课程", "网课", "训练营", "教学", "课件", "讲义", "大纲", "培训",
    "认证", "考证", "证书", "报名", "直播课", "录播",

    # 强营销/引流
    "免费", "限时", "优惠", "折扣", "券", "秒杀", "购买", "下单", "立即",
    "订阅", "关注", "领取", "下载", "送", "福利", "推广", "赞助",

    # 标题党/流量文
    "最全", "终极", "大全", "合集", "盘点", "Top", "最佳", "必看", "干货",
    "套路", "秘籍", "技巧", "清单", "模板", "速览", "一文读懂", "科普",
    ]
    
    # 中文弱噪音（扣分）
    soft_noise_keywords_zh: List[str] = [
    "资源", "工具", "对比", "测评", "替代", "方案", "选型",
    "职业", "求职", "面试", "简历", "薪资", "路线图", "规划",
    "总结", "解读", "是什么", "为什么",
    ]
    
    # 正则：专杀 listicle / 标题公式（非常有效）
    # 这些正则表达式用于匹配常见的标题公式，如 "Top 10 ways to..."
    noise_regex: List[str] = [
    r"\btop\s*\d+\b",
    r"\b\d+\s*(ways|tips|tricks|templates|examples|steps)\b",
    r"\b(ultimate|complete)\s+guide\b",
    r"\b(checklist|cheat\s*sheet|templates?)\b",
    r"\b(you\s+won't\s+believe|what\s+happens\s+next)\b",
    ]
    
    # 热度阈值
    min_hn_score: int = 10
    min_hf_upvotes: int = 5

    # Hacker News 相关性过滤（避免 HN Top Stories 混入非 AI 新闻）
    # 仅用于 HN 入库前的“强相关”关键词判定；白名单域名仍然直通。
    hackernews_keywords: List[str] = [
        "ai", "artificial intelligence",
        "llm", "large language model",
        "gpt", "chatgpt", "openai",
        "anthropic", "claude",
        "gemini", "deepmind",
        "qwen", "mistral", "llama",
        "diffusion", "stable diffusion", "sora", "dall-e",
        "rag", "retrieval-augmented", "embedding",
        "prompt", "prompting",
        "transformer", "vision-language", "multimodal",
        "machine learning", "ml",
    ]
    
    # 过滤数量配置
    l2_papers_limit: int = 40
    l2_news_limit: int = 30
    l2_news_min_score: float = 6.0
    l2_news_min_reason_len: int = 20
    # L2 论文分类配额：每类进入 L3 的数量（18篇）
    l2_paper_category_min: int = 18
    l2_paper_category_max: int = 18
    l3_final_limit: int = 10
    l3_papers_target: int = 18
    l3_news_target: int = 11
    l3_hf_papers_target: int = 4
    l3_arxiv_papers_target: int = 14
    # 论文分类展示配置（每个领域展示的数量）
    paper_category_targets: dict = {
        "General AI": 6,
        "Computer Vision": 6,
        "Robotics": 6,
    }
    paper_categories: List[str] = ["General AI", "Computer Vision", "Robotics"]
    l3_paper_category_target: int = 6
    # 论文摄取上限（进入 L1/L2 前）
    hf_daily_limit: int = 20
    # 0 表示不限制（拉取该公告日的全部论文）
    arxiv_daily_limit: int = 0

    # Reddit 配置
    reddit_subreddits: List[str] = ["MachineLearning"]
    reddit_sort: str = "top"  # top / hot / new
    reddit_limit: int = 50
    reddit_min_upvotes: int = 10
    reddit_user_agent: str = "AI-Tides/1.0 (https://github.com/ai-tides)"

    # GitHub Trending 配置
    github_trending_url: str = "https://github.com/trending"
    github_trending_limit: int = 25
    github_trending_keywords: List[str] = [
        "ai", "llm", "gpt", "diffusion", "vision", "agent", "ml", "machine learning"
    ]

    # 语义去重配置
    semantic_dedup_enabled: bool = True
    semantic_dedup_threshold: float = 0.85
    semantic_dedup_max_items: int = 200
    
    # Qwen 模型配置
    qwen_l2_model: str = "qwen-flash"
    qwen_l3_model: str = "qwen3-max"
    # L3 并发控制（避免高并发导致接口断连）
    l3_max_concurrency: int = 1
    # L3 摘要批次大小（避免单次请求过大）
    l3_summary_batch_size: int = 8
    # Qwen 请求超时（秒）
    qwen_timeout_seconds: float = 60.0
    
    # 来源权重配置 (Source Weighting)
    # 匹配 source_name 或 url 中的关键词，给予加分
    source_weights: dict = {
        # Top Labs
        "OpenAI": 2.0,
        "Anthropic": 2.0,
        "DeepMind": 2.0,
        "Google": 1.5,
        "Meta": 1.5,
        "Microsoft": 1.5,
        "NVIDIA": 1.5,
        "BAIR": 1.5,
        
        # Top Media
        "The Verge": 1.0,
        "TechCrunch": 1.0,
        "VentureBeat": 1.0,
        "MIT Technology Review": 1.0,
        "Nature": 1.5,
        "Science": 1.5,
        
        # High Signal
        "Hugging Face": 1.0,
    }
    
    # 新闻来源可信度偏置
    # 官方来源（白名单域名 / 白名单 RSS）给予额外加分
    # 非官方来源降低权重（可能存在误导或未经证实的信息）
    official_news_bonus: float = 0.6
    non_official_news_penalty: float = -1.0

    # ===== RSS 源配置 =====
    # RSS (Really Simple Syndication) 是什么？
    # RSS 是一种网站内容聚合格式，允许网站自动发布最新内容。
    # 通过 RSS Feed，我们可以：
    # 1. 自动获取官方博客的最新文章（无需爬虫）
    # 2. 获取结构化数据（标题、摘要、发布时间、链接）
    # 3. 避免网页解析的复杂性和不稳定性
    #
    # 在 AI Tides Pipeline 中的作用：
    # - 作为新闻数据源之一（与 Hacker News 并列）
    # - 主要获取官方 AI 实验室的博客更新
    # - 白名单 RSS 源会直接进入 L3，跳过 L1/L2 过滤
    #
    # RSS Feed 格式示例：
    # <rss>
    #   <item>
    #     <title>GPT-5 Release</title>
    #     <link>https://openai.com/blog/gpt-5</link>
    #     <description>We're releasing GPT-5...</description>
    #     <pubDate>2024-01-15</pubDate>
    #   </item>
    # </rss>
    #
    # 配置说明：
    # - name: RSS 源的显示名称
    # - url: RSS Feed 的 URL 地址（通常是 /rss.xml 或 /feed.xml）
    # - whitelist: 是否为白名单（True=直通 L3，False=正常过滤流程）
    rss_feeds: List[dict] = [
        # 官方 AI 实验室博客（白名单，直通 L3）
        {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "whitelist": True},
        # Anthropic 没有公开 RSS，跳过
        # {"name": "Anthropic", "url": "https://www.anthropic.com/news/rss", "whitelist": True},
        {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "whitelist": True},
        {"name": "DeepMind Blog", "url": "https://deepmind.google/blog/rss.xml", "whitelist": True},
        {"name": "Microsoft Research", "url": "https://www.microsoft.com/en-us/research/feed/", "whitelist": True},
        {"name": "NVIDIA Blog", "url": "https://blogs.nvidia.com/feed/", "whitelist": True},
        {"name": "BAIR Blog", "url": "https://bair.berkeley.edu/blog/feed.xml", "whitelist": True},
        # Meta AI 没有公开 RSS，跳过
        # {"name": "Meta AI", "url": "https://ai.meta.com/blog/rss/", "whitelist": True},

        # 国际主流 AI 媒体（非白名单，需经过 L1/L2 筛选）
        {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "whitelist": False},
        {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "whitelist": False},
        {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "whitelist": False},
        
        # 其他高质量来源（需要正常过滤）
        {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "whitelist": False},
        {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "whitelist": False},
        {"name": "AWS Machine Learning Blog", "url": "https://aws.amazon.com/blogs/machine-learning/feed/", "whitelist": False},
        {"name": "Google Cloud AI", "url": "https://cloud.google.com/blog/products/ai-machine-learning/rss", "whitelist": False},
        {"name": "Microsoft AI Blog", "url": "https://blogs.microsoft.com/ai/feed/", "whitelist": False},
        {"name": "NVIDIA Developer AI", "url": "https://developer.nvidia.com/blog/category/artificial-intelligence/feed/", "whitelist": False},
        {"name": "MIT CSAIL News", "url": "https://news.mit.edu/topic/mitcomputers-rss.xml", "whitelist": False},

        # 中国顶尖 AI 实验室/公司（GitHub 官方活动流）
        {"name": "Tencent AI Lab (GitHub)", "url": "https://github.com/tencent-ailab.atom", "whitelist": False},
        {"name": "Baidu Research (GitHub)", "url": "https://github.com/baidu-research.atom", "whitelist": False},
        {"name": "Alibaba DAMO Academy (GitHub)", "url": "https://github.com/alibaba-damo-academy.atom", "whitelist": False},
        {"name": "Huawei Noah's Ark (GitHub)", "url": "https://github.com/huawei-noah.atom", "whitelist": False},
        {"name": "PaddlePaddle (GitHub)", "url": "https://github.com/PaddlePaddle.atom", "whitelist": False},
        {"name": "OpenGVLab (GitHub)", "url": "https://github.com/OpenGVLab.atom", "whitelist": False},
    ]
    
    # 输出配置
    output_dir: str = "pipeline/output"
    data_json_path: str = "src/data/tide-news.json"
    public_reports_dir: str = "public/reports"
    public_history_path: str = "public/history.json"
    feedback_path: str = "pipeline/output/feedback.json"


# 全局配置实例
config = Config()
