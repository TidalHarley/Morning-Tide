import { useState, useEffect, useRef, useCallback } from "react";
import { ChevronLeft, ChevronRight, ExternalLink, Play, ChevronDown, ChevronUp } from "lucide-react";
import { InlineEmphasis } from "./InlineEmphasis";
import { SummaryTooltip } from "./SummaryTooltip";
import { useLanguage } from "@/contexts/LanguageContext";

interface NewsItem {
  id: string;
  title: string;
  summary?: string;
  source?: string;
  publishedAt?: string | null;
  url?: string;
  tags?: string[];
  imageUrl?: string;
  signalReasons?: string[];
}

interface NewsSectionProps {
  news: NewsItem[];
  onPlayAudio?: () => void;
  audioAvailable?: boolean;
}

const CATEGORY_COLORS: Record<string, string> = {
  "AI Research": "category-tag-red",
  "Machine Learning": "category-tag-blue",
  "Industry": "category-tag-purple",
  "Robotics": "category-tag-green",
  "NLP": "category-tag-orange",
  "Computer Vision": "category-tag-blue",
  default: "category-tag-gray",
};

const BASE_URL = import.meta.env.BASE_URL || "/";
const FALLBACK_IMAGE = `${BASE_URL}placeholder.svg`;
const PLACEHOLDER_IMAGES = [FALLBACK_IMAGE];

function resolveImageSrc(rawUrl?: string): string {
  const value = (rawUrl || "").trim();
  if (!value) return FALLBACK_IMAGE;
  if (value.startsWith("data:") || value.startsWith("javascript:")) return FALLBACK_IMAGE;
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  if (value.startsWith("/")) return `${BASE_URL}${value.replace(/^\/+/, "")}`;
  return FALLBACK_IMAGE;
}

function getTimeAgo(
  publishedAt: string | null | undefined,
  labels: {
    today: string;
    justNow: string;
    yesterday: string;
    hoursAgo: string;
    daysAgo: string;
  }
): string {
  if (!publishedAt) return labels.today;
  const date = new Date(publishedAt);
  if (isNaN(date.getTime())) return labels.today;
  
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  
  if (diffHours < 1) return labels.justNow;
  if (diffHours < 24) return `${diffHours}${labels.hoursAgo}`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return labels.yesterday;
  return `${diffDays}${labels.daysAgo}`;
}

function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS.default;
}

