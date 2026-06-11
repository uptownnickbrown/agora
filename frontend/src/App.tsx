import React, { useCallback, useEffect, useState } from "react";
import { api, getToken, Me, PlayerState, setToken } from "./api";
import { InstructorScreen } from "./instructor";
import { Docks, MarketSquare, ShopScreen, Workshop } from "./places";
import { PipDock, Puzzle } from "./pip";
import { Crier, GuildHall, Leaderboards, Merchant, Recap } from "./town";
import { Asset, Coins, EffortBar, Toast } from "./ui";
import "./theme.css";

type ToastMsg = { message: string; error?: boolean } | null;

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [worldId, setWorldId] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastMsg>(null);
  const [authChecked, setAuthChecked] = useState(false);

  const notify = useCallback((message: string, error = false) => {
    setToast({ message, error });
  }, []);

  const loadMe = useCallback(async () => {
    if (!getToken()) { setAuthChecked(true); return; }
    try {
      const m = await api.get("/auth/me");
      setMe(m);
      if (m.worlds.length === 1) setWorldId(m.worlds[0].world_id);
    } catch { setToken(null); }
    setAuthChecked(true);
  }, []);
  useEffect(() => { loadMe(); }, [loadMe]);

  if (!authChecked) return null;

  return (
    <div className="shell smog-overlay">
      {!me && <AuthScreen onAuthed={loadMe} notify={notify} />}
      {me && !worldId && (
        <WorldPicker me={me} notify={notify}
                     onPick={setWorldId} onRefresh={loadMe} />
      )}
      {me && worldId && (
        <GameShell me={me} wid={worldId} notify={notify}
                   onLeave={() => setWorldId(null)} />
      )}
      {toast && <Toast message={toast.message} error={toast.error}
                       onDone={() => setToast(null)} />}
    </div>
  );
}

