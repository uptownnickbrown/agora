/* The market square, your shop, the workshop, and the docks. */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { api, getToken, PlayerState } from "./api";
import { Asset, Confetti, GoodIcon, Sparkline } from "./ui";

type Notify = (msg: string, error?: boolean) => void;

/* -- the caravan visitor: one haggle a day ------------------------------------- */

function VisitorCard({ wid, notify, refresh }: {
  wid: string; notify: Notify; refresh: () => void;
}) {
  const [deal, setDeal] = useState<any>(null);
  const [price, setPrice] = useState<number | "">("");
  const [flavor, setFlavor] = useState("");
  const [closing, setClosing] = useState<any>(null); // accepted summary
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    () => api.get(`/worlds/${wid}/haggle`).then(setDeal).catch(() => {}), [wid]);
  useEffect(() => { load(); }, [load]);

  if (!deal) return null;

  const buying = deal.side === "npc_buys";
  const total = price === "" ? null : price * deal.qty;

  async function quote() {
    if (price === "" || busy) return;
    setBusy(true);
    try {
      const out = await api.post(`/worlds/${wid}/haggle/offer`, { price });
      if (out.result === "accepted") {
        setClosing(out);
        setFlavor("");
        notify(buying ? `Deal! Sold ${deal.qty} ${deal.good} at ${out.price}c each.`
                      : `Deal! Bought ${deal.qty} ${deal.good} at ${out.price}c each.`);
        refresh();
      } else {
        setFlavor(out.flavor);
        if (out.result === "walked") {
          notify("They've had enough. The caravan moves on at dusk.", true);
        }
      }
      await load();
    } catch (e: any) { notify(e.message, true); }
    setBusy(false);
  }

  async function walk() {
    try {
      await api.post(`/worlds/${wid}/haggle/walk`);
      await load();
    } catch (e: any) { notify(e.message, true); }
  }

  const done = deal.state !== "open";

  return (
    <div className="visitor-card">
      <div className="portrait">
        <Asset slot={`npc/caravan_${deal.portrait}`} glyph="🧳" size={70}
               alt={deal.visitor} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
          <b style={{ fontFamily: "var(--font-display)", fontSize: 15.5 }}>
            {deal.visitor}</b>
          <span className="kicker">today's visitor</span>
          {!done && (
            <span style={{ marginLeft: "auto", display: "flex", gap: 4,
                           alignItems: "center" }}
                  title="Offers before they walk away">
              {Array.from({ length: 3 }, (_, i) => (
                <span key={i} className={`offer-dot ${
                  i < deal.offers_left ? "" : "spent"}`} />
              ))}
            </span>
          )}
        </div>

        {!done && (
          <>
            <div className="visitor-line">
              {buying
                ? <>"I'll take <b>{deal.qty} {deal.good}</b> off your hands,
                    if the price is fair. Name it, per unit."</>
                : <>"I've got <b>{deal.qty} {deal.good}</b> to part with.
                    What'll you give me, per unit?"</>}
            </div>
            {flavor && <div className="muted" style={{ fontStyle: "italic",
                                                       marginBottom: 6 }}>{flavor}</div>}
            <div className="row" style={{ alignItems: "center", gap: 8 }}>
              <input type="number" min={1} value={price} placeholder="price"
                     style={{ width: 90 }}
                     onChange={(e) => setPrice(e.target.value === "" ? "" : +e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && quote()} />
              <button onClick={quote} disabled={price === "" || busy}>Quote</button>
              {total != null && (
                <span className="muted">
                  {deal.qty} × {price}c = <b>{total.toLocaleString()}c</b>
                  {buying ? " to you" : " from you"}
                </span>
              )}
              <button className="quiet" style={{ marginLeft: "auto" }} onClick={walk}>
                Wave them off</button>
            </div>
          </>
        )}

        {done && (
          <div style={{ fontSize: 13.5 }}>
            {deal.state === "accepted" && (
              <>
                Deal struck: {deal.qty} {deal.good} at <b>{deal.accepted_price}c</b> each.
                Their true limit was <b>{deal.reservation}c</b>
                {closing?.left_on_table === 0 || deal.accepted_price === deal.reservation
                  ? <> — you took every last copper of the surplus.</>
                  : <> — you left {Math.abs(deal.reservation - deal.accepted_price) * deal.qty}c
                      on the table.</>}
              </>
            )}
            {deal.state === "walked" && (
              <>They walked. Their true limit was <b>{deal.reservation}c</b> per unit.
                A caravan returns tomorrow; caravans always do.</>
            )}
            {deal.state === "declined" && (
              <>You waved them off. Their limit was <b>{deal.reservation}c</b> —
                tomorrow brings another wagon.</>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

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
    <>
      <VisitorCard wid={wid} notify={notify} refresh={refresh} />
      <div className="panel goods-panel" style={{ padding: "10px 12px",
                                                  marginBottom: 16 }}>
        <div className="goods-items">
          {state.goods.map((g) => (
            <div key={g.id}
                 className={`place-tile goods-chip ${good === g.id ? "active" : ""}`}
                 onClick={() => setGood(g.id)}
                 role="button"
                 title={`${g.name}${g.aptitude ? " — your specialty" : ""}${
                   g.license_required ? " — license required" : ""}`}>
              <GoodIcon good={g.id} size={22} />
              <span style={{ fontWeight: good === g.id ? 700 : 500 }}>{g.name}</span>
              {g.aptitude && <Asset slot="ui/icon_star" glyph="⭐" size={12}
                                    alt="your specialty" />}
              {g.license_required && <Asset slot="ui/icon_license" glyph="📜"
                                            size={12} alt="license required" />}
              {(state.inventory[g.id] || 0) > 0 &&
                <span className="goods-qty">{state.inventory[g.id]}</span>}
            </div>
          ))}
        </div>
      </div>
      <div className="row">
        <div className="col grow market-main">
          <div className="panel">
            <h3><GoodIcon good={good} size={26} />
              {" "}{good.charAt(0).toUpperCase() + good.slice(1)} — price chart</h3>
            {ceiling != null && <div className="heat-bad">
              <Asset slot="ui/icon_scale" glyph="⚖️" size={15} /> Price ceiling: {ceiling}</div>}
            {floor != null && <div className="heat-good">
              <Asset slot="ui/icon_scale" glyph="⚖️" size={15} /> Price floor: {floor}</div>}
            <Sparkline points={closes} width={560} height={130}
                       refLine={ceiling ?? floor ?? null}
                       refLabel={ceiling != null ? `ceiling ${ceiling}`
                         : floor != null ? `floor ${floor}` : undefined} />
            <div className="muted">
              Last close: <b>{lastClose ?? "—"}</b>
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
                          onClick={() => cancel(o.id)}>Withdraw</button>
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
    </>
  );
}

export function Workshop({ state, wid, notify, refresh }: {
  state: PlayerState; wid: string; notify: Notify; refresh: () => void;
}) {
  const [gatherGood, setGatherGood] = useState(state.player.aptitude || "grain");
  const [effort, setEffort] = useState(5);
  const gatherables = state.goods.filter((g) => g.gatherable);
  const isAptitude = gatherGood === state.player.aptitude;
  const projected = effort * (isAptitude ? 3 : 1);

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

  // [output, ingredients, effort] — mirrors template.py RECIPES.
  const RECIPES: [string, string, number][] = [
    ["flour", "2 grain", 2], ["lumber", "2 wood", 2], ["cloth", "2 wool", 2],
    ["bread", "2 flour", 2], ["garments", "2 cloth", 2], ["medicine", "2 herbs", 3],
    ["tapestries", "3 cloth", 4], ["iron", "2 ore", 3],
    ["tools", "1 iron + 1 lumber", 3], ["glowdye", "2 herbs + 1 ore (license)", 4],
  ];
  const FACILITIES: [string, string][] = [
    ["farm", "Farm Plot → grain"], ["pasture", "Pasture → wool"],
    ["woodlot", "Woodlot → wood"], ["herb_garden", "Herb Garden → herbs"],
    ["mine", "Mine → ore"], ["mill", "Mill → flour"],
    ["loom", "Loom → cloth"], ["smelter", "Smelter → iron"],
    ["bakery", "Bakery → bread"], ["tailor", "Tailor → garments"],
    ["apothecary", "Apothecary → medicine"], ["atelier", "Atelier → tapestries"],
    ["smithy", "Smithy → tools"], ["dyeworks", "Dyeworks → glowdye (license)"],
  ];
  const unlockedGoods = new Set(state.goods.map((g) => g.id));

  const effortChip = (n: number) => (
    <span className="tag" title={`Costs ${n} effort`}
          style={{ display: "inline-flex", alignItems: "center", gap: 4, margin: 0 }}>
      <Asset slot="ui/effort_token" glyph="●" size={13} alt="effort" /> {n}
    </span>
  );

  return (
    <div className="row">
      <div className="panel grow">
        <h3><Asset slot="ui/icon_basket" glyph="🧺" size={20} /> Gathering</h3>
        <div className="row" style={{ alignItems: "center" }}>
          <select value={gatherGood} onChange={(e) => setGatherGood(e.target.value)}>
            {gatherables.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}{g.aptitude ? " (your specialty, 3x)" : ""}
              </option>
            ))}
          </select>
          <label>effort <input type="number" min={1} max={40} value={effort}
                               style={{ width: 64 }}
                               onChange={(e) => setEffort(+e.target.value)} /></label>
          <button onClick={gather}>
            Gather {projected} {gatherGood}
          </button>
          {isAptitude && <span className="tag" style={{ margin: 0 }}>
            <Asset slot="ui/icon_star" glyph="⭐" size={13} /> 3x specialty</span>}
        </div>
        <div className="muted">
          Your <Asset slot="ui/icon_star" glyph="⭐" size={13} alt="specialty" /> specialty
          yields triple. Effort is the one thing you can't buy more of today,
          so spend it like it matters.
        </div>
        <hr className="divider" />
        <h3><Asset slot="ui/icon_mallet" glyph="🔨" size={20} /> Hand-crafting</h3>
        {RECIPES.filter(([out]) => unlockedGoods.has(out)).map(([out, needs, cost]) => (
          <div key={out} style={{ display: "flex", gap: 8, alignItems: "center",
                                  marginBottom: 5 }}>
            <GoodIcon good={out} />
            <span style={{ width: 92 }}>{out}</span>
            <span className="muted" style={{ flex: 1 }}>{needs}</span>
            {effortChip(cost)}
            <button className="wood" style={{ padding: "4px 12px" }}
                    onClick={() => craft(out)}>Craft</button>
          </div>
        ))}
      </div>

      <div className="panel grow">
        <img className="scene-banner" src="/assets/places/workshop_scene.png"
             alt="" onError={(e) =>
               (e.target as HTMLImageElement).style.setProperty("display", "none")} />
        <h3><Asset slot="ui/icon_windmill" glyph="🏭" size={20} /> Your facilities</h3>
        {state.facilities.length === 0 &&
          <div className="muted">No facilities yet. A building works while you sleep.
            That's the whole point of fixed costs.</div>}
        {state.facilities.map((f) => (
          <div key={f.id} className="facility-card">
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <GoodIcon good={f.output} size={34} />
              <div>
                <b>{f.name}</b>
                <div className="muted" style={{ fontSize: 12 }}>
                  tier {f.tier} · makes {f.output_per_day} {f.output}/night
                  · upkeep {f.upkeep}c/night
                  {f.workers > 0 && ` · ${f.workers} workers`}
                  {f.scrubber && " · scrubber fitted"}
                </div>
              </div>
            </div>
            <div className="row" style={{ marginTop: 8, alignItems: "center" }}>
              <button className="quiet" onClick={() =>
                facilityAction(`/worlds/${wid}/facilities/${f.id}/upgrade`)}>
                Upgrade</button>
              <label className="muted">Workers:
                <input type="number" min={0} max={12} defaultValue={f.workers}
                       style={{ width: 56, marginLeft: 4 }}
                       onBlur={(e) => facilityAction(
                         `/worlds/${wid}/facilities/${f.id}/workers`,
                         { workers: +e.target.value })} />
              </label>
              {!f.scrubber && state.world.week >= 6 &&
                <button className="quiet" onClick={() =>
                  facilityAction(`/worlds/${wid}/facilities/${f.id}/scrubber`)}>
                  Fit scrubber (250c)</button>}
            </div>
          </div>
        ))}
        <hr className="divider" />
        <h3><Asset slot="places/workshop" glyph="🏗️" size={20} /> Build</h3>
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
  const till = listings.reduce((s, l) => s + (l.sold_yesterday || 0) * l.price, 0);

  return (
    <div className="row">
      <div className="panel grow">
        <h3><Asset slot="places/shop" glyph="🏪" size={20} /> Your shop window</h3>
        {till > 0 && (
          <div className="pb-banner" style={{ marginBottom: 10 }}>
            Last night's till: {till.toLocaleString()}c while you slept
          </div>
        )}
        <div className="muted" style={{ marginBottom: 8 }}>
          Post your prices and the town browses them every night. The sales
          that follow trace out your own little demand curve, live and in
          the wild.
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
                fontStyle: "italic", fontSize: 13 }}>sold out. Restock?</span>}
              <span className="price-tag">{l.price}c</span>
            </div>
            <div className="muted" style={{ marginTop: -4, marginBottom: 8 }}>
              <b>{l.good_id}</b> · {l.qty} on shelf
              {l.sold_yesterday > 0 &&
                <b className="heat-good"> · {l.sold_yesterday} sold last night</b>}
              {" "}· {l.sold_total} all-time
            </div>
          </div>
        ))}
        {listings.length === 0 && (
          <div style={{ textAlign: "center", padding: "16px 0" }}>
            <div className="shelf" style={{ justifyContent: "center" }}>
              <span style={{ color: "var(--parchment)", opacity: 0.7,
                             fontStyle: "italic" }}>bare boards…</span>
            </div>
            <div className="muted">Empty shelves, merchant. Stock something.
              {sellable.length > 0 && <> You're holding {sellable.slice(0, 3)
                .map((g) => g.name).join(", ")}, ready to shelve.</>}
            </div>
          </div>
        )}
      </div>
      <div className="panel" style={{ flex: "0 1 300px" }}>
        <h3><Asset slot="ui/icon_finery" glyph="✨" size={20} /> Your finery</h3>
        <div className="kicker">cosmetics</div>
        {state.cosmetics.length === 0 &&
          <div className="muted">None yet. Earn prestige, or buy a little swagger
            at the Luxury Boutique in the Guild Hall.</div>}
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
          <div className="muted">None yet. Go achieve something.</div>}
        {state.achievements.map((a) => <span key={a.id} className="tag">
          <Asset slot={a.trophy ? "ui/icon_trophy" : "ui/icon_medal"}
                 glyph={a.trophy ? "🏆" : "🏅"} size={13} /> {a.name}</span>)}
      </div>
    </div>
  );
}

