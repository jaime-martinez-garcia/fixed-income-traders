// Per-trader portfolio-value line chart (uPlot wrapper).

import uPlot, { type Options } from "uplot";
import "uplot/dist/uPlot.min.css";

import type { ChartPoint } from "./state";

const MIN_HEIGHT  = 120;
const Y_AXIS_WIDTH = 72;

export class PortfolioChart {
  private plot: uPlot;
  private host: HTMLElement;

  constructor(host: HTMLElement) {
    this.host = host;

    const opts: Options = {
      width: 1, height: 1,
      pxAlign: false,
      cursor: { show: false },
      legend: { show: false },
      scales: {
        x: {
          time: true,
          range: (_u, min, max) => (min === max ? [min - 300, max + 30] : [min, max]),
        },
        y: {
          range: (_u, min, max) =>
            min === max
              ? [min - 100, max + 100]
              : [min - (max - min) * 0.1, max + (max - min) * 0.1],
        },
      },
      axes: [
        {
          stroke: () => getVar("--fg-muted") || "#8a93a1",
          grid:   { stroke: () => getVar("--grid") || "#232831" },
        },
        {
          stroke: () => getVar("--fg-muted") || "#8a93a1",
          grid:   { stroke: () => getVar("--grid") || "#232831" },
          size:   Y_AXIS_WIDTH,
          values: (_u, splits) => splits.map(formatCompact),
        },
      ],
      series: [
        {},
        {
          stroke: (u) => trendColor(u),
          fill:   (u) => fillGradient(u),
          width:  2,
        },
      ],
    };
    this.plot = new uPlot(opts, [[], []], host);

    requestAnimationFrame(() => requestAnimationFrame(() => this.syncSize()));
    new ResizeObserver(() => this.syncSize()).observe(this.host);
    window.addEventListener("themechange", () => this.plot.redraw());
  }

  update(points: ChartPoint[]): void {
    const xs = points.map((p) => p.t);
    const ys = points.map((p) => p.value);
    this.plot.setData([xs, ys]);
  }

  private syncSize(): void {
    const rect = this.host.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    this.plot.setSize({
      width:  Math.floor(rect.width),
      height: Math.max(MIN_HEIGHT, Math.floor(rect.height)),
    });
  }
}

function isUp(u: uPlot): boolean {
  const ys = u.data[1] as number[];
  return ys.length > 1 ? ys[ys.length - 1] >= ys[0] : true;
}

function trendColor(u: uPlot): string {
  const up = isUp(u);
  return getVar(up ? "--trend-up" : "--trend-down") || (up ? "#3fbf7f" : "#e05560");
}

function fillGradient(u: uPlot): CanvasGradient {
  const color   = trendColor(u);
  const { ctx, bbox } = u;
  const grad    = ctx.createLinearGradient(0, bbox.top, 0, bbox.top + bbox.height);
  grad.addColorStop(0, hexToRgba(color, 0.28));
  grad.addColorStop(1, hexToRgba(color, 0));
  return grad;
}

function getVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function formatCompact(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  return `$${Math.round(n).toLocaleString("en-US")}`;
}
