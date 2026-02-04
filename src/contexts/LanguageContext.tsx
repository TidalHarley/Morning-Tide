import { createContext, useContext, useState, ReactNode } from "react";

type Language = "en" | "zh";

interface Translations {
  purpose: string;
  purposeStatement: string;
  signal: string;
  over: string;
  noise: string;
  updated: string;
  motion: string;
  on: string;
  off: string;
  tideState: string;
  rising: string;
  calm: string;
  heroLine1: string;
  heroLine2: string;
  heroSubline: string;
  listen: string;
  dailyBriefing: string;
  curated: string;
  todayInPapers: string;
  read: string;
  watch: string;
  perspective: string;
  signalOverNoise: string;
  builtBy: string;
  chapters: string;
  news: string;
  releases: string;
  papers: string;
}

const translations: Record<Language, Translations> = {
  en: {
    purpose: "PURPOSE",
    purposeStatement: "Map the tides of AI.",
    signal: "Signal",
    over: "over",
    noise: "noise",
    updated: "Updated",
    motion: "Motion",
    on: "On",
    off: "Off",
    tideState: "TIDE STATE",
    rising: "RISING",
    calm: "CALM",
    heroLine1: "Map the",
    heroLine2: "of AI.",
    heroSubline: "Curated intelligence on models, research, and industry moves.",
    listen: "Listen",
    dailyBriefing: "Daily Briefing",
    curated: "CURATED",
    todayInPapers: "Today in Papers",
    read: "Read",
    watch: "Watch",
    perspective: "PERSPECTIVE",
    signalOverNoise: "Signal over noise",
    builtBy: "Built by",
    chapters: "Chapters",
    news: "News",
    releases: "Releases",
    papers: "Papers",
  },
  zh: {
    purpose: "愿景",
    purposeStatement: "做易懂易用有影响力的AI Agent",
    signal: "",
    over: "",
    noise: "",
    updated: "数据更新于",
    motion: "动效效果",
    on: "开启",
    off: "关闭",
    tideState: "当前态势",
    rising: "风起云涌",
    calm: "蓄势待发",
    heroLine1: "洞悉 AI",
    heroLine2: "变局",
    heroSubline: "汇聚全球AI研究与产业动态, 提供易懂的新闻、论文解析",
    listen: "聆听",
    dailyBriefing: "每日速递",
    curated: "精选",
    todayInPapers: "今日论文",
    read: "阅读",
    watch: "观看",
    perspective: "深度视角",
    signalOverNoise: "大浪淘沙",
    builtBy: "出品",
    chapters: "章节",
    news: "咨询",
    releases: "新发布",
    papers: "论文",
  },
};

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: Translations;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>("en");

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage,
        t: translations[language],
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
