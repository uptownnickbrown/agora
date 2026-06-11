/* Pip's guided tour: overlay steps for demo visitors (and the curious).
   Navigates the real UI as it talks; explore freely, leave anytime. */
import React, { useEffect, useState } from "react";
import { Asset } from "./ui";

type Step = { go?: string; title: string; text: string };

const TOURS: Record<"student" | "instructor", Step[]> = {
  student: [
    { go: "market", title: "The Market Square",
      text: "That chart is real — every point on it came from an actual trade between merchants in this town. Prices here aren't assigned. They happen." },
    { go: "market", title: "Bids and asks",
      text: "Bid buys, Ask sells. Leave the price blank to take the going rate. Your coins are escrowed the moment you post — the Agora does not do take-backsies." },
    { go: "crier", title: "The Agora Crier",
      text: "Market reports nightly. And when something big hits — a festival, a drought, a royal decree — you read it here first. I'm quoted often, and always correctly." },
    { go: "workshop", title: "The Workshop",
      text: "Gather with your ⭐ specialty for triple yield, craft goods worth more than their parts, and later: build facilities that work while you sleep. Fixed costs, dear student." },
    { go: "docks", title: "The Docks",
      text: "Fishing costs effort, and the fishery belongs to everyone. Remember I said that — it becomes extremely important around week six." },
    { go: "puzzle", title: "The Daily Ledger",
      text: "One puzzle a day, the same for the whole class. Solve it for bonus effort and the right to gloat in the dining hall." },
    { go: "boards", title: "Leaderboards — and your grade",
      text: "Wealth buys bragging rights, not grades. Your grade comes from playing and from showing me you understand. Tap my portrait anytime — I quiz gently. Now: go trade something." },
  ],
  instructor: [
    { go: "dashboard", title: "Your dashboard",
      text: "Vitals, every market, the roster — a five-minute read. The join code up top is all students need. You are now a low-touch god; the world runs itself unless you reach for a lever." },
    { go: "feed", title: "Detected moments",
      text: "Shortages, spikes, cartels, disengagement — found for you, deduplicated, ranked, each with a one-click response. This is Monday's lecture material, pre-harvested." },
    { go: "interventions", title: "The lever room",
      text: "Pick a calamity, preview its effect, execute now or schedule it. Students never see your hand — only the Crier's headlines. Try a drought. It's reversible. Mostly." },
    { go: "heatmap", title: "Mastery heatmap",
      text: "Every learning objective, every student. Green is learned; red is what to teach Monday. It fills in as students answer my little checks." },
    { go: "playbook", title: "The Lecture Playbook",
      text: "What happened in YOUR class's economy this week — with discussion questions keyed to trades your students actually made. Generate one. I write quickly." },
  ],
};

export function Tour({ role, go, onDone }: {
  role: "student" | "instructor";
  go: (target: string) => void;
  onDone: () => void;
}) {
  const steps = TOURS[role];
  const [i, setI] = useState(0);
  const step = steps[i];

  useEffect(() => {
    if (step?.go) go(step.go);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i]);

  if (!step) return null;
  const last = i === steps.length - 1;
  return (
    <div className="tour-card">
      <Asset slot="pip/pip_talking" glyph="🐦" size={64} alt="Professor Pip" />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
          <b style={{ fontFamily: "var(--font-display)", fontSize: 16 }}>
            {step.title}</b>
          <span className="muted" style={{ fontSize: 11 }}>
            Pip's tour · {i + 1}/{steps.length}</span>
          <button className="dismiss" style={{ marginLeft: "auto" }}
                  aria-label="end tour" onClick={onDone}>✕</button>
        </div>
        <div style={{ fontSize: 13.5, margin: "4px 0 8px" }}>{step.text}</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {i > 0 && <button className="quiet" style={{ padding: "4px 12px" }}
                            onClick={() => setI(i - 1)}>back</button>}
          <button style={{ padding: "4px 14px" }}
                  onClick={() => (last ? onDone() : setI(i + 1))}>
            {last ? "Set me loose!" : "next"}</button>
          <span style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
            {steps.map((_, d) => (
              <span key={d} className={`tour-dot ${d === i ? "on" : ""}`} />
            ))}
          </span>
        </div>
      </div>
    </div>
  );
}
