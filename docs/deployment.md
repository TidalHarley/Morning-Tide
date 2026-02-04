# 部署指南（GitHub Pages + GitHub Actions）

本项目推荐的线上运行方式是：**GitHub Pages 托管前端 + GitHub Actions 每天生成数据并自动部署**。

## 目标效果

- 站点地址：`https://tidalharley.github.io/Morning-Tide/`
- 每天北京时间 07:00 自动：
  - 抓取新闻/论文
  - 生成 `src/data/tide-news.json`、`public/reports/`、`public/history.json`
  - 提交回仓库
  - 构建并发布到 GitHub Pages

## 一次性配置（仓库拥有者）

1. **启用 GitHub Pages**
   - Repo → Settings → Pages
   - Source 选择 **GitHub Actions**
2. **配置 Secrets（保证站点持续运行）**
   - Repo → Settings → Secrets and variables → Actions → New repository secret
   - 添加 `DASHSCOPE_API_KEY`

> 说明：`DASHSCOPE_API_KEY` 仅在 GitHub Actions 中使用，不会暴露给网页访问者。

## Fork / 复刻部署（普适）

如果别人 fork 你的仓库：只要在自己的 fork 仓库里同样设置 `DASHSCOPE_API_KEY` Secret，即可让 Actions 正常每日运行并生成自己的站点数据。

## 本地部署（开发/调试）

```bash
npm install
npm run dev
```

运行 pipeline：

```bash
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r pipeline/requirements.txt
python -m pipeline.main
```
