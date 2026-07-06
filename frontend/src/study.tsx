/* The Study: Pip's room. Your mastery, objective by objective, and a desk
   where you practice whichever one wobbles. */
import React, { useCallback, useEffect, useState } from "react";
import { api, PlayerState } from "./api";
import { Asset } from "./ui";
import { CheckCard, openPip } from "./pip";

type Notify = (msg: string, error?: boolean) => void;

type MasteryRow = {
  lo_id: string; text: string; short: string; bloom: string; week: number;
  pct: number | null; attempts: number;
};

function meterColor(pct: number | null) {
  if (pct == null) return "rgba(59, 48, 35, 0.18)";
  if (pct > 70) return "var(--sage)";
  if (pct > 40) return "#ecc473";
  return "var(--terracotta)";
}

export function Study({ state, wid, notify, refresh }: {
  state: PlayerState; wid: string; notify: Notify; refresh: () => void;
}) {
  const [mastery, setMastery] = useState<MasteryRow[]>([]);
  const [lo, setLo] = useState<string | null>(null);

  const load = useCallback(
    () => api.get(`/worlds/${wid}/tutor/mastery`).then(setMastery).catch(() => {}),
    [wid]);
  useEffect(() => { load(); }, [load]);

  const assessed = mastery.filter((m) => m.pct != null);
  const avg = assessed.length
    ? Math.round(assessed.reduce((s, m) => s + (m.pct || 0), 0) / assessed.length)
    : null;
  const weakest = assessed.filter((m) => (m.pct || 0) <= 40);
  const weeks = [...new Set(mastery.map((m) => m.week))].sort((a, b) => a - b);
  const practicing = mastery.find((m) => m.lo_id === lo);

  return (
    <div className="row">
      <div className="panel grow" style={{ maxWidth: 660 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Asset slot="pip/pip_idle" glyph="🐦" size={54} alt="Professor Pip" />
          <div>
            <h3 style={{ marginBottom: 0 }}>Your mastery</h3>
            <div className="muted">
              What you've shown me you understand. This — not your coin
              purse — is what your grade grows from.
            </div>
          </div>
        </div>
        <div className="row" style={{ gap: 8, margin: "10px 0 4px" }}>
          <span className="plaque">{assessed.length}/{mastery.length} assessed</span>
          {avg != null && <span className="plaque">average {avg}%</span>}
          {weakest.length > 0 && (
            <span className="plaque" style={{ borderColor: "var(--terracotta)" }}>
              {weakest.length} need{weakest.length === 1 ? "s" : ""} work
            </span>
          )}
        </div>
        {weeks.map((w) => (
          <div key={w}>
            <div className="kicker" style={{ margin: "12px 0 4px" }}>
              week {w}{w === state.world.week ? " · this week" : ""}
            </div>
            {mastery.filter((m) => m.week === w).map((m) => (
              <div key={m.lo_id} className={`mastery-row ${lo === m.lo_id ? "active" : ""}`}
                   onClick={() => setLo(m.lo_id)} role="button"
                   title={m.pct == null
                     ? "Not yet assessed — practice to find out"
                     : `${m.pct}% over ${m.attempts} answer${m.attempts === 1 ? "" : "s"}`}>
                <span className="lo-text">
                  <span className="bloom-chip">{m.bloom}</span> {m.text}</span>
                <span className="meter mastery-meter">
                  <span style={{ width: `${Math.max(4, m.pct ?? 0)}%`,
                                 background: meterColor(m.pct) }} />
                </span>
                <span className="lo-pct">{m.pct == null ? "—" : `${m.pct}%`}</span>
                <button className="quiet lo-practice"
                        onClick={(e) => { e.stopPropagation(); setLo(m.lo_id); }}>
                  Practice</button>
              </div>
            ))}
          </div>
        ))}
        {mastery.length === 0 && <div className="muted" style={{ marginTop: 10 }}>
          The term hasn't started — check back when the market opens.</div>}
      </div>

      <div className="panel grow" style={{ minWidth: 320 }}>
        {practicing ? (
          <>
            <div className="kicker">practicing · {practicing.bloom}</div>
            <h3 style={{ marginBottom: 2 }}>{practicing.text}</h3>
            <div className="muted" style={{ marginBottom: 8 }}>
              {practicing.pct == null
                ? "First look at this one. No pressure; that's what practice is."
                : practicing.pct <= 40
                  ? "This one wobbles. A few good answers will steady it."
                  : practicing.pct <= 70
                    ? "Getting there. Sharpen it."
                    : "Already strong — keeping it warm never hurt."}
            </div>
            <CheckCard key={practicing.lo_id} wid={wid} lo={practicing.lo_id}
                       notify={notify} refresh={() => { refresh(); load(); }} />
            <button className="quiet" style={{ marginTop: 12 }}
                    onClick={() => setLo(null)}>Back to today's check</button>
          </>
        ) : (
          <>
            <div className="kicker">today's check</div>
            <div className="muted" style={{ margin: "4px 0 8px" }}>
              One question, picked from what's actually happening in your
              market. Your first correct answer each day earns +2 effort.
            </div>
            <CheckCard key="daily" wid={wid} notify={notify}
                       refresh={() => { refresh(); load(); }} />
            <hr className="divider" />
            <div className="muted">
              Stuck on an idea? <a style={{ cursor: "pointer", fontWeight: 600,
                                            color: "var(--sage-dark)" }}
                                   onClick={() => openPip("chat")}>Talk it out
              with Pip</a> — he guides, he doesn't hand out answers.
            </div>
          </>
        )}
      </div>
    </div>
  );
}