export function NewsSection({ news, onPlayAudio, audioAvailable = true }: NewsSectionProps) {
  const { t } = useLanguage();
  const [activeIndex, setActiveIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [briefingExpanded, setBriefingExpanded] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);
  
  // Headline carousel should be concise: only show top 2.
  const displayNews = news.slice(0, 2);

  const goToSlide = useCallback((index: number) => {
    if (isAnimating) return;
    setIsAnimating(true);
    setActiveIndex(index);
    setTimeout(() => setIsAnimating(false), 500);
  }, [isAnimating]);

  const nextSlide = useCallback(() => {
    if (displayNews.length <= 1) return;
    goToSlide((activeIndex + 1) % displayNews.length);
  }, [activeIndex, displayNews.length, goToSlide]);

  const prevSlide = useCallback(() => {
    if (displayNews.length <= 1) return;
    goToSlide((activeIndex - 1 + displayNews.length) % displayNews.length);
  }, [activeIndex, displayNews.length, goToSlide]);

  // Auto-advance carousel
  useEffect(() => {
    if (displayNews.length <= 1) return;
    const interval = setInterval(nextSlide, 8000);
    return () => clearInterval(interval);
  }, [displayNews.length, nextSlide]);

  // If the list length changes (e.g. from 5->2), clamp activeIndex.
  useEffect(() => {
    if (activeIndex >= displayNews.length && displayNews.length > 0) {
      setActiveIndex(0);
    }
  }, [activeIndex, displayNews.length]);

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
  }, [news]);

  if (news.length === 0) {
    return null;
  }

  const currentNews = displayNews[activeIndex];
  const category = currentNews?.tags?.[0] || currentNews?.source || "AI Research";
  const imageUrl = resolveImageSrc(
    currentNews?.imageUrl || PLACEHOLDER_IMAGES[activeIndex % PLACEHOLDER_IMAGES.length]
  );

  return (
    <section id="news" className="py-16 bg-background" ref={sectionRef}>
      <div className="container mx-auto px-4 md:px-6">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Content - 2 columns */}
          <div className="lg:col-span-2">
            {/* Section Header */}
            <div className="flex items-center justify-between mb-8 animate-fade-in-up">
              <h2 className="text-2xl md:text-3xl font-display font-semibold">
                {t.newsSection.headlineNews}
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={prevSlide}
                  disabled={displayNews.length <= 1}
                  className="w-10 h-10 rounded-full border border-border flex items-center justify-center hover:bg-secondary transition-colors"
                  aria-label={t.newsSection.previousSlide}
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button
                  onClick={nextSlide}
                  disabled={displayNews.length <= 1}
                  className="w-10 h-10 rounded-full border border-border flex items-center justify-center hover:bg-secondary transition-colors"
                  aria-label={t.newsSection.nextSlide}
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Main Carousel Card */}
            <div className="card-spotlight rounded-2xl overflow-visible animate-fade-in-up delay-100">
              {/* Image */}
              <div className="news-card-image relative">
                <img
                  src={imageUrl}
                  alt={currentNews?.title || t.newsSection.newsImage}
                  className="w-full h-full object-cover object-center bg-muted"
                  onError={(e) => {
                    const currentSrc = e.currentTarget.getAttribute("src") || "";
                    if (!currentSrc.endsWith("placeholder.svg")) {
                      e.currentTarget.src = FALLBACK_IMAGE;
                    }
                  }}
                />
                <div className="absolute top-4 left-4">
                  <span className={`category-tag ${getCategoryColor(category)}`}>
                    {category}
                  </span>
                </div>
              </div>

              {/* Content */}
              <div className="p-6">
                <div className="flex items-center gap-3 text-sm text-muted-foreground mb-3">
                  <span className="font-medium">{currentNews?.source || t.newsSection.editorial}</span>
                  <span className="text-border">•</span>
                  <span>
                    {getTimeAgo(currentNews?.publishedAt, {
                      today: t.newsSection.today,
                      justNow: t.newsSection.justNow,
                      yesterday: t.newsSection.yesterday,
                      hoursAgo: t.newsSection.hoursAgo,
                      daysAgo: t.newsSection.daysAgo,
                    })}
                  </span>
                </div>

                <h3 className="text-xl md:text-2xl font-semibold leading-tight mb-4">
                  {currentNews?.title}
                </h3>

                {currentNews?.summary && (
                  <SummaryTooltip text={currentNews.summary}>
                    <p className="text-muted-foreground leading-relaxed mb-4 line-clamp-2">
                      <InlineEmphasis text={currentNews.summary} />
                    </p>
                  </SummaryTooltip>
                )}

                <a
                  href={currentNews?.url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-primary font-medium hover:gap-3 transition-all"
                >
                  {t.newsSection.readFullArticle}
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </div>

            {/* Carousel Dots */}
            <div className="flex items-center justify-center gap-2 mt-6">
              {displayNews.map((_, index) => (
                <button
                  key={index}
                  onClick={() => goToSlide(index)}
                  className={`carousel-dot ${index === activeIndex ? "active" : ""}`}
                  aria-label={`Go to slide ${index + 1}`}
                />
              ))}
            </div>
          </div>

          {/* Sidebar - Daily Briefing */}
          <div className="lg:col-span-1">
            <div className="briefing-card animate-slide-in-right delay-200 sticky top-24">
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold">{t.newsSection.dailyBriefing}</h3>
                <span className="text-sm text-muted-foreground">15 min</span>
              </div>

              {/* Audio Player Button */}
              <button
                onClick={audioAvailable ? onPlayAudio : undefined}
                disabled={!audioAvailable}
                className={`audio-play-btn mb-6 group ${audioAvailable ? "" : "opacity-50 cursor-not-allowed"}`}
              >
                <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center group-hover:bg-white/30 transition-colors">
                  <Play className="w-5 h-5 fill-current ml-0.5" />
                </div>
                <span>{audioAvailable ? t.newsSection.playAudioSummary : t.newsSection.comingSoon}</span>
              </button>

              {/* Top Story */}
              {news[0] && (
                <div className="mb-5">
                  <h4 className="text-sm font-semibold mb-2">{t.newsSection.topStory}</h4>
                  <SummaryTooltip text={news[0].summary || news[0].title} tooltipClassName="summary-tooltip-compact">
                    <p className="text-sm text-muted-foreground leading-relaxed line-clamp-4">
                      {news[0].summary || news[0].title}
                    </p>
                  </SummaryTooltip>
                </div>
              )}

              {/* Industry Movement */}
              {news[1] && (
                <div className="mb-5">
                  <h4 className="text-sm font-semibold mb-2">{t.newsSection.industryMovement}</h4>
                  <SummaryTooltip text={news[1].summary || news[1].title} tooltipClassName="summary-tooltip-compact">
                    <p className="text-sm text-muted-foreground leading-relaxed line-clamp-4">
                      {news[1].summary || news[1].title}
                    </p>
                  </SummaryTooltip>
                </div>
              )}

              {/* Expand/Collapse */}
              <button
                onClick={() => setBriefingExpanded(!briefingExpanded)}
                className="flex items-center gap-2 text-sm text-primary font-medium hover:gap-3 transition-all w-full justify-center"
              >
                <span>
                  {briefingExpanded
                    ? t.newsSection.collapse
                    : t.newsSection.expandFullTranscription}
                </span>
                {briefingExpanded ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </button>

              {/* Expanded Content */}
              {briefingExpanded && (
                <div className="mt-6 pt-6 border-t border-border">
                  <div className="space-y-4">
                    {news.slice(2, 6).map((item, index) => (
                      <div key={item.id} className="animate-fade-in-up" style={{ animationDelay: `${index * 100}ms` }}>
                        <h5 className="text-sm font-medium mb-1 line-clamp-2">{item.title}</h5>
                        {item.summary && (
                          <SummaryTooltip text={item.summary} tooltipClassName="summary-tooltip-compact">
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {item.summary}
                            </p>
                          </SummaryTooltip>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Footer */}
              <div className="mt-6 pt-4 border-t border-border">
                <p className="text-xs text-muted-foreground text-center">
                  {t.newsSection.updatedDaily}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Secondary News Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mt-12">
          {/* Everything beyond the top-2 headlines should be shown here */}
          {news.slice(2).map((item, index) => {
            const itemCategory = item.tags?.[0] || item.source || "News";
            const itemImage = resolveImageSrc(
              item.imageUrl || PLACEHOLDER_IMAGES[(index + 2) % PLACEHOLDER_IMAGES.length]
            );
            
            return (
              <a
                key={item.id}
                href={item.url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="card-spotlight group block overflow-visible animate-fade-in-up"
                style={{ animationDelay: `${(index + 3) * 100}ms` }}
              >
                <div className="news-card-image relative">
                  <img
                    src={itemImage}
                    alt={item.title}
                    className="w-full h-full object-cover object-center bg-muted"
                    onError={(e) => {
                      const currentSrc = e.currentTarget.getAttribute("src") || "";
                      if (!currentSrc.endsWith("placeholder.svg")) {
                        e.currentTarget.src = FALLBACK_IMAGE;
                      }
                    }}
                  />
                  <div className="absolute top-3 left-3">
                    <span className={`category-tag text-[10px] ${getCategoryColor(itemCategory)}`}>
                      {itemCategory}
                    </span>
                  </div>
                </div>
                <div className="p-4">
                  <h4 className="font-semibold leading-snug group-hover:text-primary transition-colors line-clamp-2">
                    {item.title}
                  </h4>
                  {item.summary && (
                    <SummaryTooltip text={item.summary} tooltipClassName="summary-tooltip-compact">
                      <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                        <InlineEmphasis text={item.summary} />
                      </p>
                    </SummaryTooltip>
                  )}
                </div>
              </a>
            );
          })}
        </div>
      </div>
    </section>
  );
}
