/* The Crier, the Guild Hall, leaderboards, the Traveling Merchant, the recap. */
import React, { useCallback, useEffect, useState } from "react";
import { api, PlayerState } from "./api";
import { Asset, Coins, GoodIcon, Sparkline } from "./ui";

type Notify = (msg: string, error?: boolean) => void;

// Map a headline to the event painting it deserves.
function eventArt(title: string): string | null {
  const t = title.toLowerCase();
  if (/festival|lantern/.test(t)) return "events/festival";
  if (/drought|withers|blight/.test(t)) return "events/drought";
  if (/decree|ceiling|crown.*(price|bread)|repeal/.test(t)) return "events/decree";
  if (/traveling merchant|caravan/.test(t)) return "events/merchant";
  if (/charter/.test(t)) return "events/charter";
  if (/license|auction/.test(t)) return "events/auction";
  if (/smog|gray skies|soot|levy/.test(t)) return "events/gray_skies";
  if (/fishery|quota|fish/.test(t)) return "events/fishery_collapse";
  if (/tournament|market wars|war/.test(t)) return "events/market_wars";
  return null;
}

export function Crier({ wid }: { wid: string }) {
  const [posts, setPosts] = useState<any[]>([]);
  useEffect(() => {
    api.get(`/worlds/${wid}/crier`).then(setPosts).catch(() => {});
  }, [wid]);

  const days = [...new Set(posts.map((p) => p.day))].sort((a, b) => b - a);

  return (
    <div className="panel" style={{ maxWidth: 760, margin: "0 auto" }}>
      <div style={{ textAlign: "center", borderBottom: "3px double var(--ink)",
                    paddingBottom: 8, marginBottom: 8 }}>
        <Asset slot="crier/masthead" glyph="📯" size={64} />
        <h2 style={{ margin: 0 }}>The Agora Crier</h2>
        <div className="muted" style={{ fontStyle: "italic" }}>
          All the news that's fit to squawk
        </div>
      </div>
      {days.map((day) => {
        const news = posts.filter((p) => p.day === day && p.kind !== "market_report");
        const reports = posts.filter((p) => p.day === day && p.kind === "market_report");
        return (
          <section key={day}>
            <div className="crier-kicker" style={{ marginTop: 14,
              borderBottom: "1px solid var(--parchment-edge)", paddingBottom: 2 }}>
              ☀️ Day {day}
            </div>
            {news.map((p, i) => {
              const art = eventArt(p.title);
              return (
                <article key={`n${i}`} className="crier-feature">
                  {art && <img className="art" src={`/assets/${art}.png`} alt=""
                               onError={(e) => (e.target as HTMLImageElement)
                                 .style.setProperty("display", "none")} />}
                  <div className="body" style={art ? {} : { padding: "10px 14px" }}>
                    <div className="crier-kicker">{p.kind}</div>
                    <h4 style={{ fontSize: 17 }}>{p.title}</h4>
                    <div style={{ whiteSpace: "pre-wrap", fontSize: 14 }}>{p.body}</div>
                  </div>
                </article>
              );
            })}
            {reports.map((p, i) => (
              <details key={`r${i}`} className="crier-report">
                <summary>📊 {p.title}</summary>
                <div style={{ whiteSpace: "pre-wrap", fontSize: 13,
                              padding: "6px 0 2px 18px" }} className="muted">
                  {p.body}
                </div>
              </details>
            ))}
          </section>
        );
      })}
      {posts.length === 0 && <div className="muted">No news yet. Suspicious.</div>}
    </div>
  );
}

