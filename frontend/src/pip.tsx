/* Professor Pip: chat dock + tutor checks + the daily puzzle. */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { Asset, Confetti, Diagram, InlineMd } from "./ui";

type Notify = (msg: string, error?: boolean) => void;

/** Anywhere in the app can summon Pip: openPip("chat" | "check"). */
export function openPip(mode: "chat" | "check" = "chat") {
  window.dispatchEvent(new CustomEvent("agora-pip", { detail: { mode } }));
}

/** One tutor check, end to end: question (with optional diagram), answer,
    feedback, next. Shared by the dock (compact) and the Study (roomy). */
export function CheckCard({ wid, lo, notify, refresh, compact, onAnswered }: {
  wid: string; lo?: string | null; notify?: Notify; refresh?: () => void;
  compact?: boolean; onAnswered?: (out: any) => void;
}) {
  const [check, setCheck] = useState<any>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setFeedback(null); setAnswer(""); setCheck(null);
    try {
      const c = await api.get(
        `/worlds/${wid}/tutor/check${lo ? `?lo=${encodeURIComponent(lo)}` : ""}`);
      setCheck(c);
    } catch (e: any) { notify?.(e.message, true); }
  }, [wid, lo, notify]);
  useEffect(() => { load(); }, [load]);

  async function submit() {
    if (!check || busy) return;
    setBusy(true);
    try {
      const out = await api.post(`/worlds/${wid}/tutor/check`, {
        question_id: check.question_id, answer,
      });
      setFeedback(out);
      if (out.effort_gained > 0) {
        notify?.(`+${out.effort_gained} effort — study pays.`);
        refresh?.();
      }
      onAnswered?.(out);
    } catch (e: any) { setFeedback({ feedback: e.message, correct: false, score: 0 }); }
    setBusy(false);
  }

  if (!check) return <div className="muted" style={{ padding: 8 }}>
    Pip shuffles his question cards…</div>;
  if (check.done) return <div className="msg tutor">{check.message}</div>;

  return (
    <div style={{ padding: compact ? "8px 2px" : 0 }}>
      <p style={{ margin: "6px 0", fontWeight: 600 }}>{check.prompt}</p>
      {check.diagram && (
        <div style={{ margin: "8px 0", textAlign: "center" }}>
          <Diagram spec={check.diagram} width={compact ? 316 : 400}
                   height={compact ? 220 : 270} />
        </div>
      )}
      {check.kind === "mcq" ? (
        <div className="col" style={{ gap: 6 }}>
          {check.choices.map((c: string, i: number) => (
            <button key={i}
                    className={`check-choice ${answer === String(i) ? "" : "quiet"}`}
                    disabled={!!feedback}
                    onClick={() => setAnswer(String(i))}>
              {String.fromCharCode(65 + i)}. {c}
            </button>
          ))}
        </div>
      ) : (
        <textarea rows={compact ? 3 : 4} style={{ width: "100%" }} value={answer}
                  disabled={!!feedback}
                  placeholder="One or two sentences…"
                  onChange={(e) => setAnswer(e.target.value)} />
      )}
      {!feedback ? (
        <button style={{ marginTop: 8 }} disabled={answer === "" || busy}
                onClick={submit}>{busy ? "Grading…" : "Answer"}</button>
      ) : (
        <div className="msg tutor" style={{ marginTop: 8, maxWidth: "100%" }}>
          {feedback.correct && <Confetti />}
          <b className={feedback.correct ? "heat-good" : "heat-bad"}>
            {feedback.correct ? `✓ ${feedback.score}/100` : `✗ ${feedback.score}/100`}
          </b>{" "}
          <InlineMd text={feedback.feedback} />
          {feedback.effort_gained > 0 && (
            <div className="heat-good" style={{ marginTop: 4 }}>
              +{feedback.effort_gained} effort for today's first correct answer
            </div>
          )}
          <div><button className="quiet" style={{ marginTop: 6 }}
                       onClick={load}>Another</button></div>
        </div>
      )}
    </div>
  );
}