function AuthScreen({ onAuthed, notify }: {
  onAuthed: () => void; notify: (m: string, e?: boolean) => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");

  async function go() {
    try {
      if (mode === "register") {
        const out = await api.post("/auth/register", {
          email, display_name: name, password: password || null,
        });
        setToken(out.token);
      } else if (password) {
        const out = await api.post("/auth/login", { email, password });
        setToken(out.token);
      } else {
        const req = await api.post("/auth/magic/request", { email });
        if (req.dev_token) {
          const out = await api.post("/auth/magic/redeem", { token: req.dev_token });
          setToken(out.token);
        } else {
          notify("Check your email for a sign-in link!"); return;
        }
      }
      onAuthed();
    } catch (e: any) { notify(e.message, true); }
  }

  return (
    <div style={{ maxWidth: 420, margin: "8vh auto" }}>
      <div style={{ textAlign: "center", marginBottom: 14 }}>
        <Asset slot="brand/agora_crest" glyph="🏛️" size={84} />
        <div className="banner" style={{ fontSize: 26 }}>AGORA</div>
        <div style={{ color: "var(--parchment)", opacity: 0.85, marginTop: 8 }}>
          Live inside a working economy.
        </div>
      </div>
      <div className="panel col" style={{ gap: 10 }}>
        <div className="row">
          <button className={mode === "register" ? "" : "quiet"}
                  onClick={() => setMode("register")}>New merchant</button>
          <button className={mode === "login" ? "" : "quiet"}
                  onClick={() => setMode("login")}>Returning</button>
        </div>
        <input placeholder="email" value={email}
               onChange={(e) => setEmail(e.target.value)} />
        {mode === "register" && (
          <input placeholder="merchant name" value={name}
                 onChange={(e) => setName(e.target.value)} />
        )}
        <input placeholder={mode === "login" ? "password (blank = magic link)"
                                             : "password (optional)"}
               type="password" value={password}
               onChange={(e) => setPassword(e.target.value)} />
        <button onClick={go}>
          {mode === "register" ? "Enter the Agora" : "Sign in"}
        </button>
      </div>
    </div>
  );
}

function WorldPicker({ me, onPick, onRefresh, notify }: {
  me: Me; onPick: (wid: string) => void; onRefresh: () => void;
  notify: (m: string, e?: boolean) => void;
}) {
  const [code, setCode] = useState("");
  const [courseTitle, setCourseTitle] = useState("Econ 101");
  const [sectionName, setSectionName] = useState("Section A");

  async function join() {
    try {
      const out = await api.post("/join", { join_code: code.trim() });
      notify(`Welcome to the Agora, ${out.merchant}! Your aptitude: ${out.aptitude}.`);
      onRefresh(); onPick(out.world_id);
    } catch (e: any) { notify(e.message, true); }
  }

  async function createWorld() {
    try {
      const out = await api.post("/instructor/worlds", {
        course_title: courseTitle, section_name: sectionName,
      });
      notify(`World created. Join code: ${out.join_code}`);
      onRefresh(); onPick(out.world_id);
    } catch (e: any) { notify(e.message, true); }
  }

  return (
    <div style={{ maxWidth: 540, margin: "6vh auto" }} className="col">
      <div className="panel">
        <h3>Your worlds</h3>
        {me.worlds.length === 0 && <div className="muted">None yet.</div>}
        {me.worlds.map((w) => (
          <div key={w.world_id} style={{ display: "flex", gap: 8,
                                         alignItems: "center", marginBottom: 6 }}>
            <span style={{ flex: 1 }}>{w.merchant} — week {w.week} ({w.state})</span>
            <button onClick={() => onPick(w.world_id)}>Enter</button>
          </div>
        ))}
        <hr className="divider" />
        <div className="row" style={{ alignItems: "center" }}>
          <input placeholder="join code" value={code}
                 onChange={(e) => setCode(e.target.value)} />
          <button onClick={join}>Join a world</button>
        </div>
      </div>
      <div className="panel">
        <h3>Instructors</h3>
        <div className="row" style={{ alignItems: "center" }}>
          <input value={courseTitle} onChange={(e) => setCourseTitle(e.target.value)} />
          <input value={sectionName} onChange={(e) => setSectionName(e.target.value)} />
          <button className="wood" onClick={createWorld}>Create a world</button>
        </div>
        <div className="muted" style={{ marginTop: 6 }}>
          Creates a 7-week Agora Standard world and makes you its low-touch god.
        </div>
      </div>
    </div>
  );
}

const PLACES: [string, string, string][] = [
  ["market", "Market Square", "⚖️"],
  ["shop", "Your Shop", "🏪"],
  ["workshop", "Workshop", "🔨"],
  ["docks", "The Docks", "🎣"],
  ["puzzle", "Daily Ledger", "🧮"],
  ["crier", "The Crier", "📯"],
  ["guild", "Guild Hall", "🏛️"],
  ["boards", "Leaderboards", "🏆"],
];

function GameShell({ me, wid, notify, onLeave }: {
  me: Me; wid: string; notify: (m: string, e?: boolean) => void; onLeave: () => void;
}) {
  const [place, setPlace] = useState("market");
  const [state, setState] = useState<PlayerState | null>(null);
  const [isInstructorView, setInstructorView] = useState(false);
  const [enrolled, setEnrolled] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setState(await api.get(`/worlds/${wid}/state`));
      setEnrolled(true);
    } catch (e: any) {
      if (e.status === 403) setEnrolled(false);
    }
  }, [wid]);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    const id = setInterval(refresh, 20000);
    return () => clearInterval(id);
  }, [refresh]);

  // The art literally desaturates as smog accumulates (Gray Skies, week 6).
  useEffect(() => {
    const smog = state?.world.smog ?? 0;
    const sat = Math.max(0.55, 1 - smog / 600);
    document.documentElement.style.setProperty("--smog-sat", String(sat));
  }, [state?.world.smog]);

  const isEpilogue = state?.world.state === "epilogue";

  if (!enrolled) {
    return (
      <div className="col">
        <div className="topbar">
          <div className="banner">AGORA</div>
          <span className="plaque">Instructor — gods don't trade</span>
          <span style={{ marginLeft: "auto" }} />
          <button className="quiet" onClick={onLeave}>worlds</button>
        </div>
        <InstructorScreen wid={wid} notify={notify} />
      </div>
    );
  }
  if (!state) return <div style={{ color: "var(--parchment)" }}>Entering the Agora…</div>;

  return (
    <div>
      <div className="topbar">
        <div className="banner">AGORA</div>
        <span className="plaque">Week {state.world.week} · Day {state.world.day}</span>
        <Coins amount={state.player.coins} />
        <EffortBar effort={state.player.effort} />
        {state.world.smog != null && state.world.smog > 0 &&
          <span className="plaque" title="district smog">🏭 {state.world.smog}</span>}
        <span style={{ marginLeft: "auto", color: "var(--parchment)" }}>
          {state.player.merchant}
        </span>
        {me.is_instructor && (
          <button className="quiet" onClick={() => setInstructorView(!isInstructorView)}>
            {isInstructorView ? "🎭 play" : "👁️ god mode"}
          </button>
        )}
        <button className="quiet" onClick={onLeave}>worlds</button>
        <button className="quiet" onClick={() => { setToken(null); location.reload(); }}>
          sign out</button>
      </div>

      {isInstructorView ? (
        <InstructorScreen wid={wid} notify={notify} />
      ) : (
        <>
          <div className="places">
            {PLACES.map(([id, label, glyph]) => (
              <div key={id} className={`place-tile ${place === id ? "active" : ""}`}
                   onClick={() => setPlace(id)} role="button">
                <Asset slot={`places/${id}`} glyph={glyph} size={40} alt={label} />
                <span style={{ display: "block", marginTop: 2 }}>{label}</span>
              </div>
            ))}
            {state.world.week === 1 && (
              <div className={`place-tile ${place === "merchant" ? "active" : ""}`}
                   onClick={() => setPlace("merchant")} role="button">
                <span className="glyph">🐫</span>Traveling Merchant
              </div>
            )}
            {isEpilogue && (
              <div className={`place-tile ${place === "recap" ? "active" : ""}`}
                   onClick={() => setPlace("recap")} role="button">
                <span className="glyph">📖</span>Your Story
              </div>
            )}
          </div>

          {place === "market" &&
            <MarketSquare state={state} wid={wid} notify={notify} refresh={refresh} />}
          {place === "shop" &&
            <ShopScreen state={state} wid={wid} notify={notify} refresh={refresh} />}
          {place === "workshop" &&
            <Workshop state={state} wid={wid} notify={notify} refresh={refresh} />}
          {place === "docks" &&
            <Docks state={state} wid={wid} notify={notify} refresh={refresh} />}
          {place === "puzzle" && <Puzzle wid={wid} notify={notify} refresh={refresh} />}
          {place === "crier" && <Crier wid={wid} />}
          {place === "guild" &&
            <GuildHall state={state} wid={wid} notify={notify} refresh={refresh} />}
          {place === "boards" && <Leaderboards wid={wid} />}
          {place === "merchant" && <Merchant wid={wid} notify={notify} refresh={refresh} />}
          {place === "recap" && <Recap wid={wid} />}

          <div style={{ height: 90 }} />
          <PipDock wid={wid} nudge={state.nudge} />
        </>
      )}
    </div>
  );
}
