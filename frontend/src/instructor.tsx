/* The instructor's backstage: dashboard, feed, interventions, pedagogy. */
import React, { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { GoodIcon, Sparkline } from "./ui";

type Notify = (msg: string, error?: boolean) => void;
type Prefill = { kind: string; params: Record<string, any> } | null;

export function InstructorScreen({ wid, notify }: { wid: string; notify: Notify }) {
  const [tab, setTab] = useState("dashboard");
  const [prefill, setPrefill] = useState<Prefill>(null);
  const tabs = ["dashboard", "feed", "interventions", "heatmap", "gradebook", "playbook"];

  function respond(kind: string, params: Record<string, any>) {
    setPrefill({ kind, params });
    setTab("interventions");
  }

  return (
    <div className="col">
      <div className="places">
        {tabs.map((t) => (
          <div key={t} className={`place-tile ${tab === t ? "active" : ""}`}
               onClick={() => setTab(t)} role="button">{t}</div>
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
  const chips: { label: string; cls: string }[] = [];
  Object.entries(rules?.ceilings || {}).forEach(([g, p]) =>
    chips.push({ label: `⚖️ ${g} ceiling ${p}`, cls: "heat-bad" }));
  Object.entries(rules?.floors || {}).forEach(([g, p]) =>
    chips.push({ label: `⚖️ ${g} floor ${p}`, cls: "heat-good" }));
  Object.entries(rules?.taxes || {}).forEach(([g, t]) =>
    chips.push({ label: `🏛️ ${g} tax ${t}/unit`, cls: "" }));
  Object.entries(rules?.subsidies || {}).forEach(([g, s]) =>
    chips.push({ label: `🎁 ${g} subsidy ${s}/unit`, cls: "" }));
  if (rules?.smog_tax) chips.push({ label: `🏭 smog tax ${rules.smog_tax}/unit`, cls: "" });
  if (chips.length === 0)
    return <span className="muted">No price controls, taxes, or subsidies in force.</span>;
  return <>{chips.map((c) => (
    <span key={c.label} className={`tag ${c.cls}`}>{c.label}</span>))}</>;
}

function Dashboard({ wid, notify }: { wid: string; notify: Notify }) {
  const [data, setData] = useState<any>(null);
  const load = useCallback(
    () => api.get(`/worlds/${wid}/instructor/dashboard`).then(setData).catch(() => {}),
    [wid]);
  useEffect(() => { load(); }, [load]);
  if (!data) return <div className="panel">Loading the world…</div>;

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
            <span className="plaque">{w.state}</span>
            <span className="plaque" style={{ cursor: "pointer" }}
                  title="click to copy"
                  onClick={() => { navigator.clipboard?.writeText(w.join_code);
                                   notify("Join code copied — paste it in your syllabus."); }}>
              join code: <b>{w.join_code}</b> ⧉</span>
            {w.smog > 0 && <span className="plaque">smog {w.smog}</span>}
            <span className="plaque">🐟 {w.fish_stock}</span>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <button onClick={() => act(`/worlds/${wid}/instructor/close-day`, undefined,
                                       "The market bell rings — day closed.")}>
              Run daily close</button>
            <button className="wood" onClick={() =>
              act(`/worlds/${wid}/instructor/advance-week`, undefined, "Week advanced.")}>
              Advance week</button>
            <button className="quiet" onClick={() =>
              act(`/worlds/${wid}/instructor/state`, { state: "epilogue" },
                  "The world enters its epilogue.")}>End world → epilogue</button>
          </div>
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
  concentration: (g) => ({ kind: "antitrust", params: { good: g } }),
  cartel: (g) => ({ kind: "antitrust", params: { good: g } }),
  parallel_pricing: (g) => ({ kind: "antitrust", params: { good: g } }),
  commons_depletion: () => ({ kind: "fishing_quota",
    params: { per_player_per_day: 3 } }),
  smog: () => ({ kind: "smog_tax", params: { per_unit: 3 } }),
  disengagement: () => ({ kind: "stimulus", params: { amount: 50 } }),
};

function goodOf(summary: string): string {
  return summary.match(/\b(?:in|of|on|for) ([a-z]+)\b/)?.[1] || "";
}

function Feed({ wid, onRespond }: {
  wid: string; onRespond: (kind: string, params: Record<string, any>) => void;
}) {
  const [feed, setFeed] = useState<any>(null);
  useEffect(() => {
    api.get(`/worlds/${wid}/instructor/feed`).then(setFeed).catch(() => {});
  }, [wid]);
  if (!feed) return <div className="panel">Listening…</div>;

  // Digest: collapse the daily drumbeat into one card per (kind, good).
  const groups = new Map<string, any[]>();
  for (const m of feed.moments) {
    const key = `${m.kind}|${goodOf(m.summary)}`;
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
          Repeated alerts are folded together — newest first. Each is a teachable
          moment; some deserve a response.
        </div>
        {cards.length === 0 && <div className="muted">Nothing yet. Give them time
          — someone always corners something.</div>}
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
                  ⚡ respond</button>
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
          <div className="muted">None yet. The world runs itself until you reach
            for a lever.</div>}
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
  good: { label: "good", type: "good", def: "grain" },
  goods: { label: "goods", type: "goods", def: ["garments"] },
  price: { label: "price (coppers)", type: "number", def: 60 },
  per_unit: { label: "per unit (coppers)", type: "number", def: 8 },
  days: { label: "days", type: "number", def: 3 },
  price_mult: { label: "price multiplier", type: "number", step: 0.1, def: 1.5,
                hint: ">1 = NPCs pay/charge more" },
  qty_mult: { label: "quantity multiplier", type: "number", step: 0.1, def: 0.5,
              hint: "<1 = scarcity, >1 = glut/boom" },
  per_player_per_day: { label: "per merchant per day", type: "number", def: 3 },
  closed: { label: "fishery closed?", type: "bool", def: true },
  auction_id: { label: "auction id", type: "text", def: "glowdye-1" },
  licenses: { label: "licenses for sale", type: "number", def: 4 },
  close_day_offset: { label: "closes in (days)", type: "number", def: 2 },
  amount: { label: "coppers per merchant", type: "number", def: 50 },
  player_id: { label: "merchant", type: "player", def: "" },
  "player_id?": { label: "merchant (optional)", type: "player", def: "" },
  divest_fraction: { label: "divest fraction", type: "number", step: 0.1, def: 0.5 },
  fine: { label: "fine (coppers)", type: "number", def: 100 },
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
              <option value="">— choose —</option>
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
            <b>{k.replace(/_/g, " ")}</b>
            <div style={{ fontSize: 12 }}>{v.blurb}</div>
          </div>
        ))}
      </div>
      <div className="panel grow">
        <h3>⚡ {kind.replace(/_/g, " ")}</h3>
        <div className="muted">Interventions are diegetic — students see the Crier's
          fiction, never your hand.</div>
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
          <label className="muted">or schedule for day
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
            {rawMode ? "form" : "raw JSON"}</button>
        </div>
        {preview && <div className="pip-bubble" style={{ marginTop: 10 }}>{preview}</div>}
      </div>
    </div>
  );
}

function Heatmap({ wid }: { wid: string }) {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api.get(`/worlds/${wid}/instructor/heatmap`).then(setData).catch(() => {});
  }, [wid]);
  if (!data) return <div className="panel">Loading…</div>;
  const empty = data.students.every((s: any) =>
    data.los.every((lo: any) => s.scores[lo.id] == null));
  const color = (pct: number | null) =>
    pct == null ? "#eee" : pct > 70 ? "var(--sage)" : pct > 40 ? "#ecc473" : "var(--terracotta)";
  return (
    <div className="panel" style={{ overflowX: "auto" }}>
      <h3>Mastery heatmap</h3>
      {empty && (
        <div className="pip-bubble" style={{ maxWidth: 560, marginBottom: 10 }}>
          No tutor checks answered yet. Checks trigger as students play (and Pip
          nudges them along) — expect the first cells to light up within a day
          or two of real activity. Green = mastered, amber = shaky, red = teach it.
        </div>
      )}
      <table style={{ borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 4 }}>student</th>
            {data.los.map((lo: any) => (
              <th key={lo.id} title={lo.text}
                  style={{ padding: 4, writingMode: "vertical-rl", maxHeight: 120 }}>
                {lo.id}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.students.map((s: any) => (
            <tr key={s.merchant}>
              <td style={{ padding: 4 }}>{s.merchant}</td>
              {data.los.map((lo: any) => {
                const score = s.scores[lo.id];
                const pct = score == null ? null : Math.round(score / 10);
                return (
                  <td key={lo.id} title={`${lo.text}: ${pct ?? "—"}%`}
                      style={{ width: 26, height: 22, background: color(pct),
                               border: "1px solid #fff", textAlign: "center" }}>
                    {pct ?? ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
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
      <div className="muted">Participation + mastery, never wealth.
        {" "}<a href={`/api/worlds/${wid}/instructor/gradebook.csv`}>Export CSV</a></div>
      {noMastery && (
        <div className="pip-bubble" style={{ maxWidth: 560, margin: "8px 0" }}>
          Mastery is 0% across the board because no tutor checks have been
          answered yet — grades here are participation-only for now.
        </div>
      )}
      <table className="book" style={{ marginTop: 8 }}>
        <thead><tr><th style={{ textAlign: "left" }}>merchant</th><th>participation</th>
          <th>mastery</th><th>grade</th><th>LOs</th></tr></thead>
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

function Playbook({ wid }: { wid: string }) {
  const [week, setWeek] = useState<number | "">("");
  const [pb, setPb] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  async function generate() {
    setBusy(true);
    try {
      const q = week === "" ? "" : `?week=${week}`;
      setPb(await api.get(`/worlds/${wid}/instructor/playbook${q}`));
    } catch { /* noop */ }
    setBusy(false);
  }
  return (
    <div className="panel">
      <h3>Lecture playbook</h3>
      <div className="muted" style={{ marginBottom: 6 }}>
        Monday-morning prep from YOUR class's data: what happened, what to teach,
        what to ask. Generated in under a minute.
      </div>
      <div className="row" style={{ alignItems: "center" }}>
        <label>week <input type="number" min={1} max={7} style={{ width: 56 }}
                           value={week}
                           onChange={(e) => setWeek(
                             e.target.value === "" ? "" : +e.target.value)} /></label>
        <button onClick={generate} disabled={busy}>
          {busy ? "Writing…" : "Generate"}</button>
        {pb && <button className="quiet" onClick={() => {
          navigator.clipboard?.writeText(pb.markdown);
        }}>copy markdown</button>}
      </div>
      {pb && (
        <div style={{ background: "#fffdf6", padding: "8px 18px 14px",
                      borderRadius: 12,
                      border: "1px solid var(--parchment-edge)", marginTop: 10 }}>
          <Markdown text={pb.markdown} />
        </div>
      )}
    </div>
  );
}