export function PipDock({ wid, day, nudge, checkAvailable, inStudy, onGoStudy }: {
  wid: string; day: number; nudge: string | null; checkAvailable?: boolean;
  inStudy?: boolean; onGoStudy?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"chat" | "check">("chat");
  const [history, setHistory] = useState<{ role: string; content: string }[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [celebrating, setCelebrating] = useState(false);
  const [nudgeDismissed, setNudgeDismissed] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // a fresh nudge un-dismisses; an old one stays dismissed
  useEffect(() => { setNudgeDismissed(false); }, [nudge]);

  // Anyone can summon Pip (welcome card, the Study, nudges).
  useEffect(() => {
    const summon = (e: Event) => {
      setOpen(true);
      setMode((e as CustomEvent).detail?.mode === "check" ? "check" : "chat");
    };
    window.addEventListener("agora-pip", summon);
    return () => window.removeEventListener("agora-pip", summon);
  }, []);

  // Once per world day: if Pip has a question waiting, open with it. The
  // single biggest thing between a shy student and the tutor is the click.
  // (Not in the Study — the question is already front and center there.)
  useEffect(() => {
    if (!checkAvailable || inStudy) return;
    const key = `agora_pip_auto_${wid}`;
    if (localStorage.getItem(key) === String(day)) return;
    localStorage.setItem(key, String(day));
    const t = setTimeout(() => { setOpen(true); setMode("check"); }, 1500);
    return () => clearTimeout(t);
  }, [checkAvailable, inStudy, wid, day]);

  const loadHistory = useCallback(
    () => api.get(`/worlds/${wid}/tutor/history`).then(setHistory).catch(() => {}),
    [wid]);
  useEffect(() => { if (open) loadHistory(); }, [open, loadHistory]);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 99999 });
  }, [history, busy]);

  async function send() {
    if (!draft.trim() || busy) return;
    const message = draft;
    setDraft("");
    setHistory((h) => [...h, { role: "user", content: message }]);
    setBusy(true);
    try {
      const out = await api.post(`/worlds/${wid}/tutor/chat`, { message });
      setHistory((h) => [...h, { role: "tutor", content: out.reply }]);
    } catch (e: any) {
      setHistory((h) => [...h, { role: "tutor", content: `(${e.message})` }]);
    }
    setBusy(false);
  }

  if (!open) {
    return (
      <div className="pip-dock" style={{ width: "auto" }}>
        {nudge && !nudgeDismissed && (
          <div className="pip-bubble nudge" style={{ marginBottom: 8, maxWidth: 300,
                                                     paddingRight: 26 }}>
            <button className="dismiss" aria-label="dismiss"
                    onClick={() => setNudgeDismissed(true)}>✕</button>
            {nudge}
            {checkAvailable && (
              <div>
                <button style={{ marginTop: 8, padding: "4px 12px" }}
                        onClick={() => { setOpen(true); setMode("check"); }}>
                  Take today's check</button>
              </div>
            )}
          </div>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <div role="button"
               title={checkAvailable ? "Pip has a question for you"
                                     : "Ask Professor Pip"}
               style={{ cursor: "pointer", textAlign: "center" }}
               onClick={() => setOpen(true)}>
            <div className="pip-avatar"
                 style={{ position: "relative", overflow: "visible",
                          margin: "0 auto" }}>
              <Asset slot={nudge && !nudgeDismissed ? "pip/pip_talking" : "pip/pip_idle"}
                     glyph="🐦" size={62} alt="Professor Pip" />
              {checkAvailable && <span className="pip-badge" />}
            </div>
            <span className="pip-label">
              {checkAvailable ? "Pip has a question" : "Ask Pip"}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="pip-dock">
      <div className="panel" style={{ padding: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div className="pip-avatar" style={{ width: 44, height: 44 }}>
            <Asset slot={busy ? "pip/pip_talking"
                     : celebrating ? "pip/pip_celebrating" : "pip/pip_idle"}
                   glyph="🐦" size={38} alt="Professor Pip" />
          </div>
          <div>
            <b>Professor Pip</b>
            <div className="muted" style={{ fontSize: 11 }}>
              market pigeon · tenured
            </div>
          </div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <button className="quiet" style={{ padding: "3px 10px" }}
                    onClick={() => setMode("chat")}>Chat</button>
            <button className="quiet" style={{ padding: "3px 10px" }}
                    onClick={() => setMode("check")}>Quiz</button>
            <button className="quiet" style={{ padding: "3px 10px" }}
                    aria-label="close" onClick={() => setOpen(false)}>✕</button>
          </div>
        </div>

        {mode === "chat" && (
          <>
            <div className="pip-chat" ref={scrollRef}>
              {history.length === 0 && (
                <div className="msg tutor">
                  Coo! Ask me anything about your markets. I'll guide; I won't trade
                  for you. A pigeon has principles.
                </div>
              )}
              {history.map((m, i) => (
                <div key={i} className={`msg ${m.role}`}>
                  <InlineMd text={m.content} />
                </div>
              ))}
              {busy && <div className="msg tutor muted">…preening thoughtfully…</div>}
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <input style={{ flex: 1 }} value={draft} placeholder="Ask Pip…"
                     onChange={(e) => setDraft(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && send()} />
              <button onClick={send} disabled={busy}>Send</button>
            </div>
          </>
        )}

        {mode === "check" && (
          <>
            <div className="kicker" style={{ marginTop: 6 }}>tutor check</div>
            <CheckCard wid={wid} compact
                       onAnswered={(out) => {
                         setCelebrating(!!out.correct);
                         setTimeout(() => setCelebrating(false), 2500);
                       }} />
            {onGoStudy && (
              <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
                Want to pick the topic and see your mastery?{" "}
                <a style={{ cursor: "pointer", fontWeight: 600,
                            color: "var(--sage-dark)" }}
                   onClick={() => { setOpen(false); onGoStudy(); }}>
                  Open the Study</a>.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/* Common Threads: sixteen terms, four hidden groups, four mistakes.
   The whole class gets the same board each day — argue accordingly. */

const TIER_EMOJI = ["🟨", "🟩", "🟦", "🟪"]; // share-text only, never UI chrome

export function Puzzle({ wid, notify, refresh }: {
  wid: string; notify: Notify; refresh: () => void;
}) {
  const [state, setState] = useState<any>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [order, setOrder] = useState<string[]>([]);
  const [shakeSel, setShakeSel] = useState(false);
  const [busy, setBusy] = useState(false);
  const [landed, setLanded] = useState<any | null>(null); // group banner animating in

  const load = useCallback(
    () => api.get(`/worlds/${wid}/puzzle`).then(setState).catch(() => {}), [wid]);
  useEffect(() => { load(); }, [load]);

  // Board = today's terms minus solved ones, in server order until shuffled.
  useEffect(() => {
    if (!state) return;
    const found = new Set(state.found.flatMap((g: any) => g.terms));
    setOrder((cur) => {
      const remaining = state.terms.filter((t: string) => !found.has(t));
      const keep = cur.filter((t) => remaining.includes(t));
      const missing = remaining.filter((t: string) => !keep.includes(t));
      return [...keep, ...missing];
    });
    setSelected((sel) => sel.filter((t) => !found.has(t)));
  }, [state]);

  function toggle(term: string) {
    if (busy || state?.finished) return;
    setSelected((sel) => sel.includes(term)
      ? sel.filter((t) => t !== term)
      : sel.length < 4 ? [...sel, term] : sel);
  }

  function shuffle() {
    setOrder((cur) => {
      const next = [...cur];
      for (let i = next.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [next[i], next[j]] = [next[j], next[i]];
      }
      return next;
    });
  }

  async function submit() {
    if (selected.length !== 4 || busy) return;
    setBusy(true);
    try {
      const out = await api.post(`/worlds/${wid}/puzzle/guess`, { terms: selected });
      if (out.result === "correct") {
        setLanded(out.group);
        setTimeout(() => setLanded(null), 900);
        if (out.solved) {
          notify(`Solved! +${out.effort_gained} effort. Pip is insufferably proud.`);
          refresh();
        }
      } else if (out.result === "one_away") {
        setShakeSel(true); setTimeout(() => setShakeSel(false), 500);
        notify("One away! Coo… so close.", true);
      } else if (out.result === "already_guessed") {
        notify("You already tried that set.", true);
      } else {
        setShakeSel(true); setTimeout(() => setShakeSel(false), 500);
        if (out.finished) notify("The ledger closes. Tomorrow, redemption.", true);
      }
      if (out.result === "correct") setSelected([]);
      await load();
    } catch (e: any) { notify(e.message, true); }
    setBusy(false);
  }

  if (!state) return <div className="panel">Unrolling today's ledger…</div>;

  const shareCard = state.guess_tiers
    .map((tiers: number[]) => tiers.map((t) => TIER_EMOJI[t]).join(""))
    .join("\n");

  function copyShare() {
    navigator.clipboard?.writeText(
      `Common Threads — Day ${state.day}\n${shareCard}`);
    notify("Copied. Go gloat.");
  }

  const remaining = order.filter(
    (t) => !state.found.some((g: any) => g.terms.includes(t)));
  const unfound = state.finished && state.reveal
    ? state.reveal.filter((g: any) =>
        !state.found.some((f: any) => f.name === g.name))
    : [];

  return (
    <div className="panel" style={{ maxWidth: 560, margin: "0 auto",
                                    textAlign: "center" }}>
      <h3 style={{ marginBottom: 2 }}>
        <Asset slot="places/puzzle" glyph="🧮" size={22} />
        {" "}Common Threads — Day {state.day}</h3>
      <div className="muted" style={{ marginBottom: 10 }}>
        Find four groups of four. Everyone in class gets today's board.
      </div>
      {(state.streak > 0 || state.streak_best > 0) && (
        <div style={{ marginBottom: 10 }}>
          <span className="streak-chip" title="Daily puzzle streak — solve every day to keep it alive.">
            <Asset slot="ui/icon_flame" glyph="🔥" size={13} />
            {" "}{state.streak} day{state.streak === 1 ? "" : "s"}
            {state.streak_best > state.streak && <span style={{ opacity: 0.7 }}>
              &nbsp;· best {state.streak_best}</span>}
          </span>
        </div>
      )}

      {state.found.map((g: any) => (
        <div key={g.name}
             className={`thread-banner tier${g.tier} ${landed?.name === g.name ? "landed" : ""}`}>
          <b>{g.name}</b>
          <div>{g.terms.join(" · ")}</div>
        </div>
      ))}
      {unfound.map((g: any) => (
        <div key={g.name} className={`thread-banner tier${g.tier} missed`}>
          <b>{g.name}</b>
          <div>{g.terms.join(" · ")}</div>
        </div>
      ))}

      {!state.finished && (
        <>
          <div className="thread-grid">
            {remaining.map((t) => (
              <button key={t} type="button"
                      className={`thread-tile ${selected.includes(t) ? "picked" : ""}
                                  ${selected.includes(t) && shakeSel ? "shake" : ""}`}
                      onClick={() => toggle(t)}>
                {t}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", justifyContent: "center", gap: 6,
                        alignItems: "center", margin: "10px 0 4px" }}>
            <span className="muted">Mistakes left:</span>
            {Array.from({ length: state.max_mistakes }, (_, i) => (
              <span key={i} className={`mistake-dot ${
                i < state.mistakes_left ? "" : "burned"}`} />
            ))}
          </div>
          <div className="row" style={{ justifyContent: "center", marginTop: 8 }}>
            <button className="quiet" onClick={shuffle}>Shuffle</button>
            <button className="quiet" disabled={selected.length === 0}
                    onClick={() => setSelected([])}>Deselect</button>
            <button disabled={selected.length !== 4 || busy} onClick={submit}>
              Submit</button>
          </div>
          <div className="muted" style={{ marginTop: 10 }}>
            Solve it for +{state.reward_effort} effort
            (+{state.flawless_bonus} more with a clean sheet).
          </div>
        </>
      )}

      {state.finished && (
        <div style={{ marginTop: 10 }}>
          {state.solved && <Confetti />}
          <Asset slot={state.solved ? "pip/pip_celebrating" : "pip/pip_concerned"}
                 glyph="🐦" size={72}
                 alt={state.solved ? "Pip celebrates" : "Pip consoles"} />
          <p style={{ marginTop: 4 }}>
            {state.solved
              ? state.mistakes_left === state.max_mistakes
                ? "Flawless. Not a thread out of place."
                : "Solved! The threads come together."
              : "The threads slipped away today. Tomorrow, redemption."}
          </p>
          <div style={{ fontSize: 20, letterSpacing: 2, lineHeight: 1.25,
                        whiteSpace: "pre" }}>{shareCard}</div>
          <button className="quiet" style={{ marginTop: 8 }} onClick={copyShare}>
            Copy share card</button>
        </div>
      )}
    </div>
  );
}
