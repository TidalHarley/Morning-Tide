# Morning Tide: your personal AI news secretary

**Free · no-code · easy deploy · high-signal**

Updated daily (UTC+8 (China Standard Time) at **07:00**)

[中文(Chinese)](README.zh-CN.md)

Live site: https://tidalharley.github.io/Morning-Tide/

<p align="center">
  <img src="./frontpage.png" alt="TidalMorning front page" width="92%" />
</p>



## Why Morning Tide?

### For students & AI enthusiasts (no-code, free, zero barrier)

- **One page, the whole day**: curated AI news from **20+ high-signal sources** (official labs + major media), refined into what actually matters.
- **Kill the information gap**: **5 minutes a day** to stay ahead of the curve — *catch up with the AI tides*.
- **No setup tax**: open-source, no accounts, no configuration, no ads — just open and read.

### For developers (deploy fast, maintain less)

- **Fast to ship**: Vite frontend + Python pipeline; works great with GitHub Pages + GitHub Actions (or cron).
- **Auto-refresh daily**: run once a day, update `tide-news.json`, and the site stays current.
- **Low daily cost**: typically **< ~$0.5/day** (depends on model choice and usage).
- **Easy to customize**: clean, structured codebase for personalized sources, scoring, and UI.

### For researchers (scan fast, trust the sources)

- **Save hours**: daily ingest from **arXiv + Hugging Face**, summarized for quick scanning.
- **Field-aware picks**: papers grouped by **General AI / Computer Vision / Robotics** to map what’s moving.
- **Credible by design**: every item links back to the original source.

<p align="center">
  <img src="./paper.png" alt="TidalMorning paper preview" width="92%" />
</p>

### Your best daily AI brief

- In an age of information overload, **high-quality signal** protects your attention and helps you make better decisions.
- **Busy professionals**: a 5-minute morning spark to stay sharp and inspired.
- **Researchers**: quick overview → pick a few papers to deep dive.
- **Builders & creators**: keep your stack current and avoid “I missed that launch” moments.

---
<p align="center">
  <img src="./content.png" alt="TidalMorning content preview" width="92%" />
</p>

---

## Sources

<table align="center">
  <tr>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=arxiv.org" alt="arXiv" width="26" height="26" /><br/>arXiv</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=huggingface.co" alt="Hugging Face" width="26" height="26" /><br/>Hugging Face Daily Papers</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=news.ycombinator.com" alt="Hacker News" width="26" height="26" /><br/>Hacker News</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=reddit.com" alt="Reddit" width="26" height="26" /><br/>Reddit</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=github.com" alt="GitHub" width="26" height="26" /><br/>GitHub Trending</td>
  </tr>
  <tr>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=openai.com" alt="OpenAI" width="26" height="26" /><br/>OpenAI Blog</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=blog.google" alt="Google AI Blog" width="26" height="26" /><br/>Google AI Blog</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=deepmind.google" alt="DeepMind" width="26" height="26" /><br/>DeepMind Blog</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=microsoft.com" alt="Microsoft Research" width="26" height="26" /><br/>Microsoft Research</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=blogs.nvidia.com" alt="NVIDIA" width="26" height="26" /><br/>NVIDIA Blog</td>
  </tr>
  <tr>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=bair.berkeley.edu" alt="BAIR" width="26" height="26" /><br/>BAIR Blog</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=theverge.com" alt="The Verge" width="26" height="26" /><br/>The Verge AI</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=techcrunch.com" alt="TechCrunch" width="26" height="26" /><br/>TechCrunch AI</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=venturebeat.com" alt="VentureBeat" width="26" height="26" /><br/>VentureBeat AI</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=technologyreview.com" alt="MIT Technology Review" width="26" height="26" /><br/>MIT Tech Review AI</td>
  </tr>
  <tr>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=aws.amazon.com" alt="AWS ML" width="26" height="26" /><br/>AWS ML Blog</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=cloud.google.com" alt="Google Cloud AI" width="26" height="26" /><br/>Google Cloud AI</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=blogs.microsoft.com" alt="Microsoft AI Blog" width="26" height="26" /><br/>Microsoft AI Blog</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=developer.nvidia.com" alt="NVIDIA Developer" width="26" height="26" /><br/>NVIDIA Developer AI</td>
    <td align="center"><img src="https://www.google.com/s2/favicons?sz=64&domain=news.mit.edu" alt="MIT CSAIL News" width="26" height="26" /><br/>MIT CSAIL News</td>
  </tr>
</table>

---

## Tech Stack (crafted for clarity & velocity)