export function Leaderboards({ wid }: { wid: string }) {
  const [boards, setBoards] = useState<any>(null);
  useEffect(() => {
    api.get(`/worlds/${wid}/leaderboards`).then(setBoards).catch(() => {});
  }, [wid]);
  if (!boards) return <div className="panel">The scribes are tallying…</div>;

  const top3 = boards.wealth.slice(0, 3);
  const rest = boards.wealth.slice(3);
  const podiumOrder = [top3[1], top3[0], top3[2]].filter(Boolean);
  const podiumCls = (r: any) =>
    r === top3[0] ? "gold" : r === top3[1] ? "silver" : "bronze";
  const medal = (r: any) => (r === top3[0] ? "🥇" : r === top3[1] ? "🥈" : "🥉");
  const maxHouse = Math.max(1, ...boards.houses.map((h: any) => h.net_worth));

  return (
    <div className="row">
      <div className="panel grow">
        <h3>💰 Wealth</h3>
        <div className="podium">
          {podiumOrder.map((r: any) => (
            <div key={r.merchant} className={`podium-slot ${podiumCls(r)}`}
                 style={r === top3[0] ? { transform: "translateY(-6px)" } : {}}>
              <div className="medal">{medal(r)}</div>
              <div className="who">{r.merchant}</div>
              <div className="score">{r.net_worth.toLocaleString()}c</div>
            </div>
          ))}
        </div>
        {rest.map((r: any, i: number) => (
          <div key={r.merchant} className="board-row">
            <span style={{ width: 26 }} className="muted">{i + 4}.</span>
            <span style={{ flex: 1 }}>{r.merchant}</span>
            <b>{r.net_worth.toLocaleString()}c</b>
          </div>
        ))}
        <div className="muted" style={{ marginTop: 10 }}>
          Wealth buys bragging rights, not grades. The Crown checked.
        </div>
      </div>
      <div className="col grow">
        <div className="panel">
          <h3>🏠 Houses</h3>
          {boards.houses.map((h: any, i: number) => (
            <div key={h.house} className="board-row">
              <span style={{ width: 20 }} className="muted">{i + 1}.</span>
              <span style={{ width: 130 }}>{h.house}
                <span className="muted"> ({h.members})</span></span>
              <div className="meter"><span style={{
                width: `${Math.round(100 * h.net_worth / maxHouse)}%` }} /></div>
              <b style={{ width: 76, textAlign: "right" }}>
                {h.net_worth.toLocaleString()}</b>
            </div>
          ))}
        </div>
        <div className="panel">
          <h3>🧩 Puzzle streaks</h3>
          {boards.puzzle_streaks.map((s: any) => (
            <div key={s.merchant} className="board-row">
              <span style={{ flex: 1 }}>{s.merchant}</span>
              <span className="streak-chip">🔥 {s.streak}</span>
              <span className="muted">best {s.best}</span>
            </div>
          ))}
          {boards.puzzle_streaks.length === 0 &&
            <div className="muted">No streaks yet — the Daily Ledger awaits.</div>}
        </div>
        <div className="panel">
          <h3>🎣 Biggest catch</h3>
          {boards.biggest_catch.map((c: any, i: number) => (
            <div key={c.merchant} className="board-row">
              <span style={{ width: 26 }}>{["🥇", "🥈", "🥉"][i] || `${i + 1}.`}</span>
              <span style={{ flex: 1 }}>{c.merchant}</span>
              <b>{(c.weight / 10).toFixed(0)} dram</b>
            </div>
          ))}
          {boards.biggest_catch.length === 0 &&
            <div className="muted">Nothing landed yet. The Docks are calling.</div>}
        </div>
      </div>
    </div>
  );
}

