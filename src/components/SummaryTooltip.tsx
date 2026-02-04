import { ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { InlineEmphasis } from "./InlineEmphasis";

interface SummaryTooltipProps {
  text?: string;
  children: ReactNode;
  tooltipClassName?: string;
}

export function SummaryTooltip({ text, children, tooltipClassName }: SummaryTooltipProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState({ left: 0, top: 0 });
  const [placeLeft, setPlaceLeft] = useState(false);
  const hasText = Boolean(text);

  const updatePosition = () => {
    const node = wrapperRef.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    const tooltipWidth = tooltipRef.current?.offsetWidth || 0;
    const rightSpace = window.innerWidth - (rect.right + 12);
    const overflowRatio =
      tooltipWidth > 0 ? (tooltipWidth - rightSpace) / tooltipWidth : 0;
    const shouldPlaceLeft = tooltipWidth > 0 && overflowRatio > 0.1;
    const left = shouldPlaceLeft ? rect.left - 12 : rect.right + 12;
    const top = rect.top + rect.height / 2;
    setPosition({ left, top });
    setPlaceLeft(shouldPlaceLeft);
  };

  useEffect(() => {
    if (!visible || !hasText) return;
    updatePosition();
    const handleScroll = () => updatePosition();
    const handleResize = () => updatePosition();
    window.addEventListener("scroll", handleScroll, true);
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("scroll", handleScroll, true);
      window.removeEventListener("resize", handleResize);
    };
  }, [hasText, visible]);

  useLayoutEffect(() => {
    if (!visible || !hasText) return;
    updatePosition();
  }, [hasText, visible, text]);

  if (!hasText) {
    return <>{children}</>;
  }

  const tooltip = (
    <div
      ref={tooltipRef}
      className={`summary-tooltip summary-tooltip-visible ${
        placeLeft ? "summary-tooltip-left" : ""
      } ${tooltipClassName || ""}`}
      role="tooltip"
      style={{ left: position.left, top: position.top }}
    >
      <InlineEmphasis text={text || ""} />
    </div>
  );

  return (
    <div
      className="summary-hover"
      ref={wrapperRef}
      onMouseEnter={() => {
        updatePosition();
        setVisible(true);
      }}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => {
        updatePosition();
        setVisible(true);
      }}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && typeof document !== "undefined" ? createPortal(tooltip, document.body) : null}
    </div>
  );
}
