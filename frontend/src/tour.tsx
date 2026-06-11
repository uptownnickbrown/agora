/* Pip's guided tour: overlay steps for demo visitors (and the curious).
   Navigates the real UI as it talks; explore freely, leave anytime. */
import React, { useEffect, useState } from "react";
import { Asset } from "./ui";

type Step = { go?: string; title: string; text: string };

const TOURS: Record<"student" | "instructor", Step[]> = {
  student: [
    { go: "market", title: "The Market Square",
      text: "That chart is real. Every point on it came from an actual trade between merchants in this town, because nobody assigns prices here; they happen on their own." },
    { go: "market", title: "Bids and asks",
      text: "A Bid buys and an Ask sells, and leaving the price blank takes the going rate. Mind that your coins are escrowed the moment you post. The Agora does not do take-backsies." },
    { go: "crier", title: "The Agora Crier",
      text: "The market report arrives nightly, and when something big hits town (a festival, a drought, a royal decree) you read it here first. I'm quoted often, and always correctly." },
    { go: "workshop", title: "The Workshop",
      text: "Gather with your ⭐ specialty for triple yield, and craft goods worth more than their parts. Later you'll build facilities that work while you sleep. Fixed costs, dear student." },
    { go: "docks", title: "The Docks",
      text: "Fishing costs effort, and the fishery belongs to everyone. Remember I said that, because it becomes extremely important around week six." },
    { go: "puzzle", title: "The Daily Ledger",
      text: "One puzzle a day, the same for the whole class. Solve it for bonus effort and the right to gloat in the dining hall." },
    { go: "boards", title: "Leaderboards and your grade",
      text: "Wealth buys bragging rights, not grades. Your grade comes from playing and from showing me you understand, and I quiz gently; tap my portrait anytime. Now go trade something." },
  ],
  instructor: [
    { go: "dashboard", title: "Your dashboard",
      text: "World vitals, every market, and your roster in one view. The join code at the top is all students need to enroll. The world runs itself; nothing here requires daily attention." },
    { go: "feed", title: "Detected moments",
      text: "Shortages, price spikes, cartels, and disengagement are detected automatically, grouped, and ranked. Each comes with a one-click response, and each one is ready-made lecture material." },
    { go: "interventions", title: "Interventions",
      text: "Choose an intervention, preview its effect, then run it now or schedule it for a later day. Students see only the Town Crier's headlines, never your hand." },
    { go: "heatmap", title: "Mastery",
      text: "Every learning objective for every student, measured by in-game tutor checks. Green is mastered; red is what to cover in your next lecture." },
    { go: "playbook", title: "The Lecture Playbook",
      text: "A weekly brief on your class's economy, with discussion questions tied to trades your students actually made. Generate one for any week of the course." },
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