export function GuildHall({ state, wid, notify, refresh }: {
  state: PlayerState; wid: string; notify: Notify; refresh: () => void;
}) {
  const [boutique, setBoutique] = useState<Record<string, any>>({});
  const [compacts, setCompacts] = useState<any[]>([]);
  const [auctions, setAuctions] = useState<any[]>([]);
  const [auctionId, setAuctionId] = useState("");
  const [bid, setBid] = useState(100);
  const [compactName, setCompactName] = useState("");
  const [compactGood, setCompactGood] = useState("cloth");
  const [compactPrice, setCompactPrice] = useState(80);

  const load = useCallback(async () => {
    const [b, c, a] = await Promise.all([
      api.get(`/worlds/${wid}/boutique`),
      api.get(`/worlds/${wid}/compacts`),
      api.get(`/worlds/${wid}/license-auctions`).catch(() => []),
    ]);
    setBoutique(b); setCompacts(c); setAuctions(a);
    if (a.length && !a.some((x: any) => x.auction_id === auctionId)) {
      setAuctionId(a[0].auction_id);
    }
  }, [wid, auctionId]);
  useEffect(() => { load().catch(() => {}); }, [load]);

  async function act(fn: () => Promise<any>, msg: string) {
    try { await fn(); notify(msg); await load(); refresh(); }
    catch (e: any) { notify(e.message, true); }
  }

  return (
    <div className="row">
      <div className="panel grow">
        <h3>📜 Crown licenses (sealed-bid)</h3>
        {state.licenses?.length > 0 && (
          <div style={{ marginBottom: 6 }}>
            {state.licenses.map((g) => (
              <span key={g} className="tag"
                    style={{ background: "rgba(217,169,63,0.25)",
                             borderColor: "var(--gold)", fontWeight: 600 }}>
                👑 you hold the {g} license
              </span>
            ))}
          </div>
        )}
        <div className="muted">When the Crier announces an auction, place your bid.
          Top bids win; you pay what you bid. Tell no one your number.</div>
        {auctions.length === 0 ? (
          <div className="muted" style={{ marginTop: 8, fontStyle: "italic" }}>
            No auctions open today. The Crown announces them in the Crier
            (week 5, traditionally).
          </div>
        ) : (
          <div className="row" style={{ alignItems: "center", marginTop: 8 }}>
            <select value={auctionId} onChange={(e) => setAuctionId(e.target.value)}>
              {auctions.map((a) => (
                <option key={a.auction_id} value={a.auction_id}>
                  {a.good} — {a.licenses} licenses, closes day {a.closes_day}
                </option>
              ))}
            </select>
            <input type="number" value={bid} onChange={(e) => setBid(+e.target.value)}
                   style={{ width: 90 }} />
            <button onClick={() => act(
              () => api.post(`/worlds/${wid}/license-bids`,
                             { auction_id: auctionId, amount: bid }),
              "Bid sealed and submitted.")}>Submit bid</button>
            {auctions.find((a) => a.auction_id === auctionId)?.my_bid != null &&
              <span className="tag">your sealed bid: {
                auctions.find((a) => a.auction_id === auctionId).my_bid}c</span>}
          </div>
        )}
        <hr className="divider" />
        <h3>🤝 Compacts (week 7)</h3>
        <div className="muted">Visible terms. Zero enforcement. What could go wrong?</div>
        {compacts.map((c) => (
          <div key={c.id} className="panel" style={{ padding: 10, marginTop: 8 }}>
            <b>{c.name}</b> <span className="tag">{c.kind}</span>
            {c.dissolved_day != null && <span className="tag">💀 dissolved</span>}
            <div className="muted">terms: {JSON.stringify(c.terms)}</div>
            <div className="muted">signatories: {c.members.join(", ") || "none"}</div>
            <div className="row" style={{ marginTop: 6 }}>
              <button className="quiet" onClick={() => act(
                () => api.post(`/worlds/${wid}/compacts/${c.id}/join`), "Signed.")}>
                sign</button>
              <button className="quiet" onClick={() => act(
                () => api.post(`/worlds/${wid}/compacts/${c.id}/leave`), "Defected!")}>
                defect</button>
            </div>
          </div>
        ))}
        <div className="row" style={{ alignItems: "center", marginTop: 8 }}>
          <input placeholder="compact name" value={compactName}
                 onChange={(e) => setCompactName(e.target.value)} />
          <select value={compactGood} onChange={(e) => setCompactGood(e.target.value)}>
            {state.goods.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
          <input type="number" value={compactPrice} style={{ width: 80 }}
                 onChange={(e) => setCompactPrice(+e.target.value)} />
          <button onClick={() => act(
            () => api.post(`/worlds/${wid}/compacts`, {
              name: compactName || "Unnamed Ring", kind: "price_accord",
              terms: { good: compactGood, price: compactPrice },
            }), "Compact founded. The Crier is watching.")}>Found compact</button>
        </div>
      </div>

      <div className="col" style={{ flex: "0 1 300px" }}>
        <div className="panel">
          <h3>🛟 The Guild's mercy</h3>
          <div className="muted">Broke? (Under 30 coppers.) The Guild offers a fresh-start
            loan. Gentle terms. Real interest.</div>
          <button className="wood" style={{ marginTop: 8 }} onClick={() => act(
            () => api.post(`/worlds/${wid}/fresh-start`), "The Guild believes in you.")}>
            Request fresh start</button>
          {state.loan && <div className="heat-bad" style={{ marginTop: 6 }}>
            Outstanding: {state.loan.outstanding} coppers</div>}
        </div>
        <div className="panel">
          <h3>🛍️ Luxury Boutique</h3>
          <div className="muted">Pure swagger. The economy thanks you for your
            contribution to the coin sink.</div>
          {Object.entries(boutique).map(([id, item]: [string, any]) => (
            <div key={id} style={{ display: "flex", gap: 8, alignItems: "center",
                                   marginTop: 6 }}>
              <span style={{ flex: 1 }}>{item.name}</span>
              <Coins amount={item.price} />
              <button className="quiet" disabled={state.cosmetics.includes(id)}
                      onClick={() => act(
                        () => api.post(`/worlds/${wid}/boutique/buy`, { cosmetic_id: id }),
                        "Delivered to your shop. Gorgeous.")}>
                {state.cosmetics.includes(id) ? "owned" : "buy"}</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function Merchant({ wid, notify, refresh }: {
  wid: string; notify: Notify; refresh: () => void;
}) {
  const [inst, setInst] = useState<any>(null);
  const [plan, setPlan] = useState<Record<string, Record<string, number>>>({});

  useEffect(() => {
    api.get(`/worlds/${wid}/merchant`).then(setInst).catch(() => {});
  }, [wid]);

  if (!inst) return <div className="panel">The merchant readies the cart…</div>;
  if (inst.completed) {
    return (
      <div className="panel" style={{ textAlign: "center" }}>
        <h3>🐫 The Traveling Merchant</h3>
        <p>You completed the route with a profit of <b>{inst.profit}</b> coppers.
          The merchant tips his hat and moves on.</p>
      </div>
    );
  }

  function setBuy(port: string, good: string, qty: number) {
    setPlan((p) => ({ ...p, [port]: { ...(p[port] || {}), [good]: qty } }));
  }

  // Live route math — the arbitrage lesson, visible while you plan.
  const legPorts: string[] = inst.ports.slice(0, -1);
  let projected = 0;
  const cargo: Record<string, number> = {};
  const spend: Record<string, number> = {};
  legPorts.forEach((port: string, i: number) => {
    const next = inst.ports[i + 1];
    let c = 0, sp = 0;
    for (const g of inst.goods) {
      const q = plan[port]?.[g] || 0;
      c += q; sp += q * inst.prices[port][g];
      projected += q * (inst.prices[next][g] - inst.prices[port][g]);
    }
    cargo[port] = c; spend[port] = sp;
  });
  const overloaded = legPorts.some((p: string) => cargo[p] > inst.capacity);

  async function submit() {
    const legs = inst.ports.slice(0, -1).map((port: string) => ({
      port, buy: Object.fromEntries(
        Object.entries(plan[port] || {}).filter(([, q]) => q > 0)),
    }));
    try {
      const out = await api.post(`/worlds/${wid}/merchant/submit`, { legs });
      notify(`Route complete! Profit ${out.profit}, reward ${out.reward} coppers.`);
      setInst({ ...inst, completed: true, profit: out.profit });
      refresh();
    } catch (e: any) { notify(e.message, true); }
  }

  return (
    <div className="panel">
      <h3>🐫 The Traveling Merchant</h3>
      <div className="muted">
        Bankroll {inst.bankroll} coppers, cargo hold {inst.capacity} crates. Buy at each
        stop; everything sells automatically at the NEXT port. Different towns, different
        prices — that's the whole trick of trade.
      </div>
      <div className="row" style={{ marginTop: 10 }}>
        {inst.ports.map((port: string, i: number) => (
          <div key={port} className="panel grow" style={{ padding: 10 }}>
            <h4 style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {i + 1}. {port}
              {i < inst.ports.length - 1 && (
                <span className="tag" style={cargo[port] > inst.capacity
                  ? { background: "var(--rose)", color: "#fff", borderColor: "transparent" }
                  : {}}>
                  🧺 {cargo[port]}/{inst.capacity}
                  {spend[port] > 0 && <> · {spend[port]}c</>}
                </span>
              )}
            </h4>
            <table className="book">
              <thead><tr><th style={{ textAlign: "left" }}>good</th><th>price</th>
                {i < inst.ports.length - 1 && <th>buy</th>}</tr></thead>
              <tbody>
                {inst.goods.map((g: string) => (
                  <tr key={g}>
                    <td style={{ textAlign: "left" }}><GoodIcon good={g} size={18} /> {g}</td>
                    <td>{inst.prices[port][g]}</td>
                    {i < inst.ports.length - 1 && (
                      <td><input type="number" min={0} max={inst.capacity}
                                 style={{ width: 54 }}
                                 value={plan[port]?.[g] || 0}
                                 onChange={(e) => setBuy(port, g, +e.target.value)} /></td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
      <div className="row" style={{ alignItems: "center", marginTop: 12 }}>
        <button onClick={submit} disabled={overloaded}>Ride the route</button>
        <span className={projected > 0 ? "heat-good" : projected < 0 ? "heat-bad" : "muted"}
              style={{ fontSize: 15 }}>
          {overloaded ? "⚠️ a camel can only carry so much"
            : projected !== 0
              ? `projected profit: ${projected > 0 ? "+" : ""}${projected} coppers`
              : "plan your cargo — buy where it's cheap, it sells at the next stop"}
        </span>
      </div>
    </div>
  );
}

export function Recap({ wid }: { wid: string }) {
  const [recap, setRecap] = useState<any>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.get(`/worlds/${wid}/recap`).then(setRecap).catch((e) => setError(e.message));
  }, [wid]);
  if (error) return <div className="panel">{error}</div>;
  if (!recap) return <div className="panel">Binding your story…</div>;
  return (
    <div className="panel" style={{ maxWidth: 700, margin: "0 auto" }}>
      <div style={{ textAlign: "center" }}>
        <Asset slot="recap/laurel" glyph="🏛️" size={52} />
        <h2>Your Economic Story</h2>
        <div className="muted">{recap.merchant} · {recap.world_days} days in the Agora</div>
      </div>
      <Sparkline points={recap.net_worth_curve.map((p: any) => p.net_worth)}
                 width={620} height={120} />
      {recap.chapters.map((c: string, i: number) => (
        <p key={i} style={{ fontSize: 15 }}>{c}</p>
      ))}
      {recap.best_trade && (
        <div className="panel" style={{ padding: 10 }}>
          <b>Finest trade:</b> {recap.best_trade.good} — bought {recap.best_trade.bought_at},
          sold {recap.best_trade.sold_at} (+{recap.best_trade.gain})
        </div>
      )}
      <h3 style={{ marginTop: 12 }}>You proved you understand</h3>
      {recap.mastery_strongest.map((m: any) => (
        <div key={m.lo}>✅ {m.lo} <span className="muted">({m.pct}%)</span></div>
      ))}
      <h3 style={{ marginTop: 12 }}>Honors</h3>
      {recap.achievements.map((a: any) => (
        <span key={a.id} className="tag">
          {String(a.name).startsWith("trophy:")
            ? <>🎣 {String(a.name).slice(7)}</>
            : <>🏅 {a.name}</>}
        </span>
      ))}
      <div className="muted" style={{ marginTop: 14, textAlign: "center",
                                      fontStyle: "italic" }}>
        "Buy low, sell high, and be kind to pigeons." — Prof. Pip
      </div>
    </div>
  );
}
