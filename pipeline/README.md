# 🌊 AI Tides Pipeline

AI 情报聚合系统的数据处理后端。

## 架构概览

```
Pipeline Flow:
┌─────────────────────────────────────────────────────────────────┐
│                     Phase 1: Ingestion                          │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌───────────┐ │
│  │ HuggingFace │  │   arXiv     │  │   HN     │  │    RSS    │ │
│  │   Papers    │  │   Papers    │  │  News    │  │   Feeds   │ │
│  └──────┬──────┘  └──────┬──────┘  └────┬─────┘  └─────┬─────┘ │
│         └────────────────┴──────────────┴──────────────┘       │
└────────────────────────────────┬────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Phase 2: 3-Stage Filtering                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ L1: Heuristic Filter [$0]                               │   │
│  │ • Keyword matching • Score threshold • Whitelist bypass │   │
│  └────────────────────────────┬────────────────────────────┘   │
│                               ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ L2: AI Scoring [Free - GLM-4-Flash]                     │   │
│  │ • Innovation score • Impact assessment • Top 15 each    │   │
│  └────────────────────────────┬────────────────────────────┘   │
│                               ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ L3: Deep Refining [Premium - GLM-4-Plus]                │   │
│  │ • Final selection • Chinese summary • Daily intro       │   │
│  └────────────────────────────┬────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Phase 3: Output                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐    │
│  │  Markdown   │  │    JSON     │  │   Frontend Update    │    │
│  │   Report    │  │   Archive   │  │   (tide-news.json)   │    │
│  └─────────────┘  └─────────────┘  └──────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
cd pipeline
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 创建 .env 文件
cp .env.example .env

# 编辑 .env，填入你的 API Key
# ZHIPU_API_KEY=your_api_key_here
```

### 3. 运行 Pipeline

```bash
# 从项目根目录运行完整 Pipeline
python -m pipeline.main

# 调试模式（详细日志）
python -m pipeline.main --debug

# 干运行模式（不保存文件）
python -m pipeline.main --dry-run
```

### 4. 调试和测试

```bash
# 使用调试工具（推荐）
# 测试数据摄取
python -m pipeline.debug ingestion

# 测试 L1 过滤（使用模拟数据）
python -m pipeline.debug l1

# 测试完整 Pipeline（使用模拟数据，不消耗 API）
python -m pipeline.debug mock

# 测试完整 Pipeline（使用真实数据）
python -m pipeline.debug full
```

详细调试指南请查看 [DEVELOPMENT.md](DEVELOPMENT.md)

## 目录结构

```
pipeline/
├── __init__.py          # 包初始化
├── main.py              # 主程序入口
├── config.py            # 配置文件
├── models.py            # 数据模型
├── output.py            # 输出生成器
├── requirements.txt     # Python 依赖
├── ingestion/           # 数据摄取模块
│   ├── __init__.py
│   ├── papers.py        # 论文源 (HF + arXiv)
│   └── news.py          # 新闻源 (HN + RSS)
├── filters/             # 过滤器模块
│   ├── __init__.py
│   ├── heuristic.py     # L1 启发式过滤
│   ├── ai_scorer.py     # L2 AI 打分
│   └── refiner.py       # L3 深度精炼
└── output/              # 输出目录
    ├── report_YYYY-MM-DD.md
    ├── report_YYYY-MM-DD.json
    └── history.json
```

## 配置说明

在 `config.py` 中可以调整：

- **AI 关键词列表**: 用于 L1 过滤
- **白名单域名**: 直通 L3 的可信来源
- **热度阈值**: HN 分数、HF upvotes 等
- **过滤数量**: L2/L3 保留的内容数量
- **GLM 模型**: 免费/付费模型选择

## GitHub Actions

Pipeline 配置为每天 UTC 23:00 (北京时间 07:00) 自动运行。

在仓库 Settings > Secrets 中添加：
- `ZHIPU_API_KEY`: 智谱 AI API Key

## 成本估算

- **L1 (启发式)**: $0
- **L2 (GLM-4-Flash)**: 免费额度内
- **L3 (GLM-4-Plus)**: ~$0.01-0.05/天

总计: **基本免费** (在智谱 AI 免费额度内)

## License

MIT
