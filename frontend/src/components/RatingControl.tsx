// Rating control: 1..5 buttons + optional "no rating" clear.

import { useState } from "react";

export function RatingControl({
  value,
  onChange,
  disabled,
}: {
  value: number | null;
  onChange: (n: number) => void;
  disabled?: boolean;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const shown = hover ?? value ?? 0;
  return (
    <div
      className="inline-flex items-center gap-1"
      role="radiogroup"
      aria-label="Rate this movie 1 to 5"
    >
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={(value ?? 0) === n}
          disabled={disabled}
          onMouseEnter={() => setHover(n)}
          onMouseLeave={() => setHover(null)}
          onClick={() => onChange(n)}
          className={
            "h-8 w-8 rounded-full border text-sm transition " +
            (shown >= n
              ? "border-accent bg-accent/20 text-white"
              : "border-slate-700 bg-bg text-slate-400") +
            (disabled ? " cursor-not-allowed opacity-60" : " hover:border-accent")
          }
        >
          {n}
        </button>
      ))}
    </div>
  );
}
