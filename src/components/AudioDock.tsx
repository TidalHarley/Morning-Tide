import { motion, AnimatePresence } from "framer-motion";
import { Play, Pause, ChevronUp, ChevronDown } from "lucide-react";
import { useState } from "react";
import { useLanguage } from "@/contexts/LanguageContext";

interface Chapter {
  title: string;
  timestamp: string;
}

interface AudioDockProps {
  isVisible: boolean;
  isPlaying: boolean;
  onPlayPause: () => void;
  isEnabled?: boolean;
  title?: string;
  duration?: string;
  progress?: number;
  chapters?: Chapter[];
}

export function AudioDock({
  isVisible,
  isPlaying,
  onPlayPause,
  isEnabled = true,
  title,
  duration = "07:32",
  progress = 0,
  chapters,
}: AudioDockProps) {
  const { t } = useLanguage();
  const [isExpanded, setIsExpanded] = useState(false);
  const defaultTitle = t.audioDock.dailyBriefing;
  const effectiveTitle = title || defaultTitle;
  const effectiveChapters =
    chapters && chapters.length > 0
      ? chapters
      : [
          { title: t.audioDock.news, timestamp: "00:00" },
          { title: t.audioDock.releases, timestamp: "02:45" },
          { title: t.audioDock.papers, timestamp: "05:20" },
        ];

  // Generate waveform bars
  const waveformBars = Array.from({ length: 20 }, (_, i) => ({
    height: Math.random() * 0.7 + 0.3,
    delay: i * 0.05,
  }));

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ y: 100, opacity: 0, x: "-50%" }}
          animate={{ y: 0, opacity: 1, x: "-50%" }}
          exit={{ y: 100, opacity: 0, x: "-50%" }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="fixed bottom-6 left-1/2 z-50"
        >
          <div className="glass-dock rounded-2xl shadow-lg">
            {/* Expanded Chapters Panel */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="border-b border-foreground/[0.06] px-5 py-3"
                >
                  <div className="font-mono text-[10px] uppercase tracking-wider text-muted-40 mb-2">
                    {t.audioDock.chapters}
                  </div>
                  <div className="space-y-1.5">
                    {effectiveChapters.map((chapter, index) => (
                      <button
                        key={index}
                        className="flex w-full items-center justify-between text-sm transition-colors hover:text-foreground"
                      >
                        <span className="text-muted-60">{chapter.title}</span>
                        <span className="font-mono text-xs tabular-nums text-muted-40">
                          {chapter.timestamp}
                        </span>
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Main Dock Content */}
            <div className="flex items-center gap-4 px-5 py-3">
              {/* Play/Pause Button */}
              <motion.button
                onClick={isEnabled ? onPlayPause : undefined}
                disabled={!isEnabled}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`flex h-9 w-9 items-center justify-center rounded-full bg-foreground/[0.06] transition-colors hover:bg-foreground/[0.1] ${
                  isEnabled ? "" : "opacity-40 cursor-not-allowed"
                }`}
              >
                {isPlaying ? (
                  <Pause className="h-4 w-4 text-foreground/70" fill="currentColor" />
                ) : (
                  <Play className="h-4 w-4 ml-0.5 text-foreground/70" fill="currentColor" />
                )}
              </motion.button>

              {/* Waveform Visualizer */}
              <div className="flex h-6 items-center gap-[2px]">
                {waveformBars.map((bar, i) => (
                  <motion.div
                    key={i}
                    className="waveform-bar"
                    style={{ height: "100%" }}
                    animate={
                      isPlaying
                        ? {
                            scaleY: [0.3, bar.height, 0.3],
                          }
                        : { scaleY: 0.3 }
                    }
                    transition={{
                      duration: 0.8,
                      repeat: Infinity,
                      delay: bar.delay,
                      ease: "easeInOut",
                    }}
                  />
                ))}
              </div>

              {/* Title & Duration */}
              <div className="flex flex-col">
                <span className="text-sm font-medium text-foreground/80">{effectiveTitle}</span>
                <span className="font-mono text-xs tabular-nums text-muted-40">{duration}</span>
              </div>

              {/* Progress Bar */}
              <div className="hidden w-32 sm:block">
                <div className="audio-progress">
                  <motion.div
                    className="audio-progress-fill"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>

              {/* Expand/Collapse Toggle */}
              <motion.button
                onClick={() => setIsExpanded(!isExpanded)}
                whileHover={{ scale: 1.1 }}
                className="ml-2 flex h-6 w-6 items-center justify-center rounded-full text-muted-40 transition-colors hover:text-foreground/60"
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronUp className="h-4 w-4" />
                )}
              </motion.button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
