## 信息渠道清单与条数统计

日期参考：`2026-01-28`（来自 `pipeline/output/report_2026-01-28.json`）

### 总体条数（当天）
- 论文摄取总数：20
- 新闻摄取总数：62
- L1 通过：论文 20，新闻 52
- L2 评分：论文 20，新闻 30
- L3 入选：论文 18，新闻 11

> 说明：以上为当日全量摄取与筛选统计，不含按来源拆分的条数。

---

## 论文渠道
### 1) HuggingFace Daily Papers
- API：`https://huggingface.co/api/daily_papers`
- 类型：论文

### 2) arXiv
- API：`http://export.arxiv.org/api/query`
- 列表页：`http://export.arxiv.org/list/{cat}/recent`
- 类别：`cs.AI`, `cs.CV`, `cs.RO`
- 类型：论文

---

## 新闻渠道
### 1) Hacker News
- 来源：Hacker News Top/相关内容
- 类型：新闻

### 2) Reddit
- 子版块：`r/MachineLearning`
- 类型：新闻

### 3) GitHub Trending
- 来源：GitHub Trending 列表
- 类型：新闻（开源项目/趋势）

### 4) RSS 聚合（官方/媒体/机构）
**官方/白名单 RSS（直通）**
- OpenAI Blog — `https://openai.com/blog/rss.xml`
- Google AI Blog — `https://blog.google/technology/ai/rss/`
- DeepMind Blog — `https://deepmind.google/blog/rss.xml`
- Microsoft Research — `https://www.microsoft.com/en-us/research/feed/`
- NVIDIA Blog — `https://blogs.nvidia.com/feed/`
- BAIR Blog — `https://bair.berkeley.edu/blog/feed.xml`

**媒体/机构 RSS（需过滤）**
- The Verge AI — `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml`
- TechCrunch AI — `https://techcrunch.com/category/artificial-intelligence/feed/`
- VentureBeat AI — `https://venturebeat.com/category/ai/feed/`
- Hugging Face Blog — `https://huggingface.co/blog/feed.xml`
- MIT Tech Review AI — `https://www.technologyreview.com/topic/artificial-intelligence/feed`
- AWS Machine Learning Blog — `https://aws.amazon.com/blogs/machine-learning/feed/`
- Google Cloud AI — `https://cloud.google.com/blog/products/ai-machine-learning/rss`
- Microsoft AI Blog — `https://blogs.microsoft.com/ai/feed/`
- NVIDIA Developer AI — `https://developer.nvidia.com/blog/category/artificial-intelligence/feed/`
- MIT CSAIL News — `https://news.mit.edu/topic/mitcomputers-rss.xml`

---

## 按来源条数（当前说明）
目前 `report_2026-01-28.json` 中尚未包含“每个来源的条数统计”。  
如需按来源精确条数，请重新运行 pipeline 生成最新报告。  
后续会在 `pipeline/output/news_sources_YYYY-MM-DD.md` 中自动输出“来源 -> 条数”统计。
