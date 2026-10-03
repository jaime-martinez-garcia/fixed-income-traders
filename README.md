# Fixed Income Traders

An autonomous fixed income trading simulation powered by AI agents and the Model Context Protocol (MCP).

Four portfolio managers — Bill, Jeffrey, Mohamed, and Kathy — independently manage bond portfolios across US Treasuries, investment-grade corporates, high-yield bonds, Treasury futures, and SOFR interest rate swaps.

Each trader runs as an OpenAI Agents SDK agent with its own strategy, memory, and access to market data and account tools exposed through MCP servers. A FastAPI backend serves live state to a TypeScript/Vite frontend.

## Traders

| Trader | Style | Focus |
|--------|-------|-------|
| **Bill** | Total Return | Active duration management, rate directional bets |
| **Jeffrey** | Unconstrained Macro | Credit spreads, cross-asset relative value |
| **Mohamed** | Sovereign Macro | Monetary policy, curve positioning, risk management |
| **Kathy** | Systematic | Bond laddering, carry, data-driven duration hedging |

## Instrument Universe

| ISIN | Name | Type |
|------|------|------|
| UST2Y | US Treasury 2-Year Note | Treasury |
| UST5Y | US Treasury 5-Year Note | Treasury |
| UST10Y | US Treasury 10-Year Note | Treasury |
| UST30Y | US Treasury 30-Year Bond | Treasury |
| AAPL5Y | Apple Inc 5-Year Bond | IG Corp |
| MSFT7Y | Microsoft 7-Year Bond | IG Corp |
| JPM10Y | JPMorgan Chase 10-Year Bond | IG Corp |
| GS5Y | Goldman Sachs 5-Year Bond | IG Corp |
| TSLA5Y | Tesla 5-Year High Yield | HY Corp |
| F7Y | Ford Motor 7-Year Bond | HY Corp |
| TY | 10Y Treasury Note Future | Future |
| US | 30Y Treasury Bond Future | Future |
| TU | 2Y Treasury Note Future | Future |
| IRS5Y | 5Y SOFR Interest Rate Swap | Swap |
| IRS10Y | 10Y SOFR Interest Rate Swap | Swap |

## Market Data

- **Live (optional):** Set `FRED_API_KEY` for real US Treasury yield curves from the [FRED API](https://fred.stlouisfed.org/docs/api/api_key.html) (free). Credit spreads are modelled on top.
- **Simulated (default):** A deterministic Nelson-Siegel yield curve generator with slow-drifting parameters — no key needed.

## Setup

### Prerequisites

- Python ≥ 3.12 with [uv](https://docs.astral.sh/uv/)
- Node.js ≥ 18

### Install

```bash
# Python dependencies
uv sync

# Optional: add fredapi for live FRED data
uv add fredapi

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Configure

```bash
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY
```

### Reset traders (first run or to start fresh)

```bash
uv run -m backend.reset
```

### Run

Open three terminals:

**Terminal 1 — Trading floor:**
```bash
uv run -m backend.trading_floor
```

**Terminal 2 — API server:**
```bash
uv run uvicorn backend.api:app --port 8000
```

**Terminal 3 — Frontend:**
```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Trading Floor                       │
│  Bill · Jeffrey · Mohamed · Kathy  (OpenAI Agents)  │
│  Each trader runs as an Agent with:                  │
│  ├── Researcher sub-agent (web search + memory)      │
│  ├── Accounts MCP server  (buy/sell/strategy)        │
│  ├── Market MCP server    (yield curve + prices)     │
│  └── Push MCP server      (notifications)            │
└───────────────────┬─────────────────────────────────┘
                    │ writes to SQLite
         ┌──────────▼──────────┐
         │    accounts.db      │
         └──────────┬──────────┘
                    │ reads (read-only)
         ┌──────────▼──────────┐
         │  FastAPI backend     │  :8000
         │  /api/traders        │
         │  /api/market         │
         └──────────┬──────────┘
                    │ proxied /api
         ┌──────────▼──────────┐
         │  Vite frontend       │  :5173
         │  4-panel dashboard   │
         └─────────────────────┘
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for agent LLM |
| `FRED_API_KEY` | No | FRED API key for live Treasury yields |
| `TAVILY_API_KEY` | No | Web search for the researcher agent |
| `RUN_EVERY_N_MINUTES` | No | Trading interval (default: 60) |
| `RUN_EVEN_WHEN_MARKET_IS_CLOSED` | No | Skip weekday check (default: false) |
| `USE_MANY_MODELS` | No | Run each trader on a different LLM |
| `PUSHOVER_USER` / `PUSHOVER_TOKEN` | No | Push notification credentials |
