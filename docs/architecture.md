# 架构概览

AI Tides 由三部分组成：数据摄取、内容过滤、前端展示。

```
Sources -> Ingestion -> L1 Heuristic -> L2 Scoring -> L3 Refining -> Output -> Frontend
```

## 模块说明

- **Ingestion**：抓取新闻与论文（HN/RSS/Reddit/GitHub/Arxiv/HF）
- **Filters**：L1/ L2/ L3 多级过滤
- **Output**：生成 JSON / Markdown / 前端数据
- **Frontend**：展示今日新闻与论文 + 搜索 + 日期切换

## 关键数据路径

- `pipeline/output/report_YYYY-MM-DD.json`
- `public/reports/report_YYYY-MM-DD.json`
- `public/history.json`
- `src/data/tide-news.json`
