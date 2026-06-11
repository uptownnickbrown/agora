/* Typed-enough client for the Agora API. Token persists in localStorage. */

const BASE = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem("agora_token");
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem("agora_token", token);
  else localStorage.removeItem("agora_token");
}

async function request(method: string, path: string, body?: unknown): Promise<any> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch { /* keep statusText */ }
    throw new ApiError(res.status, detail);
  }
  const text = await res.text();
  try { return JSON.parse(text); } catch { return text; }
}

export const api = {
  get: (path: string) => request("GET", path),
  post: (path: string, body?: unknown) => request("POST", path, body),
  del: (path: string) => request("DELETE", path),
};

export interface WorldRef {
  world_id: string;
  merchant: string;
  week: number;
  state: string;
}

export interface Me {
  user_id: string;
  email: string;
  display_name: string;
  is_instructor: boolean;
  is_admin: boolean;
  worlds: WorldRef[];
}

export interface PlayerState {
  world: {
    id: string; week: number; day: number; state: string;
    market_rules: any; fishing_rules: any; smog: number | null;
  };
  player: { id: string; merchant: string; coins: number; effort: number; aptitude: string };
  goods: { id: string; name: string; tier: string; gatherable: boolean;
           license_required: boolean; aptitude: boolean }[];
  inventory: Record<string, number>;
  facilities: { id: string; kind: string; tier: number; workers: number;
                scrubber: boolean; name: string; output: string }[];
  open_orders: { id: string; good_id: string; side: string; qty: number;
                 remaining: number; price: number; expires_day: number }[];
  achievements: string[];
  cosmetics: string[];
  loan: { outstanding: number } | null;
  nudge: string | null;
}
