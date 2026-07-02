/* Small shared UI atoms in the parchment-and-felt direction. Rendered-asset
   slots (see docs/ASSET_WISHLIST.md) fall back to emoji glyphs gracefully. */
import React, { useEffect, useRef, useState } from "react";

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

/** Floating "+12 / −3" that rises off a stat chip whenever its value moves.
    The Clash-of-Clans rule: never let a currency change silently. */
function useDelta(value: number) {
  const [deltas, setDeltas] = useState<{ id: number; amount: number }[]>([]);
  const prev = useRef(value);
  const nextId = useRef(0);
  useEffect(() => {
    const d = value - prev.current;
    prev.current = value;
    if (d === 0) return;
    const id = nextId.current++;
    setDeltas((ds) => [...ds, { id, amount: d }]);
    const t = setTimeout(() =>
      setDeltas((ds) => ds.filter((x) => x.id !== id)), 1400);
    return () => clearTimeout(t);
  }, [value]);
  return deltas;
}

function DeltaFloats({ deltas }: { deltas: { id: number; amount: number }[] }) {
  return (
    <>
      {deltas.map((d) => (
        <span key={d.id} className={`stat-delta ${d.amount > 0 ? "gain" : "loss"}`}>
          {d.amount > 0 ? "+" : "−"}{Math.abs(d.amount).toLocaleString()}
        </span>
      ))}
    </>
  );
}

export function Coins({ amount, onClick }: { amount: number; onClick?: () => void }) {
  // Count toward the new amount — money you can watch arrive.
  const [shown, setShown] = useState(amount);
  const deltas = useDelta(amount);
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
    <span className={`stat ${onClick ? "stat-button" : ""}`} role={onClick ? "button" : undefined}
          title="Coppers — earn them by selling; spend them on goods, buildings, and finery."
          onClick={onClick}>
      <span className="coin" /> <b>{shown.toLocaleString()}</b>
      <span className="stat-label">coppers</span>
      <DeltaFloats deltas={deltas} />
    </span>
  );
}

