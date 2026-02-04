import { Fragment } from "react";

interface InlineEmphasisProps {
  text: string;
}

export function InlineEmphasis({ text }: InlineEmphasisProps) {
  if (!text) {
    return null;
  }
  const parts = text.split("**");
  return (
    <>
      {parts.map((part, index) => {
        if (!part) {
          return null;
        }
        if (index % 2 === 1) {
          return (
            <strong key={`em-${index}`} className="font-semibold text-foreground">
              {part}
            </strong>
          );
        }
        return <Fragment key={`txt-${index}`}>{part}</Fragment>;
      })}
    </>
  );
}
