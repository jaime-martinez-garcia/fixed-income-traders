// A trader's recent fixed income trades, newest first.

import type { Transaction } from "./api";

const MAX_ROWS = 12;

export class TransactionsView {
  private host: HTMLElement;

  constructor(host: HTMLElement) {
    this.host = host;
    host.classList.add("txns");
  }

  render(transactions: Transaction[]): void {
    this.host.innerHTML = "";
    if (transactions.length === 0) {
      const empty = document.createElement("div");
      empty.className = "txn-empty";
      empty.textContent = "No trades yet";
      this.host.append(empty);
      return;
    }
    for (const t of transactions.slice(-MAX_ROWS).reverse()) {
      const row = document.createElement("div");
      row.className = "txn-row";

      const date = document.createElement("span");
      date.className = "txn-date";
      date.textContent = dateOf(t.timestamp);

      const side = document.createElement("span");
      side.className = "txn-side";
      side.dataset.side = t.notional >= 0 ? "buy" : "sell";
      side.textContent = t.notional >= 0 ? "BUY" : "SELL";

      const detail = document.createElement("span");
      detail.className = "txn-detail";
      // Show: $10k UST10Y @ 98.50 (4.32%)
      const notStr   = formatNotional(Math.abs(t.notional));
      const priceStr = t.price.toFixed(2);
      const ytmStr   = t.ytm.toFixed(2);
      detail.textContent = `${notStr} ${t.isin} @ ${priceStr} (${ytmStr}%)`;

      row.append(date, side, detail);
      this.host.append(row);
    }
  }
}

function dateOf(stamp: string): string {
  const parts = stamp.split(" ")[0].split("-");
  return parts.length === 3 ? `${parts[1]}-${parts[2]}` : stamp;
}

function formatNotional(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(0)}k`;
  return `$${n}`;
}
