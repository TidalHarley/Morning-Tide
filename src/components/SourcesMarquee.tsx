import { useLanguage } from "@/contexts/LanguageContext";

type SourceItem = {
  name: string;
  domain: string;
  iconUrl?: string;
};

const SOURCES: SourceItem[] = [
  { name: "OpenAI", domain: "openai.com" },
  { name: "Google AI Blog", domain: "blog.google" },
  { name: "DeepMind", domain: "deepmind.google" },
  { name: "Microsoft Research", domain: "microsoft.com" },
  { name: "NVIDIA Blog", domain: "blogs.nvidia.com" },
  { name: "BAIR", domain: "bair.berkeley.edu" },
  { name: "The Verge AI", domain: "theverge.com" },
  { name: "TechCrunch AI", domain: "techcrunch.com" },
  { name: "VentureBeat AI", domain: "venturebeat.com" },
  { name: "Hugging Face Blog", domain: "huggingface.co" },
  { name: "MIT Tech Review", domain: "technologyreview.com" },
  { name: "AWS ML Blog", domain: "aws.amazon.com" },
  { name: "Google Cloud AI", domain: "cloud.google.com" },
  { name: "Microsoft AI Blog", domain: "blogs.microsoft.com" },
  { name: "NVIDIA Developer", domain: "developer.nvidia.com" },
  { name: "MIT CSAIL News", domain: "news.mit.edu" },
  { name: "Hacker News", domain: "news.ycombinator.com" },
  { name: "Reddit", domain: "reddit.com" },
  { name: "GitHub Trending", domain: "github.com" },
  { name: "arXiv", domain: "arxiv.org" },
  { name: "Hugging Face Daily Papers", domain: "huggingface.co" },
  { name: "Tencent AI Lab", domain: "tencentailab.com" },
  { name: "Baidu Research", domain: "research.baidu.com" },
  {
    name: "Alibaba DAMO",
    domain: "damo.alibaba.com",
    iconUrl: "https://avatars.githubusercontent.com/u/115537614?s=200&v=4",
  },
  {
    name: "Huawei Noah's Ark",
    domain: "noahlab.ai",
    iconUrl: "https://avatars.githubusercontent.com/u/12619994?s=200&v=4",
  },
  { name: "PaddlePaddle", domain: "paddlepaddle.org" },
  {
    name: "OpenGVLab",
    domain: "opengvlab.shlab.org.cn",
    iconUrl: "https://avatars.githubusercontent.com/u/94522163?s=200&v=4",
  },
];

const LOGO_SIZE = 36;
const FALLBACK_ICON = "placeholder.svg";

export function SourcesMarquee() {
  const { t } = useLanguage();
  const loop = [...SOURCES, ...SOURCES];

  return (
    <section className="sources-marquee-section">
      <div className="sources-marquee-header">
        <span className="sources-marquee-title">{t.sources.title}</span>
        <span className="sources-marquee-subtitle">{t.sources.subtitle}</span>
      </div>
      <div className="sources-marquee">
        <div className="sources-marquee-track">
          {loop.map((source, index) => (
            <div key={`${source.name}-${index}`} className="sources-marquee-item">
              <div className="sources-marquee-icon">
                <img
                  src={
                    source.iconUrl ||
                    `https://www.google.com/s2/favicons?sz=64&domain=${source.domain}`
                  }
                  width={LOGO_SIZE}
                  height={LOGO_SIZE}
                  loading="lazy"
                  alt={source.name}
                  onError={(e) => {
                    const currentSrc = e.currentTarget.getAttribute("src") || "";
                    if (!currentSrc.endsWith("placeholder.svg")) {
                      e.currentTarget.src = FALLBACK_ICON;
                    }
                  }}
                />
              </div>
              <span className="sources-marquee-label">{source.name}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
