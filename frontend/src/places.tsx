/* The market square, your shop, the workshop, and the docks. */
import React, { useCallback, useEffect, useState } from "react";
import { api, getToken, PlayerState } from "./api";
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

  // Live feed: refresh instantly when anyone trades this good (DECISIONS #8).
  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const sock = new WebSocket(
      `${proto}://${location.host}/api/worlds/${wid}/ws?token=${getToken()}`);
    sock.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "day_closed" || msg.good_id === good) load().catch(() => {});
      } catch { /* ignore */ }
    };
    return () => sock.close();
  }, [wid, good, load]);

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
      <div className="panel goods-panel" style={{ flex: "0 1 200px" }}>
        <div className="kicker">Goods</div>
        <div className="goods-items">
          {state.goods.map((g) => (
            <div key={g.id}
                 className={`place-tile ${good === g.id ? "active" : ""}`}
                 style={{ marginBottom: 6, textAlign: "left", padding: "7px 10px",
                          display: "flex", alignItems: "center", gap: 8 }}
                 onClick={() => setGood(g.id)}
                 role="button">
              <GoodIcon good={g.id} />
              <span style={{ fontWeight: good === g.id ? 700 : 400 }}>{g.name}</span>
              {g.aptitude && <span title="your aptitude">⭐</span>}
              {g.license_required && <span title="license required">📜</span>}
              <span style={{ marginLeft: "auto", opacity: 0.8 }}>
                {state.inventory[g.id] || 0}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="col grow market-main">
        <div className="panel">
          <h3><GoodIcon good={good} size={26} /> {good} — price chart</h3>
          {ceiling != null && <div className="heat-bad">⚖️ Price ceiling: {ceiling}</div>}
          {floor != null && <div className="heat-good">⚖️ Price floor: {floor}</div>}
          <Sparkline points={closes} width={560} height={130}
                     refLine={ceiling ?? floor ?? null}
                     refLabel={ceiling != null ? `ceiling ${ceiling}`
                       : floor != null ? `floor ${floor}` : undefined} />
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

      <div className="col market-side" style={{ flex: "0 1 260px" }}>
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
        <img className="scene-banner" src="/assets/places/workshop_scene.png"
             alt="" onError={(e) =>
               (e.target as HTMLImageElement).style.setProperty("display", "none")} />
        <h3>🏭 Your facilities</h3>
        {state.facilities.length === 0 &&
          <div className="muted">No facilities yet. A building works while you sleep —
            that's the whole point of fixed costs.</div>}
        {state.facilities.map((f) => (
          <div key={f.id} className="facility-card">
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <GoodIcon good={f.output} size={34} />
              <div>
                <b>{f.name}</b>
                <div className="muted" style={{ fontSize: 12 }}>
                  tier {f.tier} · makes {f.output}
                  {f.workers > 0 && ` · ${f.workers} workers`}
                  {f.scrubber && " · 🌬️ scrubber"}
                </div>
              </div>
            </div>
            <div className="row" style={{ marginTop: 8, alignItems: "center" }}>
              <button className="quiet" onClick={() =>
                facilityAction(`/worlds/${wid}/facilities/${f.id}/upgrade`)}>
                ⬆ upgrade</button>
              <label className="muted">workers:
                <input type="number" min={0} max={12} defaultValue={f.workers}
                       style={{ width: 56, marginLeft: 4 }}
                       onBlur={(e) => facilityAction(
                         `/worlds/${wid}/facilities/${f.id}/workers`,
                         { workers: +e.target.value })} />
              </label>
              {!f.scrubber && state.world.week >= 6 &&
                <button className="quiet" onClick={() =>
                  facilityAction(`/worlds/${wid}/facilities/${f.id}/scrubber`)}>
                  🌬️ fit scrubber (250)</button>}
            </div>
          </div>
        ))}
        <hr className="divider" />
        <h3>🏗️ Build</h3>
        <div className="muted" style={{ marginBottom: 8 }}>
          120 coppers of fixed cost, working for you every night thereafter.
        </div>
        <div className="build-grid">
          {FACILITIES.filter(([, label]) =>
            unlockedGoods.has(label.split("→ ")[1]?.split(" ")[0] || "")).map(([kind, label]) => {
            const [name, output] = label.split(" → ");
            return (
              <div key={kind} className="build-card" role="button"
                   onClick={() => build(kind)}>
                <GoodIcon good={output.split(" ")[0]} size={34} />
                <div>{name}</div>
                <div className="cost">→ {output} · 120c</div>
              </div>
            );
          })}
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

  const sellable = state.goods.filter((g) => (state.inventory[g.id] || 0) > 0
    || listings.some((l) => l.good_id === g.id));

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
            {state.goods.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name} ({state.inventory[g.id] || 0} held)
              </option>
            ))}
          </select>
          <label>price <input type="number" min={1} value={price} style={{ width: 72 }}
                              onChange={(e) => setPrice(+e.target.value)} /></label>
          <label>stock <input type="number" min={0} value={qty} style={{ width: 64 }}
                              onChange={(e) => setQty(+e.target.value)} /></label>
          <button onClick={list}>Stock shelf</button>
        </div>
        <hr className="divider" />
        {listings.map((l) => (
          <div key={l.good_id}>
            <div className="shelf">
              {Array.from({ length: Math.min(l.qty, 9) }, (_, i) => (
                <GoodIcon key={i} good={l.good_id} size={30} />
              ))}
              {l.qty > 9 && <span style={{ color: "var(--parchment)",
                fontFamily: "var(--font-display)" }}>+{l.qty - 9}</span>}
              {l.qty === 0 && <span style={{ color: "var(--parchment)", opacity: 0.7,
                fontStyle: "italic", fontSize: 13 }}>sold out — restock?</span>}
              <span className="price-tag">{l.price}c</span>
            </div>
            <div className="muted" style={{ marginTop: -4, marginBottom: 8 }}>
              <b>{l.good_id}</b> · {l.qty} on shelf · {l.sold_total} sold all-time
            </div>
          </div>
        ))}
        {listings.length === 0 && (
          <div style={{ textAlign: "center", padding: "16px 0" }}>
            <div className="shelf" style={{ justifyContent: "center" }}>
              <span style={{ color: "var(--parchment)", opacity: 0.7,
                             fontStyle: "italic" }}>bare boards…</span>
            </div>
            <div className="muted">Empty shelves, merchant. Stock something —
              {sellable.length > 0 && <> you're holding {sellable.slice(0, 3)
                .map((g) => g.name).join(", ")}.</>}
            </div>
          </div>
        )}
      </div>
      <div className="panel" style={{ flex: "0 1 300px" }}>
        <h3>✨ Your finery</h3>
        <div className="kicker">cosmetics</div>
        {state.cosmetics.length === 0 &&
          <div className="muted">None yet — earn prestige, or buy swagger at the
            Luxury Boutique in the Guild Hall.</div>}
        <div className="row" style={{ gap: 8 }}>
          {state.cosmetics.map((c) => (
            <div key={c} style={{ textAlign: "center", width: 76 }}>
              <Asset slot={`cosmetics/${c}`} glyph="🎀" size={56} alt={c} />
              <div className="muted" style={{ fontSize: 11 }}>{c.replace(/_/g, " ")}</div>
            </div>
          ))}
        </div>
        <div className="kicker" style={{ marginTop: 10 }}>achievements</div>
        {state.achievements.length === 0 &&
          <div className="muted">none yet — go achieve something</div>}
        {state.achievements.map((a) => <span key={a} className="tag">🏅 {a}</span>)}
      </div>
    </div>
  );
}

