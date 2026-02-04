import { useState, useEffect, useMemo, useRef } from "react";
import { TideHeader } from "@/components/TideHeader";
import { TideHero } from "@/components/TideHero";
import { SourcesMarquee } from "@/components/SourcesMarquee";
import { NewsSection } from "@/components/NewsSection";
import { PapersSection } from "@/components/PapersSection";
import { TideFooter } from "@/components/TideFooter";
import { AudioDock } from "@/components/AudioDock";
import tideData from "@/data/tide-news.json";

type PipelineItem = {
  id: string;
  title: string;
  url?: string;
  summary?: string;
  tags?: string[];
  source?: string;
  publishedAt?: string | null;
  authors?: string | string[];
  paperCategory?: string;
  signalReasons?: string[];
};

type TideData = {
  meta?: { tideState?: "rising" | "calm" };
  papers?: PipelineItem[];
  news?: PipelineItem[];
  audioUrl?: string;
};

const Index = () => {
  const [audioVisible, setAudioVisible] = useState(false);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [audioProgress, setAudioProgress] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [reportData, setReportData] = useState<TideData | null>(null);
  
  const newsRef = useRef<HTMLDivElement>(null);
  const papersRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const data = (reportData ?? (tideData as TideData)) as TideData;
  const pipelinePapers = useMemo(() => data.papers || [], [data.papers]);
  const pipelineNews = useMemo(() => data.news || [], [data.news]);
  const audioUrl = (data as { audioUrl?: string }).audioUrl || "";

  // Load history
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const response = await fetch("/history.json");
        if (!response.ok) return;
        const history = (await response.json()) as { date: string }[];
        const dates = history.map((item) => item.date);
        setAvailableDates(dates);
        if (dates.length > 0) {
          setSelectedDate((prev) => prev || dates[0]);
        }
      } catch {
        // ignore history load errors
      }
    };
    loadHistory();
  }, []);

  // Load report for selected date
  useEffect(() => {
    if (!selectedDate) return;
    const loadReport = async () => {
      try {
        const response = await fetch(`/reports/report_${selectedDate}.json`);
        if (!response.ok) return;
        const report = (await response.json()) as TideData;
        setReportData(report);
      } catch {
        // ignore report load errors
      }
    };
    loadReport();
  }, [selectedDate]);

  // Audio player setup
  useEffect(() => {
    if (!audioUrl) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setAudioPlaying(false);
      setAudioProgress(0);
      setAudioDuration(0);
      return;
    }

    const audio = audioRef.current ?? new Audio(audioUrl);
    if (audio.src !== audioUrl) {
      audio.src = audioUrl;
    }
    audioRef.current = audio;

    const handleLoaded = () => {
      const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
      setAudioDuration(duration);
    };
    const handleTimeUpdate = () => {
      if (!audio.duration || !Number.isFinite(audio.duration)) {
        setAudioProgress(0);
        return;
      }
      setAudioProgress((audio.currentTime / audio.duration) * 100);
    };
    const handlePlay = () => setAudioPlaying(true);
    const handlePause = () => setAudioPlaying(false);
    const handleEnded = () => {
      setAudioPlaying(false);
      setAudioProgress(0);
    };
    const handleError = () => {
      setAudioPlaying(false);
      setAudioProgress(0);
    };

    audio.addEventListener("loadedmetadata", handleLoaded);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("play", handlePlay);
    audio.addEventListener("pause", handlePause);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("error", handleError);

    return () => {
      audio.removeEventListener("loadedmetadata", handleLoaded);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("pause", handlePause);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("error", handleError);
    };
  }, [audioUrl]);

  // Scroll animation observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
          }
        });
      },
      {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px",
      }
    );

    document.querySelectorAll(".scroll-animate").forEach((el) => {
      observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  const handlePlayAudio = () => {
    setAudioVisible(true);
    if (!audioRef.current || !audioUrl) return;
    audioRef.current
      .play()
      .then(() => setAudioPlaying(true))
      .catch(() => setAudioPlaying(false));
  };

  const handlePlayPause = () => {
    if (!audioRef.current || !audioUrl) return;
    if (audioRef.current.paused) {
      audioRef.current.play().catch(() => {
        setAudioPlaying(false);
      });
    } else {
      audioRef.current.pause();
    }
  };

  const formatDuration = (seconds: number) => {
    if (!seconds || !Number.isFinite(seconds)) return "00:00";
    const minutes = Math.floor(seconds / 60);
    const remaining = Math.floor(seconds % 60);
    return `${minutes.toString().padStart(2, "0")}:${remaining
      .toString()
      .padStart(2, "0")}`;
  };

  const scrollToNews = () => {
    newsRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const scrollToPapers = () => {
    papersRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="relative min-h-screen bg-background text-foreground">
      {/* Fixed Header */}
      <TideHeader variant="hero" />

      {/* Hero Section */}
      <TideHero onViewNews={scrollToNews} onViewPapers={scrollToPapers} />

      {/* Trusted Sources Marquee */}
      <SourcesMarquee />

      {/* Date Selector (if available) */}
      {availableDates.length > 1 && (
        <div className="bg-background border-b border-border sticky top-16 md:top-20 z-40">
          <div className="container mx-auto px-4 md:px-6 py-3">
            <div className="flex items-center justify-end gap-3">
              <span className="text-sm text-muted-foreground">View archive:</span>
              <select
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="rounded-lg border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                {availableDates.map((date) => (
                  <option key={date} value={date}>
                    {date}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* News Section */}
      <div ref={newsRef}>
        <NewsSection
          news={pipelineNews}
          onPlayAudio={handlePlayAudio}
          audioAvailable={Boolean(audioUrl)}
        />
      </div>

      {/* Papers Section */}
      <div ref={papersRef}>
        <PapersSection papers={pipelinePapers} />
      </div>

      {/* Footer */}
      <TideFooter />

      {/* Audio Dock */}
      <AudioDock
        isVisible={audioVisible}
        isPlaying={audioPlaying}
        onPlayPause={handlePlayPause}
        progress={audioProgress}
        duration={formatDuration(audioDuration)}
        isEnabled={Boolean(audioUrl)}
      />
    </div>
  );
};

export default Index;
