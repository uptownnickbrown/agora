/* The instructor's backstage: dashboard, feed, interventions, pedagogy. */
import React, { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { Sparkline } from "./ui";

type Notify = (msg: string, error?: boolean) => void;

export function InstructorScreen({ wid, notify }: { wid: string; notify: Notify }) {
  const [tab, setTab] = useState("dashboard");
  const tabs = ["dashboard", "feed", "interventions", "heatmap", "gradebook", "playbook"];
  return (
    <div className="col">
      <div className="places">
        {tabs.map((t) => (
          <div key={t} className={`place-tile ${tab === t ? "active" : ""}`}
               onClick={() => setTab(t)} role="button">{t}</div>
        ))}
      </div>
      {tab === "dashboard" && <Dashboard wid={wid} notify={notify} />}
      {tab === "feed" && <Feed wid={wid} />}
      {tab === "interventions" && <Interventions wid={wid} notify={notify} />}
      {tab === "heatmap" && <Heatmap wid={wid} />}
      {tab === "gradebook" && <Gradebook wid={wid} />}
      {tab === "playbook" && <Playbook wid={wid} />}
    </div>
  );
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
            <span className="plaque">join code: <b>{w.join_code}</b></span>
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
          <div className="muted" style={{ marginTop: 6 }}>
            Active market rules: {JSON.stringify(w.market_rules)}
          </div>
        </div>
        <div className="panel grow">
          <h3>Vitals over time</h3>
          <div className="kicker">trade volume</div>
          <Sparkline points={data.vitals.map((v: any) => v.volume)} width={340} height={60} />
          <div className="kicker">wealth gini (bp)</div>
          <Sparkline points={data.vitals.map((v: any) => v.gini_bp)} width={340} height={60}
                     stroke="#c4633e" />
          <div className="kicker">fish stock</div>
          <Sparkline points={data.vitals.map((v: any) => v.fish_stock)} width={340}
                     height={60} stroke="#4a7a96" />
        </div>
      </div>
      <div className="row">
        <div className="panel grow">
          <h3>Price charts</h3>
          <div className="row">
            {Object.entries(data.charts).slice(0, 8).map(([good, pts]: [string, any]) => (
              <div key={good} style={{ flex: "1 1 200px" }}>
                <div className="kicker">{good}</div>
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
              <span className="muted">{p.coins}c</span>
              <span className={w.day - p.last_active_day >= 5 ? "heat-bad" : "muted"}>
                day {p.last_active_day}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Feed({ wid }: { wid: string }) {
  const [feed, setFeed] = useState<any>(null);
  useEffect(() => {
    api.get(`/worlds/${wid}/instructor/feed`).then(setFeed).catch(() => {});
  }, [wid]);
  if (!feed) return <div className="panel">Listening…</div>;
  const sevColor: any = { alert: "var(--rose)", notable: "var(--terracotta)", info: "var(--ink-soft)" };
  return (
    <div className="row">
      <div className="panel grow">
        <h3>Detected moments</h3>
        {feed.moments.length === 0 && <div className="muted">Nothing yet. Give them time
          — someone always corners something.</div>}
        {feed.moments.map((m: any) => (
          <div key={m.id} style={{ borderLeft: `4px solid ${sevColor[m.severity]}`,
                                   padding: "6px 10px", marginBottom: 8,
                                   background: "rgba(0,0,0,0.025)" }}>
            <div className="kicker">day {m.day} · {m.kind} · {m.severity}</div>
            <div style={{ fontSize: 14 }}>{m.summary}</div>
          </div>
        ))}
      </div>
      <div className="panel" style={{ flex: "0 1 340px" }}>
        <h3>Your interventions</h3>
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

function Interventions({ wid, notify }: { wid: string; notify: Notify }) {
  const [catalog, setCatalog] = useState<Record<string, any>>({});
  const [kind, setKind] = useState("supply_shock");
  const [params, setParams] = useState('{"good": "grain", "price_mult": 1.6, "qty_mult": 0.45, "days": 5}');
  const [scheduleDay, setScheduleDay] = useState<number | "">("");
  const [preview, setPreview] = useState("");

  useEffect(() => {
    api.get(`/worlds/${wid}/instructor/interventions`).then(setCatalog).catch(() => {});
  }, [wid]);

  const EXAMPLES: Record<string, string> = {
    supply_shock: '{"good": "grain", "price_mult": 1.6, "qty_mult": 0.45, "days": 5}',
    demand_shock: '{"goods": ["garments", "bread"], "price_mult": 1.7, "qty_mult": 1.8, "days": 3}',
    price_ceiling: '{"good": "bread", "price": 60}',
    repeal_ceiling: '{"good": "bread"}',
    price_floor: '{"good": "wool", "price": 40}',
    repeal_floor: '{"good": "wool"}',
    tax: '{"good": "garments", "per_unit": 8}',
    subsidy: '{"good": "medicine", "per_unit": 10}',
    smog_tax: '{"per_unit": 3}',
    fishing_quota: '{"per_player_per_day": 3}',
    fishery_season: '{"closed": true}',
    license_auction: '{"good": "glowdye", "auction_id": "glowdye-1", "licenses": 4, "close_day_offset": 2}',
    stimulus: '{"amount": 50}',
  };

  async function run(schedule: boolean) {
    let parsed: any;
    try { parsed = JSON.parse(params); }
    catch { notify("Parameters must be valid JSON", true); return; }
    try {
      const body: any = { kind, params: parsed };
      if (schedule && scheduleDay !== "") body.schedule_day = scheduleDay;
      const out = await api.post(`/worlds/${wid}/instructor/interventions`, body);
      notify(out.scheduled ? `Scheduled for day ${scheduleDay}.` : `Done: ${out.crier}`);
    } catch (e: any) { notify(e.message, true); }
  }

  async function doPreview() {
    let parsed: any = {};
    try { parsed = JSON.parse(params); } catch { /* preview anyway */ }
    const out = await api.post(`/worlds/${wid}/instructor/interventions/preview`,
                               { kind, params: parsed });
    setPreview(out.preview);
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
               onClick={() => { setKind(k); setParams(EXAMPLES[k] || "{}"); setPreview(""); }}
               role="button">
            <b>{k}</b>
            <div style={{ fontSize: 12 }}>{v.blurb}</div>
          </div>
        ))}
      </div>
      <div className="panel grow">
        <h3>⚡ {kind}</h3>
        <div className="muted">Interventions are diegetic — students see the Crier's
          fiction, never your hand.</div>
        <textarea rows={4} style={{ width: "100%", marginTop: 8 }}
                  value={params} onChange={(e) => setParams(e.target.value)} />
        <div className="row" style={{ alignItems: "center", marginTop: 8 }}>
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
  const color = (pct: number | null) =>
    pct == null ? "#eee" : pct > 70 ? "var(--sage)" : pct > 40 ? "#ecc473" : "var(--terracotta)";
  return (
    <div className="panel" style={{ overflowX: "auto" }}>
      <h3>Mastery heatmap</h3>
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
  return (
    <div className="panel">
      <h3>Gradebook</h3>
      <div className="muted">Participation + mastery, never wealth.
        {" "}<a href={`/api/worlds/${wid}/instructor/gradebook.csv`}>Export CSV</a></div>
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
        <pre style={{ whiteSpace: "pre-wrap", fontFamily: "var(--font-body)",
                      background: "#fffdf6", padding: 14, borderRadius: 8,
                      border: "1px solid var(--parchment-edge)", marginTop: 10 }}>
          {pb.markdown}
        </pre>
      )}
    </div>
  );
}
