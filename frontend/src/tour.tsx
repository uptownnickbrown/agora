/* Pip's guided tour: overlay steps for demo visitors (and the curious).
   Navigates the real UI as it talks; explore freely, leave anytime. */
import React, { useEffect, useState } from "react";
import { Asset } from "./ui";

type Step = { go?: string; title: string; text: string };

const TOURS: Record<"student" | "instructor", Step[]> = {
  student: [
    { go: "market", title: "The Market Square",
      text: "That chart is real. Every point on it came from an actual trade between merchants in this town, because nobody assigns prices here; they happen on their own. A Bid buys, an Ask sells, and leaving the price blank takes the going rate." },
    { go: "market", title: "Today's caravan visitor",
      text: "See the trader at the top of the square? One deal a day: they name a good, you name a price, and their true limit stays hidden until the table clears. Quote too timidly and you leave coppers behind. That sting has a name — surplus — and you'll feel it before you can define it." },
    { go: "crier", title: "The Agora Crier",
      text: "The market report arrives nightly, and when something big hits town (a festival, a drought, a royal decree) you read it here first. I'm quoted often, and always correctly." },
    { go: "workshop", title: "The Workshop",
      text: "Gather with your starred specialty for triple yield, and craft goods worth more than their parts. Mind your effort bar up top: twenty fresh at dawn, forty at most, and the rest evaporates. Later, buildings will work while you sleep. Fixed costs, dear student." },
    { go: "docks", title: "The Docks",
      text: "Cast a line, wait for the strike, reel like you mean it. The fishery belongs to everyone — remember I said that, because it becomes extremely important around week six." },
    { go: "puzzle", title: "The Daily Ledger",
      text: "Sixteen tiles, four hidden groups, four mistakes — one board a day, the same for the whole class. Solve it for bonus effort and the right to gloat in the dining hall." },
    { go: "study", title: "The Study",
      text: "My favorite room. Every idea in the course sits here with a meter showing how well you've shown it to me, and you can practice any of them — some with charts to read. This mastery, not your coin purse, is what your grade grows from." },
    { go: "boards", title: "Leaderboards",
      text: "Wealth buys bragging rights, not grades — the Crown checked. Watch the puzzle streaks and the biggest-catch board if you want a rivalry worth having." },
    { go: "market", title: "Your first move",
      text: "Enough of me. Post a bid for something cheap, strike a deal with the caravan, or spend three effort at the Docks — and once you've made your first coppers, I'll be in the corner with today's question." },
  ],
  instructor: [
    { go: "dashboard", title: "Your dashboard",
      text: "World vitals, every market, and your roster in one view. The join code at the top is all students need to enroll. The world runs itself; nothing here requires daily attention." },
    { go: "feed", title: "Detected moments",
      text: "Shortages, price spikes, cartels, and disengagement are detected automatically, grouped, and ranked. Each comes with a one-click response, and each one is ready-made lecture material." },
    { go: "interventions", title: "Interventions",
      text: "Choose an intervention, preview its effect, then run it now or schedule it for a later day. Students see only the Town Crier's headlines, never your hand." },
    { go: "heatmap", title: "Mastery",
      text: "Every learning objective for every student, measured by in-game tutor checks — hover any column for the full Bloom-aligned objective. Students see their own row in Pip's Study and can practice weak objectives directly, so expect red cells to heal between lectures." },
    { go: "playbook", title: "The Playbook and the Monday Brief",
      text: "A lecture-prep brief built from your class's actual market data, with discussion questions tied to trades your students really made. It is also emailed to you every Monday with the gradebook attached, so the default workload is reading one email." },
    { go: "dashboard", title: "That's the whole job",
      text: "The simulation runs itself, the Brief lands on Mondays, and you drop in for the fun parts. This is a shared demo world, so go ahead: visit Interventions, cause a drought, and watch the Feed light up." },
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
                            onClick={() => setI(i - 1)}>Back</button>}
          <button style={{ padding: "4px 14px" }}
                  onClick={() => (last ? onDone() : setI(i + 1))}>
            {last ? "Set me loose!" : "Next"}</button>
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
