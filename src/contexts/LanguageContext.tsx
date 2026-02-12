import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from "react";

export type Language = "en" | "zh";

const STORAGE_KEY = "morning-tide-language";

const translations = {
  en: {
    header: {
      home: "Home",
      news: "News",
      papers: "Papers",
      about: "About",
      createdBy: "Created by @ TidalHarley",
      switchLight: "Switch to light mode",
      switchDark: "Switch to dark mode",
    },
    hero: {
      subtitle: "The AI morning brief - top news, key papers, and audio in minutes.",
      tagline: "Ride the tide. Start ahead.",
      viewNews: "View Today's News",
      latestResearch: "Latest Research",
      scroll: "Scroll",
    },
    sources: {
      title: "Trusted sources we scan daily",
      subtitle: "Official labs · arXiv · Hugging Face · RSS · HN · GitHub",
    },
    index: {
      viewArchive: "View archive:",
    },
    newsSection: {
      headlineNews: "Headline News",
      previousSlide: "Previous slide",
      nextSlide: "Next slide",
      newsImage: "News image",
      editorial: "Editorial",
      readFullArticle: "Read full article",
      dailyBriefing: "Daily Briefing",
      playAudioSummary: "Play Audio Summary",
      comingSoon: "Coming Soon",
      topStory: "Top Story",
      industryMovement: "Industry Movement",
      collapse: "Collapse",
      expandFullTranscription: "Expand Full Transcription",
      updatedDaily: "Updated daily at 7:00 AM EST",
      today: "Today",
      justNow: "Just now",
      yesterday: "Yesterday",
      hoursAgo: "h ago",
      daysAgo: "d ago",
    },
    papersSection: {
      featuredResearch: "Featured AI Research",
      featuredDesc:
        "Curated selection of the latest breakthroughs in artificial intelligence and machine learning",
      researchTeam: "Research Team",
      readPaper: "Read Paper",
      viewAllResearch: "View All Research",
    },
    audioDock: {
      dailyBriefing: "Daily Briefing",
      chapters: "Chapters",
      news: "News",
      releases: "Releases",
      papers: "Papers",
    },
    footer: {
      desc: "Your daily source for AI news, research, and insights. Updated every morning at 7:00 AM.",
      navigate: "Navigate",
      home: "Home",
      todaysNews: "Today's News",
      researchPapers: "Research Papers",
      audioBriefings: "Audio Briefings",
      stayUpdated: "Stay Updated",
      stayUpdatedDesc: "Get our daily digest delivered to your inbox.",
      rights: "All rights reserved.",
    },
    notFound: {
      title: "Oops! Page not found",
      backHome: "Return to Home",
    },
  },
  zh: {
    header: {
      home: "首页",
      news: "新闻",
      papers: "论文",
      about: "关于",
      createdBy: "由 @ TidalHarley 创建",
      switchLight: "切换为亮色",
      switchDark: "切换为暗色",
    },
    hero: {
      subtitle: "AI 晨报：几分钟掌握重点新闻、核心论文与音频速递。",
      tagline: "顺势而上，先人一步。",
      viewNews: "查看今日新闻",
      latestResearch: "最新研究",
      scroll: "下滑查看",
    },
    sources: {
      title: "我们每日扫描的可信来源",
      subtitle: "官方实验室 · arXiv · Hugging Face · RSS · HN · GitHub",
    },
    index: {
      viewArchive: "查看历史：",
    },
    newsSection: {
      headlineNews: "头条新闻",
      previousSlide: "上一条",
      nextSlide: "下一条",
      newsImage: "新闻配图",
      editorial: "编辑部",
      readFullArticle: "阅读原文",
      dailyBriefing: "每日简报",
      playAudioSummary: "播放音频摘要",
      comingSoon: "即将上线",
      topStory: "重点事件",
      industryMovement: "行业动态",
      collapse: "收起",
      expandFullTranscription: "展开完整转写",
      updatedDaily: "每日更新（美东时间 7:00）",
      today: "今天",
      justNow: "刚刚",
      yesterday: "昨天",
      hoursAgo: "小时前",
      daysAgo: "天前",
    },
    papersSection: {
      featuredResearch: "精选 AI 研究",
      featuredDesc: "精选人工智能与机器学习领域的最新突破",
      researchTeam: "研究团队",
      readPaper: "阅读论文",
      viewAllResearch: "查看全部研究",
    },
    audioDock: {
      dailyBriefing: "每日简报",
      chapters: "章节",
      news: "新闻",
      releases: "发布",
      papers: "论文",
    },
    footer: {
      desc: "你的 AI 每日信息源，覆盖新闻、研究与洞察。每天早上 7:00 更新。",
      navigate: "导航",
      home: "首页",
      todaysNews: "今日新闻",
      researchPapers: "研究论文",
      audioBriefings: "音频简报",
      stayUpdated: "保持更新",
      stayUpdatedDesc: "将每日摘要发送到你的邮箱。",
      rights: "保留所有权利。",
    },
    notFound: {
      title: "页面不存在",
      backHome: "返回首页",
    },
  },
} as const;

type Translations = (typeof translations)["en"];

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: Translations;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

function getInitialLanguage(): Language {
  if (typeof window === "undefined") return "zh";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "zh" || stored === "en") return stored;
  const browserLang = (navigator.language || "").toLowerCase();
  return browserLang.startsWith("zh") ? "zh" : "en";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(getInitialLanguage);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, language);
    }
    if (typeof document !== "undefined") {
      document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
    }
  }, [language]);

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      t: translations[language],
    }),
    [language]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
