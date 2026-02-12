import { useState, useEffect } from "react";
import { Sunrise, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useLanguage } from "@/contexts/LanguageContext";

interface TideHeaderProps {
  variant?: "hero" | "light";
}

export function TideHeader({ variant = "hero" }: TideHeaderProps) {
  const [scrolled, setScrolled] = useState(false);
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { language, setLanguage, t } = useLanguage();
  const isDark = (resolvedTheme || theme) === "dark";

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const isHero = variant === "hero";
  const showBackground = !isHero || scrolled;

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        showBackground
          ? "bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl shadow-sm"
          : "bg-transparent"
      }`}
    >
      <div className="container mx-auto px-4 md:px-6">
        <div className="flex items-center justify-between h-16 md:h-20">
          {/* Logo */}
          <a href="/" className="flex items-center gap-3 group">
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${
                showBackground
                  ? "bg-gradient-to-br from-sky-400 to-blue-500"
                  : "bg-white/20 backdrop-blur-sm"
              }`}
            >
              <Sunrise className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-col">
              <span
                className={`font-brush text-2xl font-normal tracking-tight transition-colors ${
                  showBackground ? "text-foreground" : "text-white"
                }`}
              >
                Morning Tide
              </span>
              <span
                className={`text-[10px] font-medium tracking-wider uppercase transition-colors ${
                  showBackground ? "text-muted-foreground" : "text-white/70"
                }`}
              >
                {t.header.createdBy}
              </span>
            </div>
          </a>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            {[
              { id: "home", label: t.header.home },
              { id: "news", label: t.header.news },
              { id: "papers", label: t.header.papers },
              { id: "about", label: t.header.about },
            ].map((item) => (
              <a
                key={item.id}
                href={item.id === "home" ? "/" : `#${item.id}`}
                className={`nav-link ${
                  showBackground ? "nav-link-light" : "nav-link-hero"
                }`}
              >
                {item.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <div
              className={`hidden md:flex items-center rounded-lg border px-1 py-1 ${
                showBackground ? "border-border" : "border-white/30"
              }`}
            >
              <button
                type="button"
                onClick={() => setLanguage("zh")}
                className={`px-2 py-1 text-xs rounded ${
                  language === "zh"
                    ? showBackground
                      ? "bg-secondary text-foreground"
                      : "bg-white/20 text-white"
                    : showBackground
                    ? "text-muted-foreground hover:text-foreground"
                    : "text-white/70 hover:text-white"
                }`}
              >
                中文
              </button>
              <button
                type="button"
                onClick={() => setLanguage("en")}
                className={`px-2 py-1 text-xs rounded ${
                  language === "en"
                    ? showBackground
                      ? "bg-secondary text-foreground"
                      : "bg-white/20 text-white"
                    : showBackground
                    ? "text-muted-foreground hover:text-foreground"
                    : "text-white/70 hover:text-white"
                }`}
              >
                EN
              </button>
            </div>
            <button
              type="button"
              onClick={() => setTheme(isDark ? "light" : "dark")}
              className={`p-2 rounded-lg transition-colors ${
                showBackground
                  ? "text-foreground hover:bg-secondary"
                  : "text-white hover:bg-white/10"
              }`}
              aria-label={isDark ? t.header.switchLight : t.header.switchDark}
              title={isDark ? t.header.switchLight : t.header.switchDark}
            >
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            {/* Mobile Menu Button */}
            <button
              className={`md:hidden p-2 rounded-lg transition-colors ${
                showBackground
                  ? "text-foreground hover:bg-secondary"
                  : "text-white hover:bg-white/10"
              }`}
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
