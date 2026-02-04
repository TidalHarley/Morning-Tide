import { useState, useEffect } from "react";
import { Sunrise, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

interface TideHeaderProps {
  variant?: "hero" | "light";
}

export function TideHeader({ variant = "hero" }: TideHeaderProps) {
  const [scrolled, setScrolled] = useState(false);
  const { theme, setTheme, resolvedTheme } = useTheme();
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
                Created by @ TidalHarley
              </span>
            </div>
          </a>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            {["Home", "News", "Papers", "About"].map((item) => (
              <a
                key={item}
                href={item === "Home" ? "/" : `#${item.toLowerCase()}`}
                className={`nav-link ${
                  showBackground ? "nav-link-light" : "nav-link-hero"
                }`}
              >
                {item}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setTheme(isDark ? "light" : "dark")}
              className={`p-2 rounded-lg transition-colors ${
                showBackground
                  ? "text-foreground hover:bg-secondary"
                  : "text-white hover:bg-white/10"
              }`}
              aria-label={isDark ? "切换为亮色" : "切换为暗色"}
              title={isDark ? "切换为亮色" : "切换为暗色"}
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
