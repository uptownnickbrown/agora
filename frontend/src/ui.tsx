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
  // Count toward the new amount — money you can watch arrive.
  const [shown, setShown] = useState(amount);
  useEffect(() => {
    const from = shown;
    if (from === amount) return;
    const t0 = performance.now(), dur = 600;
    let raf = 0;
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / dur);
      const eased = 1 - (1 - k) * (1 - k);
      setShown(Math.round(from + (amount - from) * eased));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [amount]);
  return (
    <span className="stat" title="coppers">
      <span className="coin" /> <b>{shown.toLocaleString()}</b>
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

export function Sparkline({ points, width = 280, height = 80, stroke = "#5f7a4a",
                            refLine, refLabel }: {
  points: (number | null)[]; width?: number; height?: number; stroke?: string;
  refLine?: number | null; refLabel?: string;
}) {
  const vals = points.filter((p): p is number => p != null);
  if (vals.length < 2) return <div className="muted">not enough history yet</div>;
  let min = Math.min(...vals), max = Math.max(...vals);
  if (refLine != null) { min = Math.min(min, refLine); max = Math.max(max, refLine); }
  const span = max - min || 1;
  const X = (idx: number) => (idx / (points.length - 1)) * (width - 46) + 4;
  const Y = (p: number) => height - 8 - ((p - min) / span) * (height - 20);
  const pts: { x: number; y: number; v: number }[] = [];
  points.forEach((p, idx) => { if (p != null) pts.push({ x: X(idx), y: Y(p), v: p }); });
  const line = pts.map((c) => `${c.x},${c.y}`).join(" ");
  const area = `${pts[0].x},${height - 6} ${line} ${pts[pts.length - 1].x},${height - 6}`;
  const last = pts[pts.length - 1];
  return (
    <svg className="sparkline" width={width} height={height}
         viewBox={`0 0 ${width} ${height}`}
         style={{ maxWidth: "100%", height: "auto" }}>
      {[0.25, 0.5, 0.75].map((f) => (
        <line key={f} x1={4} x2={width - 42} y1={8 + f * (height - 20)}
              y2={8 + f * (height - 20)} stroke="#3b3023" strokeOpacity={0.07} />
      ))}
      <polygon points={area} fill={stroke} opacity={0.12} />
      <polyline fill="none" stroke={stroke} strokeWidth={2.2}
                strokeLinejoin="round" strokeLinecap="round" points={line} />
      {refLine != null && (
        <>
          <line x1={4} x2={width - 42} y1={Y(refLine)} y2={Y(refLine)}
                stroke="#b5485d" strokeWidth={1.5} strokeDasharray="5 4" />
          {refLabel && <text x={6} y={Y(refLine) - 3} fontSize={10}
                             fill="#b5485d">{refLabel}</text>}
        </>
      )}
      <circle cx={last.x} cy={last.y} r={3.4} fill={stroke}
              stroke="#fffdf6" strokeWidth={1.4} />
      <text x={last.x + 7} y={last.y + 4} fontSize={12} fontWeight={700}
            fill="#3b3023">{last.v}</text>
      <text x={4} y={12} fontSize={10} fill="#6b5d49">{max}</text>
      <text x={4} y={height - 1} fontSize={10} fill="#6b5d49">{min}</text>
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