<table align="center" style="border-collapse:separate;border-spacing:10px;">
  <tr>
    <td align="center" style="border:1px solid #e5e7eb;padding:10px 12px;"><img src="https://cdn.simpleicons.org/react/61DAFB" alt="React" width="26" height="26" /><br/>React</td>
    <td align="center" style="border:1px solid #e5e7eb;padding:10px 12px;"><img src="https://cdn.simpleicons.org/typescript/3178C6" alt="TypeScript" width="26" height="26" /><br/>TypeScript</td>
    <td align="center" style="border:1px solid #e5e7eb;padding:10px 12px;"><img src="https://cdn.simpleicons.org/vite/646CFF" alt="Vite" width="26" height="26" /><br/>Vite</td>
    <td align="center" style="border:1px solid #e5e7eb;padding:10px 12px;"><img src="https://cdn.simpleicons.org/tailwindcss/38B2AC" alt="Tailwind CSS" width="26" height="26" /><br/>Tailwind</td>
    <td align="center" style="border:1px solid #e5e7eb;padding:10px 12px;"><img src="https://cdn.simpleicons.org/python/3776AB" alt="Python" width="26" height="26" /><br/>Python</td>
  </tr>
  <tr>
    <td align="center" style="border:1px solid #e5e7eb;padding:10px 12px;"><img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/qwen.svg" alt="Qwen" width="26" height="26" /><br/>Qwen</td>
    <td align="center" style="border:1px solid #e5e7eb;padding:10px 12px;"><img src="https://www.google.com/s2/favicons?sz=64&domain=openai.com" alt="OpenAI" width="26" height="26" /><br/>OpenAI</td>
    <td align="center" style="border:1px solid #e5e7eb;padding:10px 12px;"><img src="https://cdn.simpleicons.org/githubactions/2088FF" alt="GitHub Actions" width="26" height="26" /><br/>GitHub Actions</td>
    <td align="center" style="border:1px solid #e5e7eb;padding:10px 12px;"><img src="https://cdn.simpleicons.org/vercel/000000" alt="Vercel" width="26" height="26" /><br/>Vercel</td>
    <td align="center" style="border:1px solid #e5e7eb;padding:10px 12px;"><img src="https://cdn.simpleicons.org/netlify/00C7B7" alt="Netlify" width="26" height="26" /><br/>Netlify</td>
  </tr>
</table>


## What it does (high level)

```text
Sources → Ingestion → L1 Heuristic → L2 AI Scoring → L3 Deep Refining → Output → Frontend
```

- **Output artifacts**
  - Frontend data: `src/data/tide-news.json`
  - (Optional, for archive): `public/reports/report_YYYY-MM-DD.json` + `public/history.json`

---

## Quickstart

### Frontend (dashboard)

```bash
cd Morning-Tide
npm install
npm run dev
```

Then open the dev server URL shown in your terminal.

### Pipeline (generate today’s report)

```bash
cd Morning-Tide
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -r pipeline/requirements.txt

# Set env vars (see env.example)
python -m pipeline.main
```

---

## Configuration

Copy `env.example` and fill in the keys you need:

- **Required for L2/L3 AI**: `DASHSCOPE_API_KEY` (Qwen via DashScope compatible endpoint)
- **Optional for audio**: `OPENAI_API_KEY`
- **Optional networking**: `AI_TIDES_USE_PROXY`, `AI_TIDES_VERIFY_SSL`

All knobs live in `pipeline/config.py`.

---

## Deploy (recommended)

### Option A: GitHub Pages + GitHub Actions (recommended)

- The site is deployed from GitHub Pages (static `dist/`).
- GitHub Actions runs the pipeline daily (07:00 Beijing time), commits updated data, and redeploys Pages.

#### Keep the public site running (owner)
1. In **your repo** → Settings → Secrets and variables → Actions → **New repository secret**
2. Add `DASHSCOPE_API_KEY` (this key is used only inside GitHub Actions and is not exposed to visitors).

#### Fork / local deploy (everyone else)
- **Fork**: set `DASHSCOPE_API_KEY` in your fork’s Secrets the same way.
- **Local**: copy `env.example` → `.env` and fill your own `DASHSCOPE_API_KEY`.

See `docs/deployment.md`.

---

## Project structure

```text
Morning-Tide/
  pipeline/                 # ingestion + filtering + output
  public/                   # static assets (and optional archived reports)
  src/                      # React frontend
  docs/                     # architecture & deployment notes
```


## Credits

Built by **@TidalHarley**. If you like this project, please consider giving it a ⭐