const TROPHY_SLUGS: Record<string, string> = {
  "Smug Trout": "smug_trout",
  "Old Whiskerjaw": "old_whiskerjaw",
  "Gilded Leviathan": "gilded_leviathan",
};

export function Docks({ state, wid, notify, refresh }: {
  state: PlayerState; wid: string; notify: Notify; refresh: () => void;
}) {
  const [result, setResult] = useState<any>(null);
  const [casting, setCasting] = useState(false);
  const [catches, setCatches] = useState<any[]>([]);

  async function cast() {
    setCasting(true);
    setResult(null);
    try {
      // a beat of suspense — the timing-gauge feel without trusting the client
      await new Promise((r) => setTimeout(r, 1100));
      const out = await api.post(`/worlds/${wid}/fishing/cast`);
      setResult(out);
      setCatches((c) => [out, ...c].slice(0, 6));
      if (out.trophy) notify(`🏆 ${out.trophy}!`);
      else if (out.qty) notify(`Caught ${out.qty} fish!`);
      else notify("Nothing biting…", true);
      refresh();
    } catch (e: any) { notify(e.message, true); }
    setCasting(false);
  }

  const quota = state.world.fishing_rules?.quota;
  const closed = state.world.fishing_rules?.closed;
  const myTrophies = state.achievements
    .filter((a) => a.startsWith("trophy:"))
    .map((a) => a.slice(7));

  return (
    <div className="row">
      <div className="panel grow" style={{ maxWidth: 640 }}>
        <h3>🎣 The Docks</h3>
        <div className="docks-scene">
          <img src="/assets/places/docks_scene.png" alt="The docks at dusk" />
          {casting && <span className="ripple" />}
        </div>
        <div style={{ textAlign: "center", marginTop: 12 }}>
          {closed && <div className="heat-bad" style={{ marginBottom: 6 }}>
            The fishery is CLOSED by royal order.</div>}
          {quota != null && !closed &&
            <div className="heat-bad" style={{ marginBottom: 6 }}>
              Royal quota: {quota} fish per merchant per day.</div>}
          <button onClick={cast} disabled={casting || !!closed}
                  style={{ fontSize: 17, padding: "12px 34px" }}>
            {casting ? "The line is out…" : "Cast (3 effort)"}
          </button>
          {result && (
            <div style={{ marginTop: 10 }}>
              {result.qty > 0
                ? <div style={{ display: "flex", gap: 8, justifyContent: "center",
                                alignItems: "center" }}>
                    {Array.from({ length: result.qty }, (_, i) =>
                      <GoodIcon key={i} good="fish" size={30} />)}
                    <b>{result.qty} fish</b>
                    <span className="muted">({(result.weight / 10).toFixed(0)}dg)</span>
                  </div>
                : <span className="muted">The hook came back bare.</span>}
              {result.trophy && (
                <div style={{ marginTop: 8 }}>
                  <Asset slot={`trophies/${TROPHY_SLUGS[result.trophy] || ""}`}
                         glyph="🏆" size={84} alt={result.trophy} />
                  <div style={{ fontFamily: "var(--font-display)", fontSize: 17 }}>
                    🏆 {result.trophy}!</div>
                </div>
              )}
              <div className="muted" style={{ fontStyle: "italic", marginTop: 6 }}>
                {result.stock_hint}</div>
            </div>
          )}
          <div className="muted" style={{ marginTop: 12 }}>
            The fishery belongs to everyone. Which is to say: to no one.
          </div>
        </div>
      </div>

      <div className="col" style={{ flex: "0 1 300px" }}>
        <div className="panel">
          <h3>🏆 Trophy wall</h3>
          <div className="trophy-wall">
            {Object.entries(TROPHY_SLUGS).map(([name, slug]) => (
              <div key={name}
                   className={`trophy-slot ${myTrophies.includes(name) ? "" : "empty"}`}
                   title={myTrophies.includes(name) ? name : `${name} — uncaught`}>
                <Asset slot={`trophies/${slug}`} glyph="🐟" size={64} alt={name} />
                <div>{myTrophies.includes(name) ? name : "???"}</div>
              </div>
            ))}
          </div>
          <div className="muted" style={{ marginTop: 8 }}>
            Hooked in {state.inventory.fish || 0} fish · sell them in the Market
            before they get philosophical.
          </div>
        </div>
        {catches.length > 0 && (
          <div className="panel">
            <h3>Today's casts</h3>
            {catches.map((c, i) => (
              <div key={i} className="muted" style={{ fontSize: 13 }}>
                {c.qty > 0 ? `🐟 ${c.qty} (${(c.weight / 10).toFixed(0)}dg)` : "— bare hook"}
                {c.trophy ? ` · 🏆 ${c.trophy}` : ""}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
