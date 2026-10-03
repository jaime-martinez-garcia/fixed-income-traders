// Holdings heatmap: one tile per instrument, size proportional to market value,
// colour by unrealised P&L. Tiles flash green/red when the price ticks.

import type { Holding } from "./api";

const FLASH_MS = 600;

// Short label for each instrument type
const TYPE_BADGE: Record<string, string> = {
  treasury: "TSY",
  ig_corp:  "IG",
  hy_corp:  "HY",
  future:   "FUT",
  swap:     "IRS",
};

export class Heatmap {
  private host: HTMLElement;
  private tiles = new Map<string, HTMLElement>();

  constructor(host: HTMLElement) {
    this.host = host;
    host.classList.add("heatmap");
  }

  render(holdings: Holding[], priceDirections: Record<string, "up" | "down" | "same">): void {
    const isins = new Set(holdings.map((h) => h.isin));

    for (const [isin, el] of this.tiles) {
      if (!isins.has(isin)) {
        el.remove();
        this.tiles.delete(isin);
      }
    }

    if (holdings.length === 0) {
      this.host.dataset.empty = "true";
      return;
    }
    delete this.host.dataset.empty;

    const totalValue = holdings.reduce((s, h) => s + h.market_value, 0);

    for (const h of holdings) {
      const share = totalValue > 0 ? h.market_value / totalValue : 1 / holdings.length;
      let tile = this.tiles.get(h.isin);
      if (!tile) {
        tile = this.createTile(h);
        this.host.append(tile);
        this.tiles.set(h.isin, tile);
      }
      tile.style.flexGrow = String(Math.max(0.05, share));
      tile.dataset.pnl = h.unrealized_pnl >= 0 ? "up" : "down";

      // Update dynamic fields
      tile.querySelector(".heatmap-ytm")!.textContent  = `${h.ytm.toFixed(2)}%`;
      tile.querySelector(".heatmap-value")!.textContent = formatMoney(h.market_value);

      const dir = priceDirections[h.isin];
      if (dir === "up" || dir === "down") flash(tile, dir);
    }
  }

  private createTile(h: Holding): HTMLElement {
    const tile = document.createElement("div");
    tile.className = "heatmap-tile";
    const badge = TYPE_BADGE[h.instrument_type] ?? h.instrument_type.toUpperCase();
    const mat = h.maturity_years >= 1
      ? `${h.maturity_years.toFixed(0)}Y`
      : `${(h.maturity_years * 12).toFixed(0)}M`;
    tile.innerHTML = `
      <span class="heatmap-ticker">${h.isin}</span>
      <span class="heatmap-meta">${badge} · ${mat}</span>
      <span class="heatmap-ytm"></span>
      <span class="heatmap-value"></span>
    `;
    return tile;
  }
}

function flash(tile: HTMLElement, dir: "up" | "down"): void {
  tile.classList.remove("flash-up", "flash-down");
  void tile.offsetWidth;
  tile.classList.add(dir === "up" ? "flash-up" : "flash-down");
  setTimeout(() => tile.classList.remove("flash-up", "flash-down"), FLASH_MS);
}

function formatMoney(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(1)}k`;
  return `$${n.toFixed(0)}`;
}
