import { useEffect, useRef } from "react";
import { ChevronRight } from "lucide-react";

interface TideHeroProps {
  onViewNews?: () => void;
  onViewPapers?: () => void;
}

export function TideHero({ onViewNews, onViewPapers }: TideHeroProps) {
  const heroRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const hero = heroRef.current;
    if (!hero) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = hero.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width - 0.5) * 20;
      const y = ((e.clientY - rect.top) / rect.height - 0.5) * 20;
      hero.style.setProperty("--parallax-x", `${x}px`);
      hero.style.setProperty("--parallax-y", `${y}px`);
    };

    hero.addEventListener("mousemove", handleMouseMove);
    return () => hero.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <section
      ref={heroRef}
      className="hero-section relative min-h-screen flex flex-col overflow-hidden"
      style={{ "--parallax-x": "0px", "--parallax-y": "0px" } as React.CSSProperties}
    >
      {/* Background Image with Parallax */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat transform transition-transform duration-100"
        style={{
          backgroundImage: `
            linear-gradient(
              to bottom,
              rgba(0, 0, 0, 0.2) 0%,
              rgba(0, 0, 0, 0.3) 40%,
              rgba(0, 0, 0, 0.6) 100%
            ),
            url('https://images.unsplash.com/photo-1741320096907-ce0189840469?auto=format&fit=crop&w=2070&q=80')
          `,
          transform: "translate(var(--parallax-x), var(--parallax-y)) scale(1.05)",
        }}
      />

      {/* Content */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 text-center pt-32 md:pt-44">
        {/* Main Title */}
        <h1 className="animate-blur-in mb-6 mt-8">
          <span className="block font-brush text-6xl sm:text-7xl md:text-8xl lg:text-9xl font-bold tracking-tight hero-title hero-title-art">
            Morning
          </span>
          <span className="block font-brush text-6xl sm:text-7xl md:text-8xl lg:text-9xl font-bold tracking-tight hero-title hero-title-art -mt-2 md:-mt-4">
            Tide
          </span>
        </h1>

        {/* Subtitle */}
        <p className="animate-fade-in-up delay-200 max-w-2xl text-lg sm:text-xl md:text-2xl text-white/90 font-light mb-4">
          The AI morning brief—top news, key papers, and audio in minutes.
        </p>

        {/* Tagline */}
        <p className="animate-fade-in-up delay-300 text-base sm:text-lg text-white/70 mb-10">
          Ride the tide. Start ahead.
        </p>

        {/* CTA Buttons */}
        <div className="animate-fade-in-up delay-400 flex flex-col sm:flex-row items-center gap-4">
          <button
            onClick={onViewNews}
            className="btn-outline flex items-center gap-2 group"
          >
            <span>View Today&apos;s News</span>
            <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </button>
          <button
            onClick={onViewPapers}
            className="btn-primary"
          >
            Latest Research
          </button>
        </div>
      </div>

      {/* Scroll Indicator */}
      <div className="animate-fade-in-up delay-600 absolute bottom-8 left-1/2 -translate-x-1/2">
        <div className="flex flex-col items-center gap-2 text-white/50">
          <span className="text-xs uppercase tracking-widest">Scroll</span>
          <div className="w-6 h-10 rounded-full border-2 border-white/30 flex justify-center pt-2">
            <div className="w-1 h-2 bg-white/50 rounded-full animate-bounce" />
          </div>
        </div>
      </div>
    </section>
  );
}