export function EffortBar({ effort, cap = 40, onClick }: {
  effort: number; cap?: number; onClick?: () => void;
}) {
  const pips = Math.min(10, Math.ceil(cap / 4));
  const filled = Math.round((effort / cap) * pips);
  const deltas = useDelta(effort);
  const brimming = effort > cap - 20; // tomorrow's +20 would spill over the cap
  return (
    <span className={`stat ${onClick ? "stat-button" : ""} ${brimming ? "stat-brimming" : ""}`}
          role={onClick ? "button" : undefined}
          title={brimming
            ? `Effort ${effort}/${cap} — brimming! Anything over ${cap} at dawn is lost, so spend some today.`
            : `Effort ${effort}/${cap} — your daily energy. +20 at dawn, up to ${cap}. Gathering, crafting, and fishing spend it.`}
          onClick={onClick}>
      {Array.from({ length: pips }, (_, i) => (
        <span key={i} className={`effort-pip ${i < filled ? "" : "spent"}`} />
      ))}
      <b>{effort}<span className="stat-cap">/{cap}</span></b>
      <span className="stat-label">effort</span>
      <DeltaFloats deltas={deltas} />
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

const DIAGRAM_COLORS: Record<string, string> = {
  sage: "#5f7a4a", terracotta: "#a84f2f", sky: "#4a7a96", ink: "#3b3023",
};

/** Painted-style economics diagram for tutor checks. Data space is 0-100 on
    both axes; the spec contract lives in backend/app/pedagogy/bank.py. */
export function Diagram({ spec, width = 360, height = 250 }: {
  spec: any; width?: number; height?: number;
}) {
  const padL = 36, padR = 34, padT = 14, padB = 32;
  const X = (x: number) => padL + (x / 100) * (width - padL - padR);
  const Y = (y: number) => height - padB - (y / 100) * (height - padT - padB);
  const color = (c: string) => DIAGRAM_COLORS[c] || DIAGRAM_COLORS.ink;
  return (
    <svg className="diagram" width={width} height={height}
         viewBox={`0 0 ${width} ${height}`}
         style={{ maxWidth: "100%", height: "auto" }} role="img"
         aria-label={`${spec.ylab} against ${spec.xlab} diagram`}>
      <rect x={0} y={0} width={width} height={height} rx={12} fill="#fffdf6"
            stroke="#d9cba8" />
      {/* axes */}
      <line x1={X(0)} y1={Y(0)} x2={X(0)} y2={Y(102)} stroke="#6b5d49"
            strokeWidth={1.5} />
      <line x1={X(0)} y1={Y(0)} x2={X(103)} y2={Y(0)} stroke="#6b5d49"
            strokeWidth={1.5} />
      <text x={X(0) - 4} y={padT + 2} fontSize={11} fontWeight={600}
            fill="#6b5d49" textAnchor="start">{spec.ylab}</text>
      <text x={width - padR} y={height - 6} fontSize={11} fontWeight={600}
            fill="#6b5d49" textAnchor="end">{spec.xlab}</text>
      {/* dotted guides from a point to both axes, with readable values */}
      {(spec.guides || []).map((g: any, i: number) => (
        <g key={`g${i}`}>
          <line x1={X(g.q)} y1={Y(0)} x2={X(g.q)} y2={Y(g.p)} stroke="#8a6a48"
                strokeWidth={1} strokeDasharray="2 4" />
          <line x1={X(0)} y1={Y(g.p)} x2={X(g.q)} y2={Y(g.p)} stroke="#8a6a48"
                strokeWidth={1} strokeDasharray="2 4" />
          <text x={X(g.q)} y={Y(0) + 12} fontSize={10} fill="#6b5d49"
                textAnchor="middle">{g.q}</text>
        </g>
      ))}
      {/* the ceiling / floor line */}
      {spec.hline && (
        <g>
          <line x1={X(0)} y1={Y(spec.hline.p)} x2={X(100)} y2={Y(spec.hline.p)}
                stroke="#b5485d" strokeWidth={2} strokeDasharray="7 5" />
          <text x={X(100) + 3} y={Y(spec.hline.p) + 4} fontSize={10.5}
                fontWeight={700} fill="#b5485d">{spec.hline.label}</text>
          <text x={X(0) - 4} y={Y(spec.hline.p) + 4} fontSize={10}
                fill="#b5485d" textAnchor="end">{spec.hline.p}</text>
        </g>
      )}
      {/* curves */}
      {(spec.lines || []).map((l: any, i: number) => {
        const pts = l.pts.map(([x, y]: number[]) => `${X(x)},${Y(y)}`).join(" ");
        const [lx, ly] = l.pts[l.pts.length - 1];
        return (
          <g key={`l${i}`}>
            <polyline points={pts} fill="none" stroke={color(l.color)}
                      strokeWidth={2.4} strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeDasharray={l.dashed ? "7 5" : undefined} />
            <text x={X(lx) + 5} y={Y(ly) + 4} fontSize={12} fontWeight={700}
                  fill={color(l.color)}>{l.label}</text>
          </g>
        );
      })}
      {/* named points (equilibria etc.) */}
      {(spec.points || []).map((p: any, i: number) => (
        <g key={`p${i}`}>
          <circle cx={X(p.q)} cy={Y(p.p)} r={4} fill="#d9a93f"
                  stroke="#3b3023" strokeWidth={1.2} />
          {p.label && <text x={X(p.q) + 7} y={Y(p.p) - 6} fontSize={12}
                            fontWeight={700} fill="#3b3023">{p.label}</text>}
        </g>
      ))}
    </svg>
  );
}

/** Lightweight inline markdown (bold/italic) for LLM text — Pip writes in
    asterisks; render them instead of printing them. */
export function InlineMd({ text }: { text: string }) {
  const out: React.ReactNode[] = [];
  const re = /\*\*([^*]+)\*\*|\*([^*]+)\*/g;
  let last = 0, m: RegExpExecArray | null, k = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    out.push(m[1] ? <b key={k++}>{m[1]}</b> : <i key={k++}>{m[2]}</i>);
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return <span style={{ whiteSpace: "pre-wrap" }}>{out}</span>;
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
