import { useEffect, useMemo, useRef, useState } from "react";
import { ExternalLink, Calendar, User } from "lucide-react";
import { SummaryTooltip } from "./SummaryTooltip";
import { useLanguage } from "@/contexts/LanguageContext";

interface Paper {
  id?: string;
  arxivId?: string;
  title: string;
  tags?: string[];
  paperCategory?: string;
  signalReasons?: string[];
  impactScore?: number;
  score?: number;
  url?: string;
  source?: string;
  summary?: string;
  authors?: string | string[];
  publishedAt?: string | null;
}

interface PapersSectionProps {
  papers: Paper[];
}

const CATEGORY_COLORS: Record<string, string> = {
  "Deep Learning": "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
  "NLP": "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800",
  "Computer Vision": "bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800",
  "RLHF": "bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800",
  "AutoML": "bg-pink-100 text-pink-700 border-pink-200 dark:bg-pink-900/30 dark:text-pink-400 dark:border-pink-800",
  "Multimodal AI": "bg-cyan-100 text-cyan-700 border-cyan-200 dark:bg-cyan-900/30 dark:text-cyan-400 dark:border-cyan-800",
  "Explainability": "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800",
  "Robotics": "bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
  default: "bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700",
};

function getCategoryStyle(category: string): string {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS.default;
}

const CATEGORY_ORDER = ["General AI", "Computer Vision", "Robotics"];

function getPaperCategory(paper: Paper): string {
  const rawCategory = (paper.paperCategory || "").trim();
  if (rawCategory && CATEGORY_ORDER.includes(rawCategory)) {
    return rawCategory;
  }
  const tags = (paper.tags || []).map((tag) => tag.toLowerCase());
  if (tags.includes("robotics")) {
    return "Robotics";
  }
  return "General AI";
}

function formatDate(dateStr: string | null | undefined, language: "zh" | "en"): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return "";
  return date.toLocaleDateString(language === "zh" ? "zh-CN" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function getUrl(paper: Paper): string {
  if (paper.url) return paper.url;
  if (paper.arxivId) return `https://arxiv.org/abs/${paper.arxivId}`;
  return "#";
}

export function PapersSection({ papers }: PapersSectionProps) {
  const { language, t } = useLanguage();
  const sectionRef = useRef<HTMLElement>(null);
  const grouped = useMemo(() => {
    const groups: Record<string, Paper[]> = {};
    papers.forEach((paper) => {
      const category = getPaperCategory(paper);
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(paper);
    });
    return groups;
  }, [papers]);

  const availableCategories = CATEGORY_ORDER.filter((cat) => grouped[cat]?.length);
  const [activeCategory, setActiveCategory] = useState<string>(
    availableCategories[0] || "General AI"
  );

  useEffect(() => {
    if (availableCategories.length === 0) {
      setActiveCategory("General AI");
      return;
    }
    if (!availableCategories.includes(activeCategory)) {
      setActiveCategory(availableCategories[0]);
    }
  }, [availableCategories, activeCategory]);

  const displayPapers = (grouped[activeCategory] || []).slice(0, 6);

  // Handle card spotlight effect
  useEffect(() => {
    const section = sectionRef.current;
    if (!section) return;

    const cards = section.querySelectorAll(".card-spotlight");

    const handleMouseMove = (e: Event) => {
      const mouseEvent = e as MouseEvent;
      const card = mouseEvent.currentTarget as HTMLElement;
      const rect = card.getBoundingClientRect();
      const x = mouseEvent.clientX - rect.left;
      const y = mouseEvent.clientY - rect.top;
      card.style.setProperty("--spotlight-x", `${x}px`);
      card.style.setProperty("--spotlight-y", `${y}px`);
    };

    cards.forEach((card) => {
      card.addEventListener("mousemove", handleMouseMove);
    });

    return () => {
      cards.forEach((card) => {
        card.removeEventListener("mousemove", handleMouseMove);
      });
    };
  }, [papers]);

  if (displayPapers.length === 0) {
    return null;
  }

  return (
    <section id="papers" className="py-20 bg-secondary/30" ref={sectionRef}>
      <div className="container mx-auto px-4 md:px-6">
        {/* Section Header */}
        <div className="text-center mb-12 animate-fade-in-up">
          <h2 className="text-3xl md:text-4xl font-display font-semibold mb-4">
            {t.papersSection.featuredResearch}
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            {t.papersSection.featuredDesc}
          </p>
        </div>

        {/* Category Tabs */}
        {availableCategories.length > 0 && (
          <div className="flex flex-wrap items-center justify-center gap-2 mb-8">
            {availableCategories.map((category) => {
              const isActive = category === activeCategory;
              return (
                <button
                  key={category}
                  onClick={() => setActiveCategory(category)}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium border transition-colors ${
                    isActive
                      ? "bg-foreground text-background border-foreground"
                      : "bg-transparent text-foreground/70 border-border hover:text-foreground"
                  }`}
                >
                  {category}
                </button>
              );
            })}
          </div>
        )}

        {/* Papers Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayPapers.map((paper, index) => {
            const category = getPaperCategory(paper);
            const authors = Array.isArray(paper.authors) 
              ? paper.authors.join(", ") 
              : paper.authors || t.papersSection.researchTeam;
            const date = formatDate(paper.publishedAt, language);
            
            return (
              <div
                key={paper.id || `paper-${index}`}
                className="card-spotlight p-6 flex flex-col animate-fade-in-up"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <span className={`paper-card-tag ${getCategoryStyle(category)}`}>
                    {category}
                  </span>
                  <Calendar className="w-4 h-4 text-muted-foreground" />
                </div>

                {/* Title */}
                <h3 className="text-lg font-semibold leading-snug mb-3 line-clamp-2">
                  {paper.title}
                </h3>

                {/* Authors */}
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
                  <User className="w-4 h-4" />
                  <span className="line-clamp-1">{authors}</span>
                </div>

                {/* Summary */}
                {paper.summary && (
                  <SummaryTooltip text={paper.summary}>
                    <p className="text-sm text-muted-foreground leading-relaxed mb-4 flex-1 line-clamp-3">
                      {paper.summary}
                    </p>
                  </SummaryTooltip>
                )}

                {/* Footer */}
                <div className="flex items-center justify-between mt-auto pt-4 border-t border-border">
                  {date && (
                    <span className="text-sm text-muted-foreground">{date}</span>
                  )}
                  <a
                    href={getUrl(paper)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-sm text-primary font-medium hover:gap-3 transition-all ml-auto"
                  >
                    {t.papersSection.readPaper}
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              </div>
            );
          })}
        </div>

        {/* View All Link */}
        {papers.length > 6 && (
          <div className="text-center mt-10 animate-fade-in-up delay-600">
            <a
              href="#all-papers"
              className="btn-outline inline-flex items-center gap-2"
            >
              {t.papersSection.viewAllResearch}
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        )}
      </div>
    </section>
  );
}
