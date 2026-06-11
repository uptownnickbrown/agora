/* Professor Pip: chat dock + tutor checks + the daily puzzle. */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { Asset, Confetti } from "./ui";

type Notify = (msg: string, error?: boolean) => void;

export function PipDock({ wid, nudge, checkAvailable }: {
  wid: string; nudge: string | null; checkAvailable?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"chat" | "check">("chat");
  const [history, setHistory] = useState<{ role: string; content: string }[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [check, setCheck] = useState<any>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<any>(null);
  const [nudgeDismissed, setNudgeDismissed] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // a fresh nudge un-dismisses; an old one stays dismissed
  useEffect(() => { setNudgeDismissed(false); }, [nudge]);

  const loadHistory = useCallback(
    () => api.get(`/worlds/${wid}/tutor/history`).then(setHistory).catch(() => {}),
    [wid]);
  useEffect(() => { if (open) loadHistory(); }, [open, loadHistory]);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 99999 });
  }, [history, feedback]);

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

  async function loadCheck() {
    setMode("check"); setFeedback(null); setAnswer("");
    const c = await api.get(`/worlds/${wid}/tutor/check`);
    setCheck(c);
  }

  async function submitCheck() {
    if (!check || busy) return;
    setBusy(true);
    try {
      const out = await api.post(`/worlds/${wid}/tutor/check`, {
        question_id: check.question_id, answer,
      });
      setFeedback(out);
    } catch (e: any) { setFeedback({ feedback: e.message, correct: false }); }
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
          </div>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <div className="pip-avatar" role="button"
               title={checkAvailable ? "Pip has a question for you"
                                     : "Ask Professor Pip"}
               style={{ cursor: "pointer", position: "relative",
                        overflow: "visible" }}
               onClick={() => setOpen(true)}>
            <Asset slot={nudge && !nudgeDismissed ? "pip/pip_talking" : "pip/pip_idle"}
                   glyph="🐦" size={58} alt="Professor Pip" />
            {checkAvailable && <span className="pip-badge" />}
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
                     : feedback?.correct ? "pip/pip_celebrating" : "pip/pip_idle"}
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
                    onClick={() => setMode("chat")}>chat</button>
            <button className="quiet" style={{ padding: "3px 10px" }}
                    onClick={loadCheck}>quiz me</button>
            <button className="quiet" style={{ padding: "3px 10px" }}
                    onClick={() => setOpen(false)}>✕</button>
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
                <div key={i} className={`msg ${m.role}`}>{m.content}</div>
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

        {mode === "check" && check && (
          <div style={{ padding: "8px 2px" }}>
            {check.done ? (
              <div className="msg tutor">{check.message}</div>
            ) : (
              <>
                <div className="kicker">tutor check</div>
                <p style={{ margin: "6px 0" }}>{check.prompt}</p>
                {check.kind === "mcq" ? (
                  <div className="col" style={{ gap: 6 }}>
                    {check.choices.map((c: string, i: number) => (
                      <button key={i}
                              className={answer === String(i) ? "" : "quiet"}
                              style={{ textAlign: "left" }}
                              onClick={() => setAnswer(String(i))}>
                        {String.fromCharCode(65 + i)}. {c}
                      </button>
                    ))}
                  </div>
                ) : (
                  <textarea rows={3} style={{ width: "100%" }} value={answer}
                            placeholder="One or two sentences…"
                            onChange={(e) => setAnswer(e.target.value)} />
                )}
                {!feedback ? (
                  <button style={{ marginTop: 8 }} disabled={answer === "" || busy}
                          onClick={submitCheck}>Answer</button>
                ) : (
                  <div className="msg tutor" style={{ marginTop: 8 }}>
                    {feedback.correct && <Confetti />}
                    <b className={feedback.correct ? "heat-good" : "heat-bad"}>
                      {feedback.correct ? `✓ ${feedback.score}/100` : `✗ ${feedback.score}/100`}
                    </b>{" "}
                    {feedback.feedback}
                    <div><button className="quiet" style={{ marginTop: 6 }}
                                 onClick={loadCheck}>another</button></div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function Puzzle({ wid, notify, refresh }: {
  wid: string; notify: Notify; refresh: () => void;
}) {
  const [state, setState] = useState<any>(null);
  const [guess, setGuess] = useState("");

  const load = useCallback(
    () => api.get(`/worlds/${wid}/puzzle`).then(setState).catch(() => {}), [wid]);
  useEffect(() => { load(); }, [load]);

  async function submit() {
    const g = parseInt(guess, 10);
    if (isNaN(g)) return;
    try {
      const out = await api.post(`/worlds/${wid}/puzzle/guess`, { guess: g });
      if (out.solved) notify("📈 Solved! +2 effort. Tell your friends (not the answer).");
      else if (out.finished) notify("The ledger closes. Tomorrow, redemption.", true);
      setGuess("");
      await load(); refresh();
    } catch (e: any) { notify(e.message, true); }
  }

  if (!state) return <div className="panel">Unrolling today's ledger…</div>;

  const heatClass = (f: string) =>
    f === "correct" ? "correct" : f.includes("scalding") ? "scalding"
      : f.includes("warm") ? "warm" : "cold";
  const arrow = (f: string) =>
    f === "correct" ? "✓" : f.startsWith("higher") ? "↑" : "↓";

  const shareCard = state.feedback
    .map((f: string) => f === "correct" ? "🟩" : f.includes("scalding") ? "🟥"
      : f.includes("warm") ? "🟧" : "🟦").join("");

  return (
    <div className="panel" style={{ maxWidth: 480, margin: "0 auto",
                                    textAlign: "center" }}>
      <h3>🧮 Market Mastermind — Day {state.day}</h3>
      {(state.streak > 0 || state.streak_best > 0) && (
        <div style={{ marginBottom: 8 }}>
          <span className="streak-chip" title="puzzle streak">
            🔥 {state.streak} day{state.streak === 1 ? "" : "s"}
            {state.streak_best > state.streak && <span style={{ opacity: 0.7 }}>
              &nbsp;· best {state.streak_best}</span>}
          </span>
        </div>
      )}
      <p>The mystery: yesterday's close for <b>{state.good}</b>.</p>
      <p className="muted" style={{ fontStyle: "italic" }}>Clue: {state.clue}</p>
      <div className="puzzle-grid" style={{ alignItems: "center" }}>
        {state.guesses.map((g: number, i: number) => (
          <div key={i} className="puzzle-row">
            <div className={`puzzle-cell ${heatClass(state.feedback[i])}`}>{g}</div>
            <div style={{ width: 80, textAlign: "left" }}>
              {arrow(state.feedback[i])} {state.feedback[i].split(":")[1] || "exact!"}
            </div>
          </div>
        ))}
      </div>
      {!state.finished ? (
        <div className="row" style={{ justifyContent: "center", alignItems: "center" }}>
          <input type="number" min={10} max={99} value={guess} style={{ width: 90 }}
                 placeholder="10–99"
                 onChange={(e) => setGuess(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && submit()} />
          <button onClick={submit}>
            Guess ({state.guesses.length + 1}/{state.max_guesses})
          </button>
        </div>
      ) : (
        <div>
          {state.solved && <Confetti />}
          <div style={{ margin: "6px 0" }}>
            <Asset slot={state.solved ? "pip/pip_celebrating" : "pip/pip_concerned"}
                   glyph={state.solved ? "🎉" : "🐦"} size={72}
                   alt={state.solved ? "Pip celebrates" : "Pip consoles"} />
          </div>
          <p>{state.solved ? "Solved! +2 effort, and Pip is insufferably proud."
            : "Closed for the day. Tomorrow, redemption."}</p>
          <div style={{ fontSize: 22, letterSpacing: 2 }}>{shareCard}</div>
          <button className="quiet" style={{ marginTop: 6 }}
                  onClick={() => {
                    navigator.clipboard?.writeText(
                      `Market Mastermind day ${state.day}: ${shareCard}`);
                    notify("Copied — go gloat.");
                  }}>copy share card</button>
        </div>
      )}
    </div>
  );
}
