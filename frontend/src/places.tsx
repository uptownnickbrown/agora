/* The market square, your shop, the workshop, and the docks. */
import React, { useCallback, useEffect, useState } from "react";
import { api, PlayerState } from "./api";
import { Asset, Coins, Confetti, GoodIcon, Sparkline } from "./ui";

type Notify = (msg: string, error?: boolean) => void;

export function MarketSquare({ state, wid, notify, refresh }: {
  state: PlayerState; wid: string; notify: Notify; refresh: () => void;
}) {
  const [good, setGood] = useState(state.goods[0]?.id || "grain");
  const [book, setBook] = useState<{ bids: [number, number][]; asks: [number, number][] }>();
  const [history, setHistory] = useState<any[]>([]);
  const [tape, setTape] = useState<any[]>([]);
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [qty, setQty] = useState(5);
  const [price, setPrice] = useState<number | "">("");
  const [celebrate, setCelebrate] = useState(false);

  const load = useCallback(async () => {
    const [b, h, t] = await Promise.all([
      api.get(`/worlds/${wid}/markets/${good}/book`),
      api.get(`/worlds/${wid}/markets/${good}/history`),
      api.get(`/worlds/${wid}/markets/${good}/tape`),
    ]);
    setBook(b); setHistory(h); setTape(t);
  }, [wid, good]);

  useEffect(() => { load().catch(() => {}); }, [load]);
  useEffect(() => {
    const id = setInterval(() => load().catch(() => {}), 8000);
    return () => clearInterval(id);
  }, [load]);

  const ceiling = state.world.market_rules?.ceilings?.[good];
  const floor = state.world.market_rules?.floors?.[good];
  const closes = history.map((h) => h.close);
  const lastClose = [...closes].reverse().find((c) => c != null);

  async function place() {
    try {
      const result = await api.post(`/worlds/${wid}/orders`, {
        good_id: good, side, qty,
        price: price === "" ? null : price, ttl_days: 2,
      });
      if (result.status === "suppressed") {
        notify("The Crown forbids that price. Your order was withdrawn.", true);
      } else if (result.trades.length) {
        const total = result.trades.reduce((s: number, t: any) => s + t.qty, 0);
        setCelebrate(true);
        setTimeout(() => setCelebrate(false), 1000);
        notify(`${side === "buy" ? "Bought" : "Sold"} ${total} ${good}!`);
      } else {
        notify("Order posted to the book.");
      }
      await load(); refresh();
    } catch (e: any) { notify(e.message, true); }
  }

  async function cancel(orderId: string) {
    try {
      await api.del(`/worlds/${wid}/orders/${orderId}`);
      notify("Order withdrawn."); await load(); refresh();
    } catch (e: any) { notify(e.message, true); }
  }

  const myOrders = state.open_orders.filter((o) => o.good_id === good);

  return (
    <div className="row">
      <div className="panel" style={{ flex: "0 1 200px" }}>
        <div className="kicker">Goods</div>
        {state.goods.map((g) => (
          <div key={g.id}
               className="place-tile"
               style={{ marginBottom: 6, textAlign: "left", padding: "7px 10px",
                        display: "flex", alignItems: "center", gap: 8 }}
               onClick={() => setGood(g.id)}
               role="button">
            <GoodIcon good={g.id} />
            <span style={{ fontWeight: good === g.id ? 700 : 400 }}>{g.name}</span>
            {g.aptitude && <span title="your aptitude">⭐</span>}
            {g.license_required && <span title="license required">📜</span>}
            <span style={{ marginLeft: "auto" }} className="muted">
              {state.inventory[g.id] || 0}
            </span>
          </div>
        ))}
      </div>

      <div className="col grow">
        <div className="panel">
          <h3><GoodIcon good={good} size={26} /> {good} — price chart</h3>
          {ceiling != null && <div className="heat-bad">⚖️ Price ceiling: {ceiling}</div>}
          {floor != null && <div className="heat-good">⚖️ Price floor: {floor}</div>}
          <Sparkline points={closes} width={420} height={110} />
          <div className="muted">
            last close: <b>{lastClose ?? "—"}</b>
            {history.length > 0 && history[history.length - 1].unfilled_demand > 0 &&
              <> · unfilled demand yesterday: <b className="heat-bad">
                {history[history.length - 1].unfilled_demand}</b></>}
          </div>
        </div>

        <div className="panel">
          <h3>Place an order {celebrate && <Confetti />}</h3>
          <div className="row" style={{ alignItems: "center" }}>
            <button className={side === "buy" ? "buy" : "quiet"}
                    onClick={() => setSide("buy")}>Bid</button>
            <button className={side === "sell" ? "sell" : "quiet"}
                    onClick={() => setSide("sell")}>Ask</button>
            <label>qty <input type="number" min={1} value={qty} style={{ width: 70 }}
                              onChange={(e) => setQty(+e.target.value)} /></label>
            <label>price <input type="number" min={1} placeholder="market"
                                value={price} style={{ width: 84 }}
                                onChange={(e) =>
                                  setPrice(e.target.value === "" ? "" : +e.target.value)} /></label>
            <button className={side} onClick={place}>
              {side === "buy" ? "Buy" : "Sell"} {qty} {good}
            </button>
          </div>
          <div className="muted">Leave price empty for a market order (fills now or not at all).</div>
          {myOrders.length > 0 && <>
            <hr className="divider" />
            <div className="kicker">your open orders</div>
            {myOrders.map((o) => (
              <div key={o.id} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span className={o.side === "buy" ? "heat-good" : "heat-bad"}>{o.side}</span>
                <span>{o.remaining}/{o.qty} @ {o.price}</span>
                <span className="muted">expires day {o.expires_day}</span>
                <button className="quiet" style={{ padding: "2px 10px" }}
                        onClick={() => cancel(o.id)}>withdraw</button>
              </div>
            ))}
          </>}
        </div>
      </div>

      <div className="col" style={{ flex: "0 1 260px" }}>
        <div className="panel">
          <h3>Order book</h3>
          <table className="book">
            <thead><tr><th>price</th><th>qty</th></tr></thead>
            <tbody>
              {(book?.asks || []).slice().reverse().map(([p, q]) => (
                <tr key={`a${p}`} className="ask-row"><td>{p}</td><td>{q}</td></tr>
              ))}
              <tr><td colSpan={2} style={{ textAlign: "center" }} className="muted">— spread —</td></tr>
              {(book?.bids || []).map(([p, q]) => (
                <tr key={`b${p}`} className="bid-row"><td>{p}</td><td>{q}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="panel">
          <h3>The tape</h3>
          <div className="muted" style={{ marginBottom: 4 }}>
            (anonymous — read the Crier for names)
          </div>
          {tape.slice(0, 10).map((t, i) => (
            <div key={i} style={{ fontSize: 13 }}>
              {t.qty} @ <b>{t.price}</b> <span className="muted">day {t.day}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function Workshop({ state, wid, notify, refresh }: {
  state: PlayerState; wid: string; notify: Notify; refresh: () => void;
}) {
  const [gatherGood, setGatherGood] = useState(state.player.aptitude || "grain");
  const [effort, setEffort] = useState(5);
  const gatherables = state.goods.filter((g) => g.gatherable);

  async function gather() {
    try {
      const out = await api.post(`/worlds/${wid}/gather`, { good_id: gatherGood, effort });
      notify(`Gathered ${out.gathered} ${out.good_id}.`); refresh();
    } catch (e: any) { notify(e.message, true); }
  }

  async function craft(output: string) {
    try {
      const out = await api.post(`/worlds/${wid}/craft`, { output, runs: 1 });
      notify(`Crafted ${out.crafted} ${out.good_id}.`); refresh();
    } catch (e: any) { notify(e.message, true); }
  }

  async function build(kind: string) {
    try {
      await api.post(`/worlds/${wid}/facilities`, { kind });
      notify("Construction complete!"); refresh();
    } catch (e: any) { notify(e.message, true); }
  }

  async function facilityAction(path: string, body?: any) {
    try { await api.post(path, body); notify("Done."); refresh(); }
    catch (e: any) { notify(e.message, true); }
  }

  const RECIPES: [string, string][] = [
    ["flour", "2 grain"], ["lumber", "2 wood"], ["cloth", "2 wool"],
    ["bread", "2 flour"], ["garments", "2 cloth"], ["medicine", "2 herbs"],
    ["tapestries", "3 cloth"], ["iron", "2 ore"], ["tools", "1 iron + 1 lumber"],
    ["glowdye", "2 herbs + 1 ore 📜"],
  ];
  const FACILITIES: [string, string, number][] = [
    ["farm", "Farm Plot → grain", 120], ["pasture", "Pasture → wool", 120],
    ["woodlot", "Woodlot → wood", 120], ["herb_garden", "Herb Garden → herbs", 120],
    ["mine", "Mine → ore", 120], ["mill", "Mill → flour", 120],
    ["loom", "Loom → cloth", 120], ["smelter", "Smelter → iron", 120],
    ["bakery", "Bakery → bread", 120], ["tailor", "Tailor → garments", 120],
    ["apothecary", "Apothecary → medicine", 120], ["atelier", "Atelier → tapestries", 120],
    ["smithy", "Smithy → tools", 120], ["dyeworks", "Dyeworks → glowdye 📜", 120],
  ];
  const unlockedGoods = new Set(state.goods.map((g) => g.id));

  return (
    <div className="row">
      <div className="panel grow">
        <h3>🧺 Gathering</h3>
        <div className="row" style={{ alignItems: "center" }}>
          <select value={gatherGood} onChange={(e) => setGatherGood(e.target.value)}>
            {gatherables.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}{g.aptitude ? " ⭐ (3x)" : ""}
              </option>
            ))}
          </select>
          <label>effort <input type="number" min={1} max={40} value={effort}
                               style={{ width: 64 }}
                               onChange={(e) => setEffort(+e.target.value)} /></label>
          <button onClick={gather}>Gather</button>
        </div>
        <div className="muted">Your aptitude ⭐ yields triple. Effort is the one thing
          you can never buy more of today — spend it like it matters, because it does.</div>
        <hr className="divider" />
        <h3>🔨 Hand-crafting</h3>
        {RECIPES.filter(([out]) => unlockedGoods.has(out)).map(([out, needs]) => (
          <div key={out} style={{ display: "flex", gap: 8, alignItems: "center",
                                  marginBottom: 5 }}>
            <GoodIcon good={out} />
            <span style={{ width: 100 }}>{out}</span>
            <span className="muted" style={{ flex: 1 }}>{needs}</span>
            <button className="wood" style={{ padding: "4px 12px" }}
                    onClick={() => craft(out)}>craft</button>
          </div>
        ))}
      </div>

      <div className="panel grow">
        <h3>🏭 Your facilities</h3>
        {state.facilities.length === 0 &&
          <div className="muted">No facilities yet. A building works while you sleep —
            that's the whole point of fixed costs.</div>}
        {state.facilities.map((f) => (
          <div key={f.id} className="panel" style={{ marginBottom: 8, padding: 10 }}>
            <b>{f.name}</b> (tier {f.tier}) → {f.output}
            {f.scrubber && " 🌬️ scrubber"}
            <div className="row" style={{ marginTop: 6 }}>
              <button className="quiet" onClick={() =>
                facilityAction(`/worlds/${wid}/facilities/${f.id}/upgrade`)}>
                upgrade (wk4+)</button>
              <label className="muted">workers (wk4+):
                <input type="number" min={0} max={12} defaultValue={f.workers}
                       style={{ width: 56, marginLeft: 4 }}
                       onBlur={(e) => facilityAction(
                         `/worlds/${wid}/facilities/${f.id}/workers`,
                         { workers: +e.target.value })} />
              </label>
              {!f.scrubber && state.world.week >= 6 &&
                <button className="quiet" onClick={() =>
                  facilityAction(`/worlds/${wid}/facilities/${f.id}/scrubber`)}>
                  fit scrubber (250)</button>}
            </div>
          </div>
        ))}
        <hr className="divider" />
        <h3>🏗️ Build (cost 120, week-gated)</h3>
        <div className="row">
          {FACILITIES.filter(([, label]) =>
            unlockedGoods.has(label.split("→ ")[1]?.split(" ")[0] || "")).map(([kind, label]) => (
            <button key={kind} className="wood" style={{ flex: "1 1 150px" }}
                    onClick={() => build(kind)}>{label}</button>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ShopScreen({ state, wid, notify, refresh }: {
  state: PlayerState; wid: string; notify: Notify; refresh: () => void;
}) {
  const [listings, setListings] = useState<any[]>([]);
  const [good, setGood] = useState("bread");
  const [price, setPrice] = useState(50);
  const [qty, setQty] = useState(5);

  const load = useCallback(
    () => api.get(`/worlds/${wid}/shop`).then(setListings).catch(() => {}),
    [wid]);
  useEffect(() => { load(); }, [load]);

  async function list() {
    try {
      await api.post(`/worlds/${wid}/shop`, { good_id: good, price, qty });
      notify("Shelf stocked. Passersby will judge your prices overnight.");
      await load(); refresh();
    } catch (e: any) { notify(e.message, true); }
  }

  return (
    <div className="row">
      <div className="panel grow">
        <h3>🏪 Your shop window</h3>
        <div className="muted" style={{ marginBottom: 8 }}>
          Posted prices, browsing customers. Every night the town samples your
          prices — your own little demand curve, in the wild.
        </div>
        <div className="row" style={{ alignItems: "center" }}>
          <select value={good} onChange={(e) => setGood(e.target.value)}>
            {state.goods.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
          <label>price <input type="number" min={1} value={price} style={{ width: 72 }}
                              onChange={(e) => setPrice(+e.target.value)} /></label>
          <label>stock <input type="number" min={0} value={qty} style={{ width: 64 }}
                              onChange={(e) => setQty(+e.target.value)} /></label>
          <button onClick={list}>Stock shelf</button>
        </div>
        <hr className="divider" />
        {listings.map((l) => (
          <div key={l.good_id} style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <GoodIcon good={l.good_id} />
            <b>{l.good_id}</b>
            <span>@ {l.price}</span>
            <span className="muted">{l.qty} on shelf · {l.sold_total} sold all-time</span>
          </div>
        ))}
        {listings.length === 0 && <div className="muted">Empty shelves, merchant.</div>}
      </div>
      <div className="panel" style={{ flex: "0 1 280px" }}>
        <h3>Cosmetics</h3>
        <div className="kicker">earned</div>
        {state.cosmetics.length === 0 && <div className="muted">none yet — go achieve something</div>}
        {state.cosmetics.map((c) => <span key={c} className="tag">{c}</span>)}
        <div className="kicker" style={{ marginTop: 8 }}>achievements</div>
        {state.achievements.map((a) => <span key={a} className="tag">🏅 {a}</span>)}
      </div>
    </div>
  );
}

export function Docks({ state, wid, notify, refresh }: {
  state: PlayerState; wid: string; notify: Notify; refresh: () => void;
}) {
  const [result, setResult] = useState<any>(null);
  const [casting, setCasting] = useState(false);

  async function cast() {
    setCasting(true);
    try {
      // a beat of suspense — the timing-gauge feel without trusting the client
      await new Promise((r) => setTimeout(r, 700));
      const out = await api.post(`/worlds/${wid}/fishing/cast`);
      setResult(out);
      if (out.trophy) notify(`🏆 ${out.trophy}!`);
      else if (out.qty) notify(`Caught ${out.qty} fish!`);
      else notify("Nothing biting…", true);
      refresh();
    } catch (e: any) { notify(e.message, true); }
    setCasting(false);
  }

  const quota = state.world.fishing_rules?.quota;
  const closed = state.world.fishing_rules?.closed;

  return (
    <div className="row">
      <div className="panel grow" style={{ textAlign: "center" }}>
        <h3>🎣 The Docks</h3>
        <div style={{ fontSize: 60, margin: "8px 0" }}>
          <Asset slot="places/docks_scene" glyph={casting ? "🌊" : "⛵"} size={120} />
        </div>
        {closed && <div className="heat-bad">The fishery is CLOSED by royal order.</div>}
        {quota != null && !closed &&
          <div className="heat-bad">Royal quota: {quota} fish per merchant per day.</div>}
        <button onClick={cast} disabled={casting || !!closed}
                style={{ fontSize: 17, padding: "12px 30px" }}>
          {casting ? "The line is out…" : "Cast (3 effort)"}
        </button>
        {result && (
          <div style={{ marginTop: 10 }}>
            {result.qty > 0
              ? <>Caught <b>{result.qty}</b> fish ({(result.weight / 10).toFixed(0)}dg)
                  {result.trophy && <div style={{ fontSize: 18 }}>🏆 <b>{result.trophy}</b></div>}</>
              : <span className="muted">The hook came back bare.</span>}
            <div className="muted" style={{ fontStyle: "italic" }}>{result.stock_hint}</div>
          </div>
        )}
        <div className="muted" style={{ marginTop: 12 }}>
          The fishery belongs to everyone. Which is to say: to no one.
        </div>
      </div>
    </div>
  );
}
