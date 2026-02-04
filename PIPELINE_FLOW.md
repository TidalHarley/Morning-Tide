# Morning Tide Pipeline 完整流程文档

## 📋 目录

1. [系统概述](#系统概述)
2. [整体架构](#整体架构)
3. [数据流程](#数据流程)
4. [各阶段详细说明](#各阶段详细说明)
5. [配置说明](#配置说明)
6. [前端展示逻辑](#前端展示逻辑)
7. [技术栈](#技术栈)
8. [改进方向](#改进方向)

---

## 系统概述

**Morning Tide** 是一个自动化 AI 内容聚合与筛选系统，通过三级过滤漏斗（L1/L2/L3）从海量数据源中筛选出最值得关注的 AI 论文和新闻，并生成中文摘要和每日报告。

### 核心目标

- **时效性**：确保内容不超过 1 天，周末跳过 arXiv 抓取
- **质量优先**：通过多级过滤确保内容质量
- **全球视野**：关注真正具有全球影响力的 AI 进展
- **自动化**：全流程自动化，无需人工干预

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Phase 1: 数据摄取                         │
├─────────────────────────────────────────────────────────────┤
│  Papers: arXiv (50篇) + HuggingFace Daily (20篇)            │
│  News: Hacker News + RSS Feeds (官方博客 + 国际媒体)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Phase 2: 三级过滤漏斗                            │
├─────────────────────────────────────────────────────────────┤
│  L1: 启发式过滤 (HeuristicFilter)                           │
│      ├─ 关键词匹配 (AI相关)                                 │
│      ├─ 噪音过滤 (教程/营销/标题党)                          │
│      ├─ 热度阈值 (HN score ≥10, HF upvotes ≥5)              │
│      └─ 白名单直通 (官方博客跳过 L1/L2)                      │
│                                                              │
│  L2: AI 智能打分 (AIScorer)                                 │
│      ├─ GLM-4.5-Flash 批量打分 (0-10分)                     │
│      ├─ 综合得分 = AI分数×0.6 + 社区热度×0.4 + 来源加权     │
│      └─ 选取 Top 30 进入 L3                                  │
│                                                              │
│  L3: 深度精炼 (Refiner)                                     │
│      ├─ GLM-4.7 最终筛选 (12篇论文 + 11条新闻)              │
│      ├─ 生成中文摘要 (主要内容/关键点/重要性)                │
│      └─ 自动打标签                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Phase 3: 输出生成                               │
├─────────────────────────────────────────────────────────────┤
│  - Markdown 报告 (report_YYYY-MM-DD.md)                     │
│  - JSON 数据 (report_YYYY-MM-DD.json)                       │
│  - 前端数据 (src/data/tide-news.json)                       │
│  - 历史记录 (history.json)                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 数据流程

### 1. 数据摄取阶段 (Phase 1)

#### 1.1 论文摄取

**arXiv 论文**
- **时间窗口**：滚动 24 小时（从当前时间回溯 1 天）
- **周末处理**：周末跳过抓取（美国周末不更新）
- **时区**：Asia/Shanghai（北京时间）
- **抓取逻辑**：
  1. 从 arXiv 列表页 (`/list/{category}/recent`) 解析"公告日期"
  2. 提取公告日期在时间窗口内的论文 ID
  3. 批量调用 arXiv API 获取完整元数据（每批 50 篇）
  4. 限制：最多抓取 50 篇（`arxiv_daily_limit`）
- **类别**：`cs.AI`, `cs.CL`, `cs.CV`, `cs.RO`, `cs.LG`

**HuggingFace Daily Papers**
- **时间窗口**：无限制（使用最近的每日总结）
- **抓取逻辑**：调用 HuggingFace Daily Papers API
- **限制**：最多抓取 20 篇（`hf_daily_limit`）

#### 1.2 新闻摄取

**Hacker News**
- **时间窗口**：最近 24 小时（`hours_lookback`）
- **抓取逻辑**：
  1. 获取 Top Stories IDs（前 200 条）
  2. 批量获取故事详情
  3. 过滤时间范围内的内容
- **评分**：使用 HN `score` 字段

**RSS Feeds**
- **时间窗口**：最近 24 小时
- **来源分类**：
  - **白名单**（`whitelist: True`）：官方 AI 实验室博客，直通 L3
    - OpenAI Blog
    - Anthropic
    - Google AI Blog
    - DeepMind Blog
    - Microsoft Research
    - NVIDIA Blog
    - BAIR Blog
    - Meta AI
  - **非白名单**（`whitelist: False`）：国际主流 AI 媒体，需经过 L1/L2 筛选
    - The Verge AI
    - TechCrunch AI
    - VentureBeat AI
    - Hugging Face Blog
    - MIT Tech Review AI

---

### 2. 三级过滤漏斗 (Phase 2)

#### 2.1 L1: 启发式过滤 (HeuristicFilter)

**目标**：快速过滤明显不符合要求的内容，减少 AI API 调用成本

**过滤规则**（按顺序执行）：

1. **白名单检查**（优先级最高）
   - 如果 URL 域名匹配 `whitelist_domains`，直接通过
   - 白名单内容跳过后续检查，直接进入 L3

2. **关键词匹配**
   - 检查标题和摘要是否包含 AI 相关关键词（`ai_keywords`）
   - 包含 200+ 个 AI 领域关键词（LLM、Transformer、RLHF、Agent 等）

3. **噪音过滤**
   - **强噪音**（命中即过滤）：
     - 教程类：`tutorial`, `beginner`, `introduction`, `教程`, `入门`
     - 营销类：`free`, `discount`, `优惠`, `限时`
     - 标题党：`ultimate guide`, `top 10`, `最全`, `大全`
   - **正则模式**：匹配标题公式（如 `Top \d+ ways`）

4. **热度阈值**
   - **论文**：
     - arXiv：默认通过（无评分机制）
     - HuggingFace：`upvotes ≥ 5`（`min_hf_upvotes`）
   - **新闻**：
     - Hacker News：`score ≥ 10`（`min_hn_score`）
     - RSS：默认通过（无评分机制）

**输出**：
- `papers_l2`：通过正常过滤的论文（进入 L2）
- `papers_whitelist`：白名单论文（跳过 L2，进入 L3）
- `news_l2`：通过正常过滤的新闻（进入 L2）
- `news_whitelist`：白名单新闻（跳过 L2，进入 L3）

#### 2.2 L2: AI 智能打分 (AIScorer)

**目标**：使用 GLM-4.5-Flash 对内容进行批量打分，评估"全球影响力"和"行业变革性"

**打分标准**（0-10 分）：
- **10 分**：改变 AI 历史进程的里程碑事件（如 GPT-4 发布、Sora 发布）
- **9 分**：具有全球产业影响力的重大发布、顶级实验室的核心突破
- **7-8 分**：显著提升现有技术水平的 SOTA 工作、主流科技媒体头条报道
- **5-6 分**：扎实的研究进展、有一定实用价值的开源项目
- **3-4 分**：过于细分领域的改进、影响力受限的小型工具
- **0-2 分**：纯营销、低质量教程、标题党

**Prompt 设计**：
- 强调"全球影响力"和"行业变革性"
- 要求识别真正的技术干货，警惕营销炒作
- 关注能影响未来 6-12 个月行业走向的内容

**综合得分计算**：
```
综合得分 = AI分数 × 0.6 + 归一化社区热度 × 0.4 + 白名单加分(2.0) + 来源加权
```

**来源加权**（`source_weights`）：
- OpenAI, Anthropic, DeepMind: +2.0
- Google, Meta, Microsoft, NVIDIA, BAIR: +1.5
- The Verge, TechCrunch, VentureBeat, MIT Tech Review: +1.0
- Nature, Science: +1.5
- Hugging Face: +1.0

**输出**：
- 对 `papers_l2` 和 `news_l2` 进行打分
- 白名单内容也需要打分（用于排序）
- 合并所有内容，按综合得分排序
- 选取 Top 30 论文和 Top 30 新闻进入 L3（`l2_papers_limit`, `l2_news_limit`）

#### 2.3 L3: 深度精炼 (Refiner)

**目标**：使用 GLM-4.7 进行最终筛选，生成中文摘要和标签

**最终筛选**：
- **论文**：从候选池中选出 12 篇
  - HuggingFace：3 篇（`l3_hf_papers_target`）
  - arXiv：9 篇（`l3_arxiv_papers_target`）
- **新闻**：从候选池中选出 11 条（`l3_news_target`）

**筛选标准**：
1. **影响力**（第一要务）：对 AI 行业有重大影响，代表今天 AI 领域最核心的进展
2. **创新性**：代表技术突破或新方向
3. **时效性**：今日最值得关注的动态
4. **多样性**：尽量覆盖不同领域（但影响力优先）

**中文摘要生成**：
- **格式要求**：必须包含三部分
  - **主要内容**：简要描述内容的核心
  - **关键点**：列出最重要的技术点或信息点
  - **为什么重要**：说明该内容的重要性和影响
- **语言风格**：简洁但要讲清楚，不要空泛，使用专业但易懂的中文
- **备用方案**：如果 GLM 失败或返回空摘要，使用 `_fallback_summary()` 生成

**自动打标签**：
- 基于预定义标签库（`TAG_LIBRARY`）进行关键词匹配
- 标签类别：
  - 技术领域：LLM, Vision, Multimodal, Agent, Robotics, Diffusion, Audio, 3D
  - 技术方法：Training, Inference, RAG, Reasoning
  - 来源分类：Industry, Research, Open Source, Benchmark
- 每个内容最多 4 个标签

**每日综述生成**：
- 由 GLM-4.7 生成 200-300 字的中文综述
- 分条分点概括今天的主要动态和趋势

---

### 3. 输出生成阶段 (Phase 3)

**输出文件**：

1. **Markdown 报告** (`report_YYYY-MM-DD.md`)
   - 每日综述
   - 精选论文列表（含摘要、标签、作者）
   - 行业新闻列表（含摘要、标签）
   - Pipeline 统计信息

2. **JSON 报告** (`report_YYYY-MM-DD.json`)
   - 完整的结构化数据
   - 用于存档和分析

3. **前端数据** (`src/data/tide-news.json`)
   - 前端可直接读取的 JSON 格式
   - 包含所有展示所需字段

4. **历史记录** (`history.json`)
   - 最近 30 天的报告摘要
   - 包含日期、论文数、新闻数、Top 论文/新闻标题

---

## 配置说明

### 核心配置 (`pipeline/config.py`)

#### API 配置
```python
zhipu_api_key: str  # 智谱 AI API Key（从环境变量读取）
```

#### 论文摄取配置
```python
arxiv_categories: List[str]  # arXiv 类别
papers_freshness_days: int = 1  # 时效天数
papers_window_mode: str = "rolling"  # 时间窗口模式（"rolling" 或 "calendar"）
papers_timezone: str = "Asia/Shanghai"  # 时区
papers_skip_weekends: bool = True  # 周末跳过
hf_daily_limit: int = 20  # HF 每日限制
arxiv_daily_limit: int = 50  # arXiv 每日限制
```

#### 过滤配置
```python
# L1 阈值
min_hn_score: int = 10  # HN 最低分数
min_hf_upvotes: int = 5  # HF 最低点赞数

# L2 限制
l2_papers_limit: int = 30  # L2 论文候选数
l2_news_limit: int = 30  # L2 新闻候选数

# L3 目标
l3_papers_target: int = 12  # 最终论文数
l3_news_target: int = 11  # 最终新闻数
l3_hf_papers_target: int = 3  # HF 论文数
l3_arxiv_papers_target: int = 9  # arXiv 论文数
```

#### 模型配置
```python
glm_free_model: str = "glm-4.5-flash"  # L2 使用的免费模型
glm_premium_model: str = "glm-4.7"  # L3 使用的高级模型
```

#### 来源权重
```python
source_weights: dict = {
    "OpenAI": 2.0,
    "Anthropic": 2.0,
    "DeepMind": 2.0,
    "Google": 1.5,
    # ... 更多来源
}
```

#### RSS 源配置
```python
rss_feeds: List[dict] = [
    {"name": "OpenAI Blog", "url": "...", "whitelist": True},
    {"name": "The Verge AI", "url": "...", "whitelist": False},
    # ... 更多源
]
```

---

## 前端展示逻辑

### 数据读取

前端从 `src/data/tide-news.json` 读取数据，该文件由 Pipeline 自动生成。

### 布局结构

```
┌─────────────────────────────────────────────────────────┐
│                    Header (TideHeader)                  │
│  [Theme Toggle] [Language Toggle] [Font Size Slider]   │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                    Hero Section                          │
│              (HeroHeadline / TideHero)                  │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│              Main Content (Grid Layout)                  │
│  ┌──────────────────────┐  ┌──────────────────────────┐  │
│  │  News of the Day   │  │      Curated List        │  │
│  │  (Featured)        │  │      (10 items)          │  │
│  │  [1st news item]   │  │  [2nd-11th news items]  │  │
│  └──────────────────────┘  └──────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Papers Section                       │  │
│  │  ┌──────────────┐  ┌──────────────────────────┐ │  │
│  │  │ HuggingFace  │  │        arXiv             │ │  │
│  │  │  (3 papers)  │  │      (9 papers)          │ │  │
│  │  └──────────────┘  └──────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 数据映射

**News of the Day** (`FeaturedPerspective`)：
- 使用 `news[0]`（第一条新闻）

**Curated List** (`CuratedList`)：
- 使用 `news[1:11]`（第 2-11 条新闻，共 10 条）
- 标题单行显示，超出部分用省略号
- 鼠标悬停显示完整摘要

**Papers Section** (`PapersSection`)：
- **HuggingFace**：筛选 `source_type === "huggingface"`，显示前 3 篇
- **arXiv**：筛选 `source_type === "arxiv"`，显示前 9 篇
- arXiv 论文的摘要直接显示在标题下方（卡片内）
- 鼠标悬停显示完整摘要（HF 论文）

### 交互功能

1. **字体大小调整**（`FontSizeToggle`）
   - 滑块控制 `html` 元素的 `data-font-size` 属性
   - CSS 变量 `--font-size-base` 响应变化
   - 主题/语言切换按钮使用 `font-size-fixed` 类，不受影响

2. **摘要显示**
   - Curated List：鼠标悬停显示完整摘要
   - Papers Section：arXiv 论文摘要直接显示，HF 论文悬停显示

3. **链接跳转**
   - 点击标题或卡片跳转到原始链接（`url` 字段）

---

## 技术栈

### 后端
- **Python 3.x**
- **Pydantic**：数据模型验证
- **Requests**：HTTP 请求
- **Feedparser**：RSS 解析
- **Tenacity**：重试机制
- **ZhipuAI SDK**：智谱 AI API 调用
- **ZoneInfo**：时区处理

### 前端
- **React + TypeScript**
- **Vite**：构建工具
- **Tailwind CSS**：样式框架
- **shadcn/ui**：UI 组件库

### AI 模型
- **GLM-4.5-Flash**：L2 批量打分（免费）
- **GLM-4.7**：L3 深度精炼（高级）

---

## 改进方向

### 1. 数据源扩展
- [ ] 增加更多国际 AI 媒体 RSS 源
- [ ] 支持 Twitter/X 热门 AI 推文
- [ ] 集成 Reddit r/MachineLearning
- [ ] 支持 YouTube AI 频道

### 2. 过滤算法优化
- [ ] L1 关键词库动态更新（基于 L2/L3 反馈）
- [ ] L2 打分 Prompt 的 A/B 测试
- [ ] 引入用户反馈机制（点赞/点踩）优化权重
- [ ] 实现去重算法（基于语义相似度）

### 3. 摘要质量提升
- [ ] 摘要长度可配置（短/中/长）
- [ ] 支持多语言摘要（英文、日文等）
- [ ] 提取关键图表/代码片段
- [ ] 生成可视化摘要（时间线、关系图）

### 4. 前端功能增强
- [ ] 支持日期切换（查看历史报告）
- [ ] 搜索功能（按标题/标签/作者）
- [ ] 收藏功能（本地存储）
- [ ] 分享功能（生成分享链接）
- [ ] 暗色模式优化

### 5. 性能优化
- [ ] 并行处理多个数据源
- [ ] 缓存机制（避免重复抓取）
- [ ] 增量更新（只抓取新内容）
- [ ] API 调用批量化（减少请求次数）

### 6. 监控与运维
- [ ] 添加健康检查端点
- [ ] 错误告警（邮件/Telegram）
- [ ] 性能指标监控（API 调用次数、耗时）
- [ ] 日志分析（识别常见错误）

### 7. 数据质量
- [ ] 摘要质量评分（基于用户反馈）
- [ ] 内容去重（基于 URL 和语义）
- [ ] 时效性验证（确保不超过 1 天）
- [ ] 来源可信度评分

### 8. 用户体验
- [ ] 移动端适配优化
- [ ] 加载状态提示
- [ ] 错误页面友好提示
- [ ] 无障碍功能（ARIA 标签）

---

## 运行方式

### 开发环境
```bash
# 安装依赖
pip install -r pipeline/requirements.txt

# 设置环境变量
export ZHIPU_API_KEY="your_api_key"

# 运行 Pipeline
python -m pipeline.main

# 调试模式（更详细日志）
python -m pipeline.main --debug

# 干运行模式（不保存文件）
python -m pipeline.main --dry-run
```

### 前端开发
```bash
cd ai-pulse-dashboard
npm install
npm run dev
```

### 生产环境
建议使用定时任务（如 cron）每天自动运行 Pipeline：
```bash
# 每天 UTC 2:00（北京时间 10:00）运行
0 2 * * * cd /path/to/project && python -m pipeline.main
```

---

## 注意事项

1. **API Key 安全**：不要将 API Key 提交到 Git，使用 `.env` 文件或环境变量
2. **时区处理**：arXiv 周末不更新，Pipeline 会自动跳过
3. **API 限制**：注意智谱 AI API 的调用频率限制
4. **数据备份**：定期备份 `pipeline/output/` 目录
5. **错误处理**：Pipeline 包含重试机制，但网络问题可能导致部分数据缺失

---

## 总结

AI Tides Pipeline 通过三级过滤漏斗（L1/L2/L3）实现了从海量数据源到精选内容的自动化流程。系统设计注重时效性、质量和自动化，能够有效筛选出真正具有全球影响力的 AI 进展。

当前系统已经实现了 MVP 功能，后续可以根据用户反馈和实际需求进行迭代优化。
