/* Small shared UI atoms in the parchment-and-felt direction. Rendered-asset
   slots (see docs/ASSET_WISHLIST.md) fall back to emoji glyphs gracefully. */
import React, { useEffect, useState } from "react";

export const GOOD_GLYPHS: Record<string, string> = {
  grain: "🌾", wood: "🪵", wool: "🧶", fish: "🐟", ore: "⛏️", herbs: "🌿",
  flour: "🥡", lumber: "🪚", cloth: "🧵", medicine: "🧪", iron: "🔩",
  bread: "🍞", garments: "👘", tapestries: "🖼️", tools: "🛠️", glowdye: "✨",
};

export function Asset({ slot, glyph, size = 24, alt }: {
  slot: string; glyph: string; size?: number; alt?: string;
}) {
  // Tries /assets/<slot>.png (the wishlist slot); falls back to an emoji glyph.
  const [failed, setFailed] = useState(false);
  if (failed) return <span style={{ fontSize: size * 0.82 }} aria-label={alt}>{glyph}</span>;
  return (
    <img src={`/assets/${slot}.png`} width={size} height={size} alt={alt || slot}
         style={{ objectFit: "contain", verticalAlign: "middle" }}
         onError={() => setFailed(true)} />
  );
}

export function GoodIcon({ good, size = 22 }: { good: string; size?: number }) {
  return <Asset slot={`goods/${good}`} glyph={GOOD_GLYPHS[good] || "📦"} size={size} alt={good} />;
}

export function Coins({ amount }: { amount: number }) {
  return (
    <span className="stat" title="coppers">
      <span className="coin" /> <b>{amount.toLocaleString()}</b>
    </span>
  );
}

export function EffortBar({ effort, cap = 40 }: { effort: number; cap?: number }) {
  const pips = Math.min(10, Math.ceil(cap / 4));
  const filled = Math.round((effort / cap) * pips);
  return (
    <span className="stat" title={`${effort} effort`}>
      {Array.from({ length: pips }, (_, i) => (
        <span key={i} className={`effort-pip ${i < filled ? "" : "spent"}`} />
      ))}
      <b>{effort}</b>
    </span>
  );
}

export function Toast({ message, error, onDone }: {
  message: string; error?: boolean; onDone: () => void;
}) {
  useEffect(() => {
    const t = setTimeout(onDone, 3200);
    return () => clearTimeout(t);
  }, [onDone]);
  return <div className={`toast ${error ? "error" : ""}`}>{message}</div>;
}

export function Sparkline({ points, width = 280, height = 80, stroke = "#5f7a4a" }: {
  points: (number | null)[]; width?: number; height?: number; stroke?: string;
}) {
  const vals = points.filter((p): p is number => p != null);
  if (vals.length < 2) return <div className="muted">not enough history yet</div>;
  const min = Math.min(...vals), max = Math.max(...vals);
  const span = max - min || 1;
  let i = -1;
  const coords = points.map((p, idx) => {
    if (p == null) return null;
    i++;
    const x = (idx / (points.length - 1)) * (width - 8) + 4;
    const y = height - 6 - ((p - min) / span) * (height - 14);
    return `${x},${y}`;
  }).filter(Boolean);
  return (
    <svg className="sparkline" width={width} height={height}
         viewBox={`0 0 ${width} ${height}`}>
      <polyline fill="none" stroke={stroke} strokeWidth={2.2}
                strokeLinejoin="round" strokeLinecap="round"
                points={coords.join(" ")} />
      <text x={4} y={12} fontSize={11} fill="#6b5d49">{max}</text>
      <text x={4} y={height - 2} fontSize={11} fill="#6b5d49">{min}</text>
    </svg>
  );
}

export function Confetti() {
  const colors = ["#c4633e", "#7a9460", "#d9a93f", "#b5485d", "#aecbd8"];
  return (
    <span style={{ position: "relative", display: "inline-block", width: 0, height: 0 }}>
      {Array.from({ length: 14 }, (_, i) => (
        <span key={i} className="confetti" style={{
          left: (i - 7) * 9, top: -6,
          background: colors[i % colors.length],
          animationDelay: `${(i % 5) * 0.06}s`,
        }} />
      ))}
    </span>
  );
}