const TROPHIES: { name: string; short: string; slug: string }[] = [
  { name: "A Remarkably Smug Trout", short: "Smug Trout", slug: "smug_trout" },
  { name: "Old Whiskerjaw", short: "Old Whiskerjaw", slug: "old_whiskerjaw" },
  { name: "The Gilded Leviathan", short: "Gilded Leviathan", slug: "gilded_leviathan" },
];
const trophySlug = (name: string) =>
  TROPHIES.find((t) => t.name === name)?.slug || "";

// idle -> waiting (line out) -> strike (reel NOW) -> reeling -> reveal
type DockPhase = "idle" | "waiting" | "strike" | "reeling";

export function Docks({ state, wid, notify, refresh }: {
  state: PlayerState; wid: string; notify: Notify; refresh: () => void;
}) {
  const [phase, setPhase] = useState<DockPhase>("idle");
  const [nibbling, setNibbling] = useState(false);
  const [caption, setCaption] = useState("");
  const [result, setResult] = useState<any>(null);
  const [catches, setCatches] = useState<any[]>([]);
  const timers = useRef<number[]>([]);
  const pending = useRef<any>(null);
  const revealed = useRef(false);

  useEffect(() => () => { timers.current.forEach(clearTimeout); }, []);
  const later = (fn: () => void, ms: number) => {
    timers.current.push(window.setTimeout(fn, ms));
  };

  function reveal(auto = false) {
    if (revealed.current || !pending.current) return;
    revealed.current = true;
    const o = pending.current;
    setPhase("reeling");
    setCaption(auto ? "It very nearly took the rod with it…" : "You strike!");
    later(() => {
      setPhase("idle");
      setCaption("");
      setResult(o);
      setCatches((c) => [o, ...c].slice(0, 6));
      if (o.trophy) notify(`${o.trophy}! Onto the trophy wall it goes.`);
      else if (o.personal_best) notify("A new personal best!");
      else if (o.qty) notify(`Landed ${o.qty} fish.`);
      refresh();
    }, 900);
  }

  async function cast() {
    setPhase("waiting");
    setResult(null);
    setCaption("The line settles on the water…");
    let out: any;
    try {
      out = await api.post(`/worlds/${wid}/fishing/cast`);
    } catch (e: any) {
      notify(e.message, true);
      setPhase("idle");
      setCaption("");
      return;
    }
    // The catch is already decided — everything below is showmanship.
    pending.current = out;
    revealed.current = false;
    const bite = out.bite_ms as number;
    for (let n = 0; n < out.nibbles; n++) {
      const at = bite * (0.3 + 0.25 * n);
      later(() => {
        setNibbling(true);
        setCaption("Something brushes the line…");
      }, at);
      later(() => {
        setNibbling(false);
        setCaption("…and drifts away.");
      }, at + 550);
    }
    later(() => {
      setNibbling(false);
      setPhase("strike");
      setCaption("");
      // dawdle too long and it hooks itself — nobody loses a fish to a meeting
      later(() => reveal(true), 4000);
    }, bite);
  }

  const quota = state.world.fishing_rules?.quota;
  const closed = state.world.fishing_rules?.closed;
  const myTrophies = state.achievements
    .filter((a) => a.trophy)
    .map((a) => a.name);

  return (
    <div className="row">
      <div className="panel grow" style={{ maxWidth: 640 }}>
        <h3><Asset slot="places/docks" glyph="🎣" size={20} /> The Docks</h3>
        <div className="docks-scene">
          <img src="/assets/places/docks_scene.png" alt="The docks at dusk" />
          {phase === "waiting" && (
            <span className={`bobber ${nibbling ? "nibbling" : ""}`} />
          )}
          {phase === "waiting" && nibbling && <span className="ripple" />}
          {phase === "strike" && <span className="strike-flash" />}
        </div>
        <div style={{ textAlign: "center", marginTop: 12, minHeight: 120 }}>
          {closed && <div className="heat-bad" style={{ marginBottom: 6 }}>
            The fishery is closed by royal order.</div>}
          {quota != null && !closed &&
            <div className="heat-bad" style={{ marginBottom: 6 }}>
              Royal quota: {quota} fish per merchant per day.</div>}

          {phase === "idle" && (
            <button onClick={cast} disabled={!!closed}
                    style={{ fontSize: 17, padding: "12px 34px" }}>
              Cast the line
              <span style={{ opacity: 0.85, fontWeight: 500, marginLeft: 8 }}>
                <Asset slot="ui/effort_token" glyph="●" size={14} alt="" /> 3 effort
              </span>
            </button>
          )}
          {phase === "waiting" && (
            <button disabled style={{ fontSize: 17, padding: "12px 34px" }}>
              The line is out…
            </button>
          )}
          {phase === "strike" && (
            <button className="reel-button" style={{ padding: "12px 40px" }}
                    onClick={() => reveal()}>
              Something's on! Reel it in!
            </button>
          )}
          {phase === "reeling" && (
            <button disabled style={{ fontSize: 17, padding: "12px 34px" }}>
              The rod bends…
            </button>
          )}
          {caption && <div className="muted" style={{ fontStyle: "italic",
                                                      marginTop: 8 }}>{caption}</div>}

          {result && phase === "idle" && (
            <div style={{ marginTop: 10 }}>
              {result.qty > 0 ? (
                <>
                  <div style={{ display: "flex", justifyContent: "center",
                                flexWrap: "wrap" }}>
                    {result.fish.map((f: any, i: number) => (
                      <div key={i} className={`catch-card ${f.size_class}`}
                           style={{ animationDelay: `${i * 0.12}s` }}>
                        <GoodIcon good="fish" size={f.size_class === "prize" ? 44
                          : f.size_class === "keeper" ? 34 : 24} />
                        <span className="species">{f.species}</span>
                        <span className="dram">{(f.weight / 10).toFixed(0)} dram
                          {f.size_class === "prize" ? " · a prize!" : ""}</span>
                      </div>
                    ))}
                  </div>
                  {result.personal_best && (
                    <div className="pb-banner">
                      New personal best: {(result.weight / 10).toFixed(0)} dram in one cast
                    </div>
                  )}
                </>
              ) : (
                <div className="muted" style={{ fontStyle: "italic" }}>
                  {result.miss_flavor}</div>
              )}
              {result.trophy && (
                <div style={{ marginTop: 8 }}>
                  <Confetti />
                  <Asset slot={`trophies/${trophySlug(result.trophy)}`}
                         glyph="🏆" size={84} alt={result.trophy} />
                  <div style={{ fontFamily: "var(--font-display)", fontSize: 17 }}>
                    {result.trophy}!</div>
                </div>
              )}
              <div className="muted" style={{ fontStyle: "italic", marginTop: 6 }}>
                {result.stock_hint}
              </div>
            </div>
          )}
          <div className="muted" style={{ marginTop: 12 }}>
            The fishery belongs to everyone. Which is to say: to no one.
          </div>
        </div>
      </div>

      <div className="col" style={{ flex: "0 1 300px" }}>
        <div className="panel">
          <h3><Asset slot="ui/icon_trophy" glyph="🏆" size={20} /> Trophy wall</h3>
          <div className="trophy-wall">
            {TROPHIES.map(({ name, short, slug }) => (
              <div key={name}
                   className={`trophy-slot ${myTrophies.includes(name) ? "" : "empty"}`}
                   title={myTrophies.includes(name) ? name : `${name} — uncaught`}>
                <Asset slot={`trophies/${slug}`} glyph="🐟" size={64} alt={name} />
                <div>{myTrophies.includes(name) ? short : "???"}</div>
              </div>
            ))}
          </div>
          <div className="muted" style={{ marginTop: 8 }}>
            Holding {state.inventory.fish || 0} fish · sell them in the Market
            before they get philosophical.
          </div>
        </div>
        {catches.length > 0 && (
          <div className="panel">
            <h3>Today's casts</h3>
            {catches.map((c, i) => (
              <div key={i} className="muted" style={{ fontSize: 13 }}>
                {c.qty > 0
                  ? <><GoodIcon good="fish" size={14} /> {c.qty}{" "}
                      ({(c.weight / 10).toFixed(0)} dram)</>
                  : "bare hook"}
                {c.trophy && <> · <Asset slot="ui/icon_trophy" glyph="🏆"
                                         size={13} /> {c.trophy}</>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
