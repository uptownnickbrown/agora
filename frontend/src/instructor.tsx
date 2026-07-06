/* The instructor's backstage: dashboard, feed, interventions, pedagogy. */
import React, { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { Asset, GoodIcon, Sparkline } from "./ui";

type Notify = (msg: string, error?: boolean) => void;
type Prefill = { kind: string; params: Record<string, any> } | null;

/** "supply_shock" -> "Supply shock" */
const titleize = (k: string) => {
  const s = k.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
};

export function InstructorScreen({ wid, notify, tab: tabProp, setTab: setTabProp }: {
  wid: string; notify: Notify;
  tab?: string; setTab?: (t: string) => void;  // optionally controlled (tour)
}) {
  const [tabState, setTabState] = useState("dashboard");
  const tab = tabProp ?? tabState;
  const setTab = setTabProp ?? setTabState;
  const [prefill, setPrefill] = useState<Prefill>(null);
  const tabs: [string, string][] = [
    ["dashboard", "Dashboard"], ["feed", "Feed"], ["interventions", "Interventions"],
    ["heatmap", "Mastery"], ["gradebook", "Gradebook"], ["playbook", "Playbook"]];

  function respond(kind: string, params: Record<string, any>) {
    setPrefill({ kind, params });
    setTab("interventions");
  }

  return (
    <div className="col">
      <div className="places">
        {tabs.map(([t, label]) => (
          <div key={t} className={`place-tile ${tab === t ? "active" : ""}`}
               onClick={() => setTab(t)} role="button">{label}</div>
        ))}
      </div>
      {tab === "dashboard" && <Dashboard wid={wid} notify={notify} />}
      {tab === "feed" && <Feed wid={wid} onRespond={respond} />}
      {tab === "interventions" &&
        <Interventions wid={wid} notify={notify} prefill={prefill} />}
      {tab === "heatmap" && <Heatmap wid={wid} />}
      {tab === "gradebook" && <Gradebook wid={wid} />}
      {tab === "playbook" && <Playbook wid={wid} />}
    </div>
  );
}

function RulesChips({ rules }: { rules: any }) {
  const chips: { icon: string; glyph: string; label: string; cls: string }[] = [];
  Object.entries(rules?.ceilings || {}).forEach(([g, p]) =>
    chips.push({ icon: "ui/icon_scale", glyph: "⚖️",
                 label: `${g} ceiling ${p}`, cls: "heat-bad" }));
  Object.entries(rules?.floors || {}).forEach(([g, p]) =>
    chips.push({ icon: "ui/icon_scale", glyph: "⚖️",
                 label: `${g} floor ${p}`, cls: "heat-good" }));
  Object.entries(rules?.taxes || {}).forEach(([g, t]) =>
    chips.push({ icon: "ui/icon_tax", glyph: "🏛️",
                 label: `${g} tax ${t}/unit`, cls: "" }));
  Object.entries(rules?.subsidies || {}).forEach(([g, s]) =>
    chips.push({ icon: "ui/icon_subsidy", glyph: "🎁",
                 label: `${g} subsidy ${s}/unit`, cls: "" }));
  if (rules?.smog_tax)
    chips.push({ icon: "ui/icon_smog", glyph: "🏭",
                 label: `smog tax ${rules.smog_tax}/unit`, cls: "" });
  if (chips.length === 0)
    return <span className="muted">No price controls, taxes, or subsidies in force.</span>;
  return <>{chips.map((c) => (
    <span key={`${c.icon}${c.label}`} className={`tag ${c.cls}`}>
      <Asset slot={c.icon} glyph={c.glyph} size={14} /> {c.label}</span>))}</>;
}

function Dashboard({ wid, notify }: { wid: string; notify: Notify }) {
  const [data, setData] = useState<any>(null);
  const load = useCallback(
    () => api.get(`/worlds/${wid}/instructor/dashboard`).then(setData).catch(() => {}),
    [wid]);
  useEffect(() => { load(); }, [load]);
  if (!data) return <div className="panel">Loading…</div>;

  async function act(path: string, body?: any, msg = "Done.") {
    try { await api.post(path, body); notify(msg); await load(); }
    catch (e: any) { notify(e.message, true); }
  }

  const w = data.world;
  return (
    <div className="col">
      <div className="row">
        <div className="panel grow">
          <h3>World vitals</h3>
          <div className="row">
            <span className="plaque">Week {w.week}</span>
            <span className="plaque">Day {w.day}</span>
            <span className="plaque">{w.state.charAt(0).toUpperCase() + w.state.slice(1)}</span>
            <span className="plaque" style={{ cursor: "pointer" }}
                  title="Click to copy"
                  onClick={() => { navigator.clipboard?.writeText(w.join_code);
                                   notify("Join code copied."); }}>
              Join code: <b>{w.join_code}</b> ⧉</span>
            {w.smog > 0 && <span className="plaque">
              <Asset slot="ui/icon_smog" glyph="🏭" size={14} /> Smog {w.smog}</span>}
            <span className="plaque" title="fish stock">
              <GoodIcon good="fish" size={14} /> {w.fish_stock}</span>
            {w.demo && <span className="plaque"
              title="Shared demo world: lifecycle buttons are disabled; interventions work.">
              <Asset slot="ui/icon_flask" glyph="🧪" size={14} /> Demo world</span>}
          </div>
          {w.demo ? (
            <div className="muted" style={{ marginTop: 10 }}>
              This shared demo world runs and reseeds itself nightly, so the
              lifecycle controls are put away. Everything else is fair game —
              try the Interventions tab and cause a drought.
            </div>
          ) : (
            <div className="row" style={{ marginTop: 10 }}>
              <button onClick={() => act(`/worlds/${wid}/instructor/close-day`, undefined,
                                         "Day closed.")}>
                Run daily close</button>
              <button className="wood" onClick={() =>
                act(`/worlds/${wid}/instructor/advance-week`, undefined, "Week advanced.")}>
                Advance week</button>
              <button className="quiet"
                title="Moves the world to its epilogue: trading stops and students see their recaps."
                onClick={() =>
                  act(`/worlds/${wid}/instructor/state`, { state: "epilogue" },
                      "World moved to epilogue.")}>End world</button>
            </div>
          )}
          <div style={{ marginTop: 8 }}><RulesChips rules={w.market_rules} /></div>
        </div>
        <div className="panel grow">
          <h3>Vitals over time</h3>
          <div className="kicker">trade volume</div>
          <Sparkline points={data.vitals.map((v: any) => v.volume)} width={340} height={56} />
          <div className="kicker">wealth gini (bp)</div>
          <Sparkline points={data.vitals.map((v: any) => v.gini_bp)} width={340} height={56}
                     stroke="#c4633e" />
          <div className="kicker">fish stock</div>
          <Sparkline points={data.vitals.map((v: any) => v.fish_stock)} width={340}
                     height={56} stroke="#4a7a96" />
        </div>
      </div>
      <div className="row">
        <div className="panel grow">
          <h3>Price charts</h3>
          <div className="row">
            {Object.entries(data.charts).map(([good, pts]: [string, any]) => (
              <div key={good} style={{ flex: "1 1 200px" }}>
                <div className="kicker"><GoodIcon good={good} size={16} /> {good}</div>
                <Sparkline points={pts.map((p: any) => p.close)} width={210} height={56} />
              </div>
            ))}
          </div>
        </div>
        <div className="panel" style={{ flex: "0 1 320px" }}>
          <h3>Roster</h3>
          {data.roster.map((p: any) => (
            <div key={p.player_id} style={{ display: "flex", gap: 8 }}>
              <span style={{ flex: 1 }}>{p.merchant}</span>
              <span className="muted">{p.coins.toLocaleString()}c</span>
              <span className={w.day - p.last_active_day >= 5 ? "heat-bad" : "muted"}
                    title="last active">
                day {p.last_active_day}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// What the one-click response to each detected-moment kind should be.
const MOMENT_RESPONSES: Record<string, (good: string) => Prefill> = {
  shortage: (g) => ({ kind: "subsidy", params: { good: g, per_unit: 10 } }),
  price_spike: (g) => ({ kind: "supply_shock",
    params: { good: g, price_mult: 0.9, qty_mult: 1.6, days: 3 } }),
  price_crash: (g) => ({ kind: "demand_shock",
    params: { goods: [g], price_mult: 1.3, qty_mult: 1.5, days: 3 } }),
  seller_withdrawal: (g) => ({ kind: "repeal_ceiling", params: { good: g } }),
  market_concentration: (g) => ({ kind: "antitrust", params: { good: g } }),
  cartel_parallel_pricing: (g) => ({ kind: "antitrust", params: { good: g } }),
  fishery_depletion: () => ({ kind: "fishing_quota",
    params: { per_player_per_day: 3 } }),
  fishery_collapse: () => ({ kind: "fishing_quota",
    params: { per_player_per_day: 3 } }),
  smog_threshold: () => ({ kind: "smog_tax", params: { per_unit: 3 } }),
  disengagement: () => ({ kind: "stimulus", params: { amount: 50 } }),
};

function goodOf(m: any): string {
  return m.payload?.good || "";
}

function Feed({ wid, onRespond }: {
  wid: string; onRespond: (kind: string, params: Record<string, any>) => void;
}) {
  const [feed, setFeed] = useState<any>(null);
  useEffect(() => {
    api.get(`/worlds/${wid}/instructor/feed`).then(setFeed).catch(() => {});
  }, [wid]);
  if (!feed) return <div className="panel">Loading…</div>;

  // Digest: collapse the daily drumbeat into one card per (kind, good).
  const groups = new Map<string, any[]>();
  for (const m of feed.moments) {
    const key = `${m.kind}|${goodOf(m)}`;
    groups.set(key, [...(groups.get(key) || []), m]);
  }
  const sevRank: any = { alert: 2, notable: 1, info: 0 };
  const cards = [...groups.entries()].map(([key, ms]) => {
    const [kind, good] = key.split("|");
    const latest = ms.reduce((a, b) => (a.day >= b.day ? a : b));
    const sev = ms.reduce((s, m) => sevRank[m.severity] > sevRank[s] ? m.severity : s,
                          "info");
    const days = ms.map((m) => m.day);
    return { key, kind, good, ms, latest, sev,
             dayLo: Math.min(...days), dayHi: Math.max(...days) };
  }).sort((a, b) => b.latest.day - a.latest.day
    || sevRank[b.sev] - sevRank[a.sev]);

  return (
    <div className="row">
      <div className="panel grow">
        <h3>Detected moments</h3>
        <div className="muted" style={{ marginBottom: 8 }}>
          Market events detected in your world, newest first. Repeated alerts are
          grouped, and each can be answered with a one-click response.
        </div>
        {cards.length === 0 && <div className="muted">No notable events yet.
          As students trade, shortages, price spikes, and cartels will appear here.</div>}
        {cards.map((c) => (
          <div key={c.key} className={`moment-card ${c.sev}`}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="kicker" style={{ letterSpacing: "0.1em" }}>
                {c.kind.replace(/_/g, " ")}{c.good ? ` · ${c.good}` : ""}
              </span>
              <span className="count-badge">×{c.ms.length}</span>
              <span className="muted" style={{ fontSize: 11 }}>
                {c.dayLo === c.dayHi ? `day ${c.dayHi}` : `days ${c.dayLo}–${c.dayHi}`}
              </span>
              {MOMENT_RESPONSES[c.kind] && (
                <button className="quiet" style={{ marginLeft: "auto",
                                                   padding: "2px 10px", fontSize: 12 }}
                        onClick={() => {
                          const p = MOMENT_RESPONSES[c.kind](c.good);
                          if (p) onRespond(p.kind, p.params);
                        }}>
                  Respond</button>
              )}
            </div>
            <div style={{ fontSize: 14, marginTop: 3 }}>{c.latest.summary}</div>
            {c.ms.length > 1 && (
              <details style={{ marginTop: 4 }}>
                <summary className="muted" style={{ cursor: "pointer", fontSize: 12 }}>
                  {c.ms.length - 1} earlier
                </summary>
                {c.ms.filter((m) => m !== c.latest)
                  .sort((a: any, b: any) => b.day - a.day)
                  .map((m: any) => (
                    <div key={m.id} className="muted" style={{ fontSize: 12 }}>
                      day {m.day}: {m.summary}
                    </div>
                  ))}
              </details>
            )}
          </div>
        ))}
      </div>
      <div className="panel" style={{ flex: "0 1 340px" }}>
        <h3>Your interventions</h3>
        {feed.interventions.length === 0 &&
          <div className="muted">None yet. The world runs on its own until you
            choose to step in.</div>}
        {feed.interventions.map((i: any, idx: number) => (
          <div key={idx} className="crier-post">
            <div className="crier-kicker">day {i.day} · {i.kind}</div>
            <div style={{ fontSize: 13 }}>{i.crier}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Per-parameter form fields; anything unlisted falls back to the JSON editor.
const PARAM_FIELDS: Record<string, { label: string; type: string; step?: number;
                                     def: any; hint?: string }> = {
  good: { label: "Good", type: "good", def: "grain" },
  goods: { label: "Goods", type: "goods", def: ["garments"] },
  price: { label: "Price (coppers)", type: "number", def: 60 },
  per_unit: { label: "Per unit (coppers)", type: "number", def: 8 },
  days: { label: "Days", type: "number", def: 3 },
  price_mult: { label: "Price multiplier", type: "number", step: 0.1, def: 1.5,
                hint: "Above 1, NPCs pay and charge more." },
  qty_mult: { label: "Quantity multiplier", type: "number", step: 0.1, def: 0.5,
              hint: "Below 1 creates scarcity; above 1, a glut." },
  per_player_per_day: { label: "Per merchant per day", type: "number", def: 3 },
  closed: { label: "Fishery closed?", type: "bool", def: true },
  auction_id: { label: "Auction ID", type: "text", def: "glowdye-1" },
  licenses: { label: "Licenses for sale", type: "number", def: 4 },
  close_day_offset: { label: "Closes in (days)", type: "number", def: 2 },
  amount: { label: "Coppers per merchant", type: "number", def: 50 },
  player_id: { label: "Merchant", type: "player", def: "" },
  "player_id?": { label: "Merchant (optional)", type: "player", def: "" },
  divest_fraction: { label: "Divest fraction", type: "number", step: 0.1, def: 0.5 },
  fine: { label: "Fine (coppers)", type: "number", def: 100 },
};

function Interventions({ wid, notify, prefill }: {
  wid: string; notify: Notify; prefill: Prefill;
}) {
  const [catalog, setCatalog] = useState<Record<string, any>>({});
  const [goods, setGoods] = useState<{ id: string; name: string }[]>([]);
  const [roster, setRoster] = useState<{ player_id: string; merchant: string }[]>([]);
  const [kind, setKind] = useState("supply_shock");
  const [params, setParams] = useState<Record<string, any>>(
    { good: "grain", price_mult: 1.6, qty_mult: 0.45, days: 5 });
  const [rawMode, setRawMode] = useState(false);
  const [rawText, setRawText] = useState("");
  const [scheduleDay, setScheduleDay] = useState<number | "">("");
  const [preview, setPreview] = useState("");

  useEffect(() => {
    api.get(`/worlds/${wid}/instructor/interventions`).then((out) => {
      setCatalog(out.catalog); setGoods(out.goods); setRoster(out.roster);
    }).catch(() => {});
  }, [wid]);

  const pick = useCallback((k: string, preset?: Record<string, any>) => {
    setKind(k); setPreview("");
    const defaults: Record<string, any> = {};
    for (const p of (catalog[k]?.params || [])) {
      defaults[p] = PARAM_FIELDS[p]?.def ?? "";
    }
    setParams({ ...defaults, ...(preset || {}) });
  }, [catalog]);

  useEffect(() => {
    if (prefill && catalog[prefill.kind]) pick(prefill.kind, prefill.params);
  }, [prefill, catalog, pick]);

  function effective(): Record<string, any> {
    if (rawMode) {
      try { return JSON.parse(rawText); } catch { return params; }
    }
    const out: Record<string, any> = {};
    for (const [k, v] of Object.entries(params)) {
      if (v === "" || v == null) continue;
      out[k.replace(/\?$/, "")] = v;
    }
    return out;
  }

  async function run(schedule: boolean) {
    try {
      const body: any = { kind, params: effective() };
      if (schedule && scheduleDay !== "") body.schedule_day = scheduleDay;
      const out = await api.post(`/worlds/${wid}/instructor/interventions`, body);
      notify(out.scheduled ? `Scheduled for day ${scheduleDay}.` : `Done: ${out.crier}`);
    } catch (e: any) { notify(e.message, true); }
  }

  async function doPreview() {
    const out = await api.post(`/worlds/${wid}/instructor/interventions/preview`,
                               { kind, params: effective() });
    setPreview(out.preview);
  }

  function field(p: string) {
    const spec = PARAM_FIELDS[p];
    if (!spec) return null;
    const val = params[p];
    const set = (v: any) => setParams((cur) => ({ ...cur, [p]: v }));
    return (
      <React.Fragment key={p}>
        <label>{spec.label}</label>
        <div>
          {spec.type === "good" && (
            <select value={val} onChange={(e) => set(e.target.value)}>
              {goods.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
          )}
          {spec.type === "goods" && (
            <div className="row" style={{ gap: 6 }}>
              {goods.map((g) => {
                const on = (val || []).includes(g.id);
                return (
                  <span key={g.id} className="tag"
                        style={{ cursor: "pointer",
                                 background: on ? "var(--sage)" : undefined,
                                 color: on ? "#fff" : undefined }}
                        onClick={() => set(on ? val.filter((x: string) => x !== g.id)
                                             : [...(val || []), g.id])}>
                    {g.name}
                  </span>
                );
              })}
            </div>
          )}
          {spec.type === "number" && (
            <input type="number" step={spec.step || 1} value={val}
                   style={{ width: 110 }}
                   onChange={(e) => set(e.target.value === "" ? ""
                     : +e.target.value)} />
          )}
          {spec.type === "text" && (
            <input value={val} style={{ width: 160 }}
                   onChange={(e) => set(e.target.value)} />
          )}
          {spec.type === "bool" && (
            <select value={String(val)} onChange={(e) => set(e.target.value === "true")}>
              <option value="true">yes</option>
              <option value="false">no</option>
            </select>
          )}
          {spec.type === "player" && (
            <select value={val} onChange={(e) => set(e.target.value)}>
              <option value="">Choose…</option>
              {roster.map((r) => (
                <option key={r.player_id} value={r.player_id}>{r.merchant}</option>
              ))}
            </select>
          )}
          {spec.hint && <span className="muted" style={{ marginLeft: 8,
            fontSize: 12 }}>{spec.hint}</span>}
        </div>
      </React.Fragment>
    );
  }

  return (
    <div className="row">
      <div className="panel" style={{ flex: "0 1 300px" }}>
        <h3>Catalog</h3>
        {Object.entries(catalog).map(([k, v]: [string, any]) => (
          <div key={k} className="place-tile"
               style={{ textAlign: "left", marginBottom: 6, padding: "6px 10px",
                        background: k === kind ? "var(--wood)" : undefined,
                        color: k === kind ? "var(--parchment)" : undefined }}
               onClick={() => pick(k)}
               role="button">
            <b>{titleize(k)}</b>
            <div style={{ fontSize: 12 }}>{v.blurb}</div>
          </div>
        ))}
      </div>
      <div className="panel grow">
        <h3>{titleize(kind)}</h3>
        <div className="muted">Students experience interventions as in-world news
          from the Town Crier. Your name never appears.</div>
        {!rawMode ? (
          <div className="form-grid">
            {(catalog[kind]?.params || []).map((p: string) => field(p))}
          </div>
        ) : (
          <textarea rows={4} style={{ width: "100%", marginTop: 8 }}
                    value={rawText} onChange={(e) => setRawText(e.target.value)} />
        )}
        <div className="row" style={{ alignItems: "center", marginTop: 10 }}>
          <button className="quiet" onClick={doPreview}>Preview impact</button>
          <button onClick={() => run(false)}>Execute now</button>
          <label className="muted">or schedule for day:
            <input type="number" style={{ width: 64, marginLeft: 6 }}
                   value={scheduleDay}
                   onChange={(e) => setScheduleDay(
                     e.target.value === "" ? "" : +e.target.value)} />
          </label>
          <button className="wood" disabled={scheduleDay === ""}
                  onClick={() => run(true)}>Schedule</button>
          <button className="quiet" style={{ marginLeft: "auto", fontSize: 12 }}
                  onClick={() => {
                    if (!rawMode) setRawText(JSON.stringify(effective(), null, 1));
                    setRawMode(!rawMode);
                  }}>
            {rawMode ? "Form" : "Raw JSON"}</button>
        </div>
        {preview && <div className="pip-bubble" style={{ marginTop: 10 }}>{preview}</div>}
      </div>
    </div>
  );
}

const heatColor = (pct: number | null) =>
  pct == null ? "#eee" : pct > 70 ? "var(--sage)" : pct > 40 ? "#ecc473" : "var(--terracotta)";

function HeatLegend() {
  return (
    <div className="row" style={{ gap: 14, margin: "2px 0 10px", fontSize: 12 }}>
      {[["var(--sage)", "Above 70%: mastered"],
        ["#ecc473", "40–70%: developing"],
        ["var(--terracotta)", "Below 40%: needs teaching"],
        ["#eee", "Blank: not yet assessed"]].map(([bg, label]) => (
        <span key={label} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
          <span style={{ width: 12, height: 12, borderRadius: 3, background: bg,
                         border: "1px solid rgba(0,0,0,0.12)" }} />
          <span className="muted">{label}</span>
        </span>
      ))}
    </div>
  );
}

/** Right-hand drill-down: the full Bloom-aligned objective, class stats,
    who needs a check-in, and the actual assessment items behind the column. */
function LoDetail({ lo, students }: { lo: any; students: any[] }) {
  const cells = students
    .map((s) => ({ merchant: s.merchant, pct: s.scores[lo.id] == null
      ? null : Math.round(s.scores[lo.id] / 10) }));
  const assessed = cells.filter((c) => c.pct != null) as
    { merchant: string; pct: number }[];
  const buckets: [string, string, number][] = [
    ["Mastered", "var(--sage)", assessed.filter((c) => c.pct > 70).length],
    ["Developing", "#ecc473", assessed.filter((c) => c.pct > 40 && c.pct <= 70).length],
    ["Needs teaching", "var(--terracotta)", assessed.filter((c) => c.pct <= 40).length],
    ["Not yet assessed", "#ddd", cells.length - assessed.length],
  ];
  const max = Math.max(1, ...buckets.map(([, , n]) => n));
  const checkIn = [...assessed].sort((a, b) => a.pct - b.pct)
    .filter((c) => c.pct <= 55).slice(0, 3);
  return (
    <>
      <div className="kicker">week {lo.week} · {lo.bloom || "objective"}</div>
      <div style={{ fontSize: 14.5, fontWeight: 600, lineHeight: 1.45,
                    margin: "4px 0 10px" }}>{lo.text}</div>
      <div className="row" style={{ gap: 8, marginBottom: 10 }}>
        <span className="plaque">class average{" "}
          <b>{lo.class_avg == null ? "—" : `${lo.class_avg}%`}</b></span>
        <span className="plaque">{lo.assessed}/{students.length} assessed</span>
      </div>
      {buckets.map(([label, bg, n]) => (
        <div key={label} style={{ display: "flex", alignItems: "center",
                                  gap: 8, marginBottom: 4, fontSize: 12.5 }}>
          <span style={{ width: 110 }} className="muted">{label}</span>
          <div className="meter" style={{ flex: 1 }}>
            <span style={{ width: `${Math.round(100 * n / max)}%`, background: bg }} />
          </div>
          <b style={{ width: 18, textAlign: "right" }}>{n}</b>
        </div>
      ))}
      {checkIn.length > 0 && (
        <>
          <div className="kicker" style={{ marginTop: 12 }}>worth a check-in</div>
          {checkIn.map((c) => (
            <div key={c.merchant} style={{ display: "flex", fontSize: 13.5 }}>
              <span style={{ flex: 1 }}>{c.merchant}</span>
              <b className={c.pct <= 40 ? "heat-bad" : ""}>{c.pct}%</b>
            </div>
          ))}
        </>
      )}
      {lo.sample_items?.length > 0 && (
        <>
          <div className="kicker" style={{ marginTop: 12 }}>
            from the item bank ({lo.item_count} items)</div>
          {lo.sample_items.map((s: string, i: number) => (
            <div key={i} className="muted"
                 style={{ fontSize: 12.5, fontStyle: "italic", margin: "5px 0",
                          paddingLeft: 10,
                          borderLeft: "3px solid var(--parchment-edge)" }}>
              “{s}”
            </div>
          ))}
        </>
      )}
      <div className="muted" style={{ fontSize: 12, marginTop: 12 }}>
        Students see this objective with their own score in Pip's Study and can
        practice it directly — red cells tend to heal between lectures.
      </div>
    </>
  );
}

function Heatmap({ wid }: { wid: string }) {
  const [data, setData] = useState<any>(null);
  const [sel, setSel] = useState<string | null>(null);
  useEffect(() => {
    api.get(`/worlds/${wid}/instructor/heatmap`).then((d) => {
      setData(d);
      // Open on the objective that most needs lecture time.
      const assessed = d.los.filter((lo: any) => lo.class_avg != null);
      const weakest = assessed.sort((a: any, b: any) => a.class_avg - b.class_avg)[0];
      setSel((weakest || d.los[0])?.id ?? null);
    }).catch(() => {});
  }, [wid]);
  if (!data) return <div className="panel">Loading…</div>;
  const empty = data.students.every((s: any) =>
    data.los.every((lo: any) => s.scores[lo.id] == null));
  const loLabel = (lo: any) => lo.short
    || titleize(lo.id.replace(/^ch\d+-/, "").replace(/-/g, "_"));
  const selected = data.los.find((lo: any) => lo.id === sel);

  // Week group headers: contiguous runs of lo.week.
  const weekSpans: { week: number; span: number }[] = [];
  for (const lo of data.los) {
    const last = weekSpans[weekSpans.length - 1];
    if (last && last.week === lo.week) last.span += 1;
    else weekSpans.push({ week: lo.week, span: 1 });
  }
  const weakest = data.los.filter((lo: any) => lo.class_avg != null)
    .sort((a: any, b: any) => a.class_avg - b.class_avg).slice(0, 2);

  if (empty) {
    return (
      <div className="panel">
        <h3>Mastery heatmap</h3>
        <div className="pip-bubble" style={{ maxWidth: 560 }}>
          No tutor checks have been answered yet. Checks appear naturally as
          students play, so expect the first results within a day or two of
          class activity.
        </div>
      </div>
    );
  }

  return (
    <div className="col">
      <div className="panel" style={{ padding: "12px 16px" }}>
        <div className="row" style={{ alignItems: "center", gap: 10 }}>
          <h3 style={{ margin: 0 }}>Mastery heatmap</h3>
          <span className="plaque">class average <b>{data.class_avg ?? "—"}%</b></span>
          <span className="plaque">{data.students.length} students ×{" "}
            {data.los.length} objectives</span>
          {weakest.length > 0 && (
            <span className="muted" style={{ fontSize: 13 }}>
              Needs lecture time:{" "}
              {weakest.map((lo: any, i: number) => (
                <React.Fragment key={lo.id}>
                  {i > 0 && ", "}
                  <a style={{ cursor: "pointer", fontWeight: 600,
                              color: "var(--terracotta-dark)" }}
                     onClick={() => setSel(lo.id)}>
                    {loLabel(lo)} ({lo.class_avg}%)</a>
                </React.Fragment>
              ))}
            </span>
          )}
        </div>
        <div className="muted" style={{ marginTop: 4, fontSize: 13 }}>
          Every learning objective for every student, measured by Pip's in-game
          tutor checks. Click any column for the full objective, the class
          picture, and the assessment items behind it.
        </div>
      </div>
      <div className="row">
        <div className="panel grow" style={{ overflowX: "auto" }}>
          <HeatLegend />
          <table style={{ borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr>
                <th />
                {weekSpans.map(({ week, span }, i) => (
                  <th key={week} colSpan={span}
                      style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
                               textTransform: "uppercase", color: "var(--ink-soft)",
                               borderLeft: i > 0 ? "2px solid var(--parchment-edge)" : undefined,
                               padding: "2px 0" }}>
                    wk {week}
                  </th>
                ))}
                <th />
              </tr>
              <tr>
                <th style={{ textAlign: "left", padding: 4, verticalAlign: "bottom" }}>Student</th>
                {data.los.map((lo: any) => (
                  <th key={lo.id} title={`${lo.bloom ? `[${lo.bloom}] ` : ""}${lo.text}`}
                      onClick={() => setSel(lo.id)}
                      style={{ padding: "4px 2px", verticalAlign: "bottom",
                               fontSize: 10, cursor: "pointer",
                               fontWeight: sel === lo.id ? 800 : 500,
                               background: sel === lo.id
                                 ? "rgba(122,148,96,0.14)" : undefined,
                               borderRadius: "6px 6px 0 0" }}>
                    <div style={{ writingMode: "vertical-rl",
                                  transform: "rotate(180deg)",
                                  height: 130, overflow: "hidden",
                                  textOverflow: "ellipsis", whiteSpace: "nowrap",
                                  margin: "0 auto" }}>
                      {loLabel(lo)}
                    </div>
                  </th>
                ))}
                <th style={{ fontSize: 10, verticalAlign: "bottom", padding: "4px 2px" }}>
                  <div style={{ writingMode: "vertical-rl", transform: "rotate(180deg)",
                                height: 130, margin: "0 auto", fontWeight: 700 }}>
                    Average
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "2px solid var(--parchment-edge)" }}>
                <td style={{ padding: 4, fontWeight: 700 }}>Class average</td>
                {data.los.map((lo: any) => (
                  <td key={lo.id} title={`${lo.text}: class ${lo.class_avg ?? "—"}%`}
                      onClick={() => setSel(lo.id)}
                      style={{ width: 26, height: 22, background: heatColor(lo.class_avg),
                               border: "1px solid #fff", textAlign: "center",
                               fontWeight: 700, cursor: "pointer" }}>
                    {lo.class_avg ?? ""}
                  </td>
                ))}
                <td style={{ textAlign: "center", fontWeight: 700 }}>
                  {data.class_avg ?? ""}</td>
              </tr>
              {data.students.map((s: any) => (
                <tr key={s.merchant}>
                  <td style={{ padding: 4 }}>{s.merchant}</td>
                  {data.los.map((lo: any) => {
                    const score = s.scores[lo.id];
                    const pct = score == null ? null : Math.round(score / 10);
                    return (
                      <td key={lo.id} title={`${s.merchant} — ${lo.text}: ${pct ?? "not yet assessed"}${pct == null ? "" : "%"}`}
                          onClick={() => setSel(lo.id)}
                          style={{ width: 26, height: 22, background: heatColor(pct),
                                   border: "1px solid #fff", textAlign: "center",
                                   cursor: "pointer",
                                   outline: sel === lo.id
                                     ? "1px solid rgba(59,48,35,0.25)" : undefined }}>
                        {pct ?? ""}
                      </td>
                    );
                  })}
                  <td style={{ textAlign: "center", fontWeight: 600,
                               color: "var(--ink-soft)" }}>
                    {s.avg ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="panel" style={{ flex: "0 0 340px", alignSelf: "flex-start" }}>
          {selected
            ? <LoDetail lo={selected} students={data.students} />
            : <div className="muted">Click a column to inspect an objective.</div>}
        </div>
      </div>
    </div>
  );
}

function Gradebook({ wid }: { wid: string }) {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    api.get(`/worlds/${wid}/instructor/gradebook`).then(setRows).catch(() => {});
  }, [wid]);
  const noMastery = rows.length > 0 && rows.every((r) => r.mastery === 0);
  return (
    <div className="panel">
      <h3>Gradebook</h3>
      <div className="muted">Grades combine participation and concept mastery.
        In-game wealth is never graded.
        {" "}<a href={`/api/worlds/${wid}/instructor/gradebook.csv`}>Export CSV</a></div>
      {noMastery && (
        <div className="pip-bubble" style={{ maxWidth: 560, margin: "8px 0" }}>
          No tutor checks have been answered yet, so mastery is 0% and grades
          currently reflect participation only.
        </div>
      )}
      <table className="book" style={{ marginTop: 8 }}>
        <thead><tr><th style={{ textAlign: "left" }}>Student</th><th>Participation</th>
          <th>Mastery</th><th>Grade</th><th>Objectives</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.merchant}>
              <td style={{ textAlign: "left" }}>{r.merchant}</td>
              <td>{(r.participation * 100).toFixed(0)}%</td>
              <td>{(r.mastery * 100).toFixed(0)}%</td>
              <td><b>{(r.grade * 100).toFixed(0)}%</b></td>
              <td>{r.los_assessed}/{r.los_total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Tiny renderer for the playbook's markdown (headings, lists, bold/italics).
function Markdown({ text }: { text: string }) {
  const inline = (s: string) => {
    const out: React.ReactNode[] = [];
    const re = /\*\*([^*]+)\*\*|\*([^*]+)\*/g;
    let last = 0, m: RegExpExecArray | null, k = 0;
    while ((m = re.exec(s))) {
      if (m.index > last) out.push(s.slice(last, m.index));
      out.push(m[1] ? <b key={k++}>{m[1]}</b> : <i key={k++}>{m[2]}</i>);
      last = m.index + m[0].length;
    }
    if (last < s.length) out.push(s.slice(last));
    return out;
  };
  const blocks: React.ReactNode[] = [];
  let list: React.ReactNode[] = [];
  const flush = (k: string) => {
    if (list.length) {
      blocks.push(<ul key={k} style={{ margin: "4px 0 10px", paddingLeft: 22 }}>
        {list}</ul>);
      list = [];
    }
  };
  text.split("\n").forEach((line, i) => {
    const t = line.trim();
    if (/^#{1,2} /.test(t)) {
      flush(`f${i}`);
      blocks.push(<h3 key={i} style={{ marginTop: 14 }}>{inline(t.replace(/^#+ /, ""))}</h3>);
    } else if (/^### /.test(t)) {
      flush(`f${i}`);
      blocks.push(<h4 key={i} style={{ marginTop: 10 }}>{inline(t.slice(4))}</h4>);
    } else if (/^[-*] /.test(t)) {
      list.push(<li key={i}>{inline(t.slice(2))}</li>);
    } else if (/^\d+\. /.test(t)) {
      list.push(<li key={i}>{inline(t.replace(/^\d+\. /, ""))}</li>);
    } else if (t === "") {
      flush(`f${i}`);
    } else {
      flush(`f${i}`);
      blocks.push(<p key={i} style={{ margin: "6px 0" }}>{inline(t)}</p>);
    }
  });
  flush("end");
  return <div style={{ fontSize: 14.5 }}>{blocks}</div>;
}

function MondayBrief({ wid }: { wid: string }) {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [demo, setDemo] = useState(false);
  const [sending, setSending] = useState(false);
  const [sentTo, setSentTo] = useState("");
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState<any>(null);
  useEffect(() => {
    api.get(`/worlds/${wid}/instructor/digest/settings`)
      .then((out) => { setEnabled(out.enabled); setDemo(!!out.demo); })
      .catch(() => setEnabled(true));
  }, [wid]);
  async function toggle() {
    const next = !enabled;
    setEnabled(next);
    try { await api.post(`/worlds/${wid}/instructor/digest/settings`,
                         { enabled: next }); }
    catch { setEnabled(!next); }
  }
  async function sendNow() {
    setSending(true); setSentTo("");
    try {
      const out = await api.post(`/worlds/${wid}/instructor/digest/send`, {});
      setSentTo(out.sent_to);
    } catch { /* noop */ }
    setSending(false);
  }
  async function loadPreview() {
    setPreviewing(true);
    try {
      setPreview(await api.get(`/worlds/${wid}/instructor/digest/preview`));
    } catch { /* noop */ }
    setPreviewing(false);
  }
  return (
    <div className="panel">
      <h3>Monday Brief</h3>
      <div className="muted" style={{ marginBottom: 8 }}>
        Each Monday this playbook lands in your inbox with the sixty-second
        version on top: the week's biggest market story, class mastery, the
        concepts that need lecture time, students who may need a nudge, and
        the gradebook attached as CSV. No login required.
      </div>
      <div className="row" style={{ alignItems: "center" }}>
        <button onClick={loadPreview} disabled={previewing}>
          {previewing ? "Assembling from your class's week…"
            : preview ? "Rebuild the preview" : "Preview this week's brief"}</button>
        {!demo && <>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 6,
                          cursor: "pointer" }}>
            <input type="checkbox" checked={enabled ?? true} onChange={toggle} />
            Email me the brief each week
          </label>
          <button className="quiet" onClick={sendNow} disabled={sending}>
            {sending ? "Sending…" : "Email me this week's brief now"}</button>
          {sentTo && <span className="muted">Sent to {sentTo}.</span>}
        </>}
        {demo && <span className="muted">
          In your own course this arrives by email every Monday, gradebook
          attached — the demo world just previews it.</span>}
      </div>
      {preview && (
        <div style={{ marginTop: 12 }}>
          <div className="muted" style={{ fontSize: 12.5, marginBottom: 6 }}>
            Subject: <b>{preview.subject}</b>
            {preview.attachments?.length > 0 &&
              <> · attachment: {preview.attachments.join(", ")}</>}
          </div>
          <iframe title="Monday Brief preview" srcDoc={preview.html}
                  sandbox=""
                  style={{ width: "100%", height: 560, border:
                           "1px solid var(--parchment-edge)", borderRadius: 12,
                           background: "#efe9d8" }} />
        </div>
      )}
    </div>
  );
}

function Playbook({ wid }: { wid: string }) {
  const [week, setWeek] = useState<number | "">("");
  const [pb, setPb] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  async function generate(w: number | "" = week) {
    setBusy(true);
    try {
      const q = w === "" ? "" : `?week=${w}`;
      setPb(await api.get(`/worlds/${wid}/instructor/playbook${q}`));
    } catch { /* noop */ }
    setBusy(false);
  }
  return (
    <div className="col">
    <div className="panel">
      <h3>Lecture playbook</h3>
      <div className="muted" style={{ marginBottom: 8 }}>
        A lecture-prep brief assembled from your class's market data: what
        happened, which concepts need attention, and discussion questions tied
        to decisions your students actually made. This same brief lands in
        your inbox every Monday.
      </div>
      <div className="row" style={{ alignItems: "center" }}>
        <label>
          <select value={week} style={{ marginRight: 4 }}
                  onChange={(e) => setWeek(
                    e.target.value === "" ? "" : +e.target.value)}>
            <option value="">This week</option>
            {[1, 2, 3, 4, 5, 6, 7].map((w) => (
              <option key={w} value={w}>Week {w}</option>
            ))}
          </select>
        </label>
        <button onClick={() => generate()} disabled={busy}>
          {busy ? "Assembling from your class's data…"
            : pb ? "Rebuild" : "Open the playbook"}</button>
        {pb && <button className="quiet" onClick={() => {
          navigator.clipboard?.writeText(pb.markdown);
        }}>Copy Markdown</button>}
      </div>
      {pb && (
        <div style={{ background: "#fffdf6", padding: "8px 18px 14px",
                      borderRadius: 12,
                      border: "1px solid var(--parchment-edge)", marginTop: 10 }}>
          <Markdown text={pb.markdown} />
        </div>
      )}
    </div>
    <MondayBrief wid={wid} />
    </div>
  );
}
