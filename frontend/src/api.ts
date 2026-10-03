// Client for the fixed income trading floor HTTP API.
// All paths are relative; in dev the Vite proxy forwards /api to FastAPI.

export interface TraderInfo {
  name: string;
  lastname: string;
  model_name: string;
}

export interface Holding {
  isin: string;
  name: string;
  instrument_type: string;
  maturity_years: number;
  notional: number;
  price: number;
  ytm: number;
  modified_duration: number;
  dv01_per_1k: number;
  avg_cost: number;
  market_value: number;
  unrealized_pnl: number;
  credit_rating: string;
}

export interface Transaction {
  isin: string;
  instrument_name: string;
  notional: number;     // positive = buy, negative = sell
  price: number;        // % of par
  ytm: number;
  timestamp: string;
  rationale: string;
}

export interface TimePoint {
  datetime: string;
  value: number;
}

export interface TraderDetail extends TraderInfo {
  balance: number;
  strategy: string;
  portfolio_value: number;
  pnl: number;
  holdings: Holding[];
  transactions: Transaction[];
  time_series: TimePoint[];
}

export interface LogRow {
  datetime: string;
  type: string;
  message: string;
  color: string;
}

export interface MarketInfo {
  source: "fred" | "simulator";
  is_market_open: boolean;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} failed: ${r.status}`);
  return r.json() as Promise<T>;
}

export function getTraders(): Promise<TraderInfo[]> {
  return get("/api/traders");
}

export function getTrader(name: string): Promise<TraderDetail> {
  return get(`/api/traders/${encodeURIComponent(name)}`);
}

export function getTraderLogs(name: string, lastN = 13): Promise<LogRow[]> {
  return get(`/api/traders/${encodeURIComponent(name)}/logs?last_n=${lastN}`);
}

export function getMarket(): Promise<MarketInfo> {
  return get("/api/market");
}

export function getYieldCurve(): Promise<Record<string, number>> {
  return get("/api/market/yield-curve");
}
