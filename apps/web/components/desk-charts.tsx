"use client";

import { useState, type PointerEvent } from "react";
import clsx from "clsx";

import type { DeskFrame, DeskKillReason, DeskMonteCarlo, DeskTrade } from "@tradenoc/types";
import { formatMoney, formatSigned, formatSignedMoney } from "@/lib/desk";

const VIEW_WIDTH = 1000;
const VIEW_HEIGHT = 200;
const LINE_COLOR = "#67e8f9";

function pointerFraction(event: PointerEvent<HTMLDivElement>): number {
  const bounds = event.currentTarget.getBoundingClientRect();
  return Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
}

function linePath(points: Array<[number, number]>): string {
  return points.map(([x, y], index) => `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`).join(" ");
}

export function EquityChart({
  frames,
  currentIndex,
  startingBalance,
  trades,
  barsPerSession,
}: {
  frames: DeskFrame[];
  currentIndex: number;
  startingBalance: number;
  trades: DeskTrade[];
  barsPerSession: number;
}) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const visible = frames.slice(0, currentIndex + 1);
  const values = [startingBalance, ...visible.map((frame) => frame.equity)];
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const padding = Math.max((rawMax - rawMin) * 0.15, startingBalance * 0.002);
  const yMin = rawMin - padding;
  const yMax = rawMax + padding;
  const lastIndex = Math.max(frames.length - 1, 1);

  const x = (index: number) => (index / lastIndex) * VIEW_WIDTH;
  const y = (value: number) => VIEW_HEIGHT - ((value - yMin) / (yMax - yMin)) * VIEW_HEIGHT;
  const points = visible.map((frame, index): [number, number] => [x(index), y(frame.equity)]);
  const line = linePath(points);
  const area = points.length ? `${line} L${points[points.length - 1][0]},${VIEW_HEIGHT} L0,${VIEW_HEIGHT} Z` : "";
  const sessionStarts = frames
    .map((frame, index) => ({ frame, index }))
    .filter(({ index }) => index > 0 && index % barsPerSession === 0);
  const worstTrade = trades.length ? trades.reduce((worst, trade) => (trade.pnl < worst.pnl ? trade : worst)) : null;
  const hovered = hoverIndex !== null ? visible[hoverIndex] : null;

  function handlePointer(event: PointerEvent<HTMLDivElement>) {
    if (!visible.length) {
      return;
    }
    const index = Math.round(pointerFraction(event) * lastIndex);
    setHoverIndex(Math.min(index, visible.length - 1));
  }

  return (
    <div>
      <div
        className="relative h-36 w-full touch-none select-none"
        onPointerMove={handlePointer}
        onPointerLeave={() => setHoverIndex(null)}
        role="img"
        aria-label={`Equity curve from ${formatMoney(startingBalance)} to ${formatMoney(visible.at(-1)?.equity ?? startingBalance)}`}
      >
        <svg
          viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
          preserveAspectRatio="none"
          className="absolute inset-0 h-full w-full overflow-visible"
          aria-hidden
        >
          <line
            x1={0}
            x2={VIEW_WIDTH}
            y1={y(startingBalance)}
            y2={y(startingBalance)}
            stroke="rgba(148,163,184,0.28)"
            strokeWidth={1}
            vectorEffect="non-scaling-stroke"
          />
          {sessionStarts.map(({ index }) => (
            <line
              key={index}
              x1={x(index)}
              x2={x(index)}
              y1={0}
              y2={VIEW_HEIGHT}
              stroke="rgba(148,163,184,0.16)"
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            />
          ))}
          <path d={area} fill={LINE_COLOR} fillOpacity={0.1} />
          <path
            d={line}
            fill="none"
            stroke={LINE_COLOR}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
          {hovered ? (
            <line
              x1={x(hoverIndex ?? 0)}
              x2={x(hoverIndex ?? 0)}
              y1={0}
              y2={VIEW_HEIGHT}
              stroke="rgba(226,232,240,0.45)"
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            />
          ) : null}
        </svg>

        <span
          className="pointer-events-none absolute right-1 rounded bg-slate-950/80 px-1 text-[10px] text-slate-400"
          style={{ top: `${(y(startingBalance) / VIEW_HEIGHT) * 100}%`, transform: "translateY(-50%)" }}
        >
          start {formatMoney(startingBalance)}
        </span>
        {sessionStarts.map(({ frame, index }) => (
          <span
            key={index}
            className="pointer-events-none absolute top-0 ml-1 text-[10px] uppercase tracking-[0.16em] text-slate-500"
            style={{ left: `${(x(index) / VIEW_WIDTH) * 100}%` }}
          >
            S{frame.session}
          </span>
        ))}

        {trades.map((trade) => {
          const index = frames.findIndex((frame) => frame.step === trade.close_step);
          if (index < 0 || index > currentIndex) {
            return null;
          }
          return (
            <span
              key={trade.id}
              title={`${trade.id} ${trade.symbol} ${formatSignedMoney(trade.pnl)} (${formatSigned(trade.r_multiple, 2, "R")})`}
              className={clsx(
                "absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-slate-950",
                trade.pnl > 0 ? "bg-emerald-400" : "bg-rose-400",
              )}
              style={{ left: `${(x(index) / VIEW_WIDTH) * 100}%`, top: `${(y(frames[index].equity) / VIEW_HEIGHT) * 100}%` }}
            />
          );
        })}

        {worstTrade && worstTrade.pnl < 0 ? (
          (() => {
            const index = frames.findIndex((frame) => frame.step === worstTrade.close_step);
            const left = Math.min(Math.max((x(index) / VIEW_WIDTH) * 100, 8), 88);
            return (
              <span
                className="pointer-events-none absolute rounded-full border border-rose-400/50 bg-rose-500/15 px-2 py-0.5 text-[11px] font-medium text-rose-100"
                style={{ left: `${left}%`, top: `${(y(frames[index].equity) / VIEW_HEIGHT) * 100}%`, transform: "translate(-50%, 70%)" }}
              >
                {formatSignedMoney(worstTrade.pnl)} {worstTrade.symbol}
              </span>
            );
          })()
        ) : null}

        {points.length ? (
          <span
            className="absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-300 ring-2 ring-slate-950"
            style={{
              left: `${(points[points.length - 1][0] / VIEW_WIDTH) * 100}%`,
              top: `${(points[points.length - 1][1] / VIEW_HEIGHT) * 100}%`,
            }}
          />
        ) : null}

        {hovered ? (
          <div
            className="pointer-events-none absolute top-2 z-10 rounded-xl border border-white/10 bg-slate-950/95 px-3 py-2 text-xs shadow-lg"
            style={{
              left: `${(x(hoverIndex ?? 0) / VIEW_WIDTH) * 100}%`,
              transform: (hoverIndex ?? 0) / lastIndex > 0.6 ? "translateX(calc(-100% - 8px))" : "translateX(8px)",
            }}
          >
            <p className="font-semibold text-white">{formatMoney(hovered.equity)}</p>
            <p className="text-slate-400">
              {formatSignedMoney(hovered.equity - startingBalance)} · S{hovered.session} {hovered.clock}
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function MonteCarloFan({ monteCarlo, startingBalance }: { monteCarlo: DeskMonteCarlo; startingBalance: number }) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const bands = monteCarlo.bands;
  const values = bands.flatMap((band) => [band.p5, band.p95]).concat(1);
  const spread = Math.max(...values) - Math.min(...values);
  const yMin = Math.min(...values) - spread * 0.08;
  const yMax = Math.max(...values) + spread * 0.08;
  const lastTrade = bands[bands.length - 1].trade_index;
  const x = (tradeIndex: number) => (tradeIndex / lastTrade) * VIEW_WIDTH;
  const y = (value: number) => VIEW_HEIGHT - ((value - yMin) / (yMax - yMin)) * VIEW_HEIGHT;
  const band = (low: "p5" | "p25", high: "p75" | "p95") =>
    `${linePath(bands.map((item) => [x(item.trade_index), y(item[high])]))} ${bands
      .slice()
      .reverse()
      .map((item) => `L${x(item.trade_index).toFixed(2)},${y(item[low]).toFixed(2)}`)
      .join(" ")} Z`;
  const hovered = hoverIndex !== null ? bands[hoverIndex] : null;
  const median = bands[bands.length - 1];

  function handlePointer(event: PointerEvent<HTMLDivElement>) {
    const target = pointerFraction(event) * lastTrade;
    let nearest = 0;
    bands.forEach((item, index) => {
      if (Math.abs(item.trade_index - target) < Math.abs(bands[nearest].trade_index - target)) {
        nearest = index;
      }
    });
    setHoverIndex(nearest);
  }

  return (
    <div>
      <div
        className="relative h-40 w-full touch-none select-none"
        onPointerMove={handlePointer}
        onPointerLeave={() => setHoverIndex(null)}
        role="img"
        aria-label={`Monte Carlo fan: median ${median.p50.toFixed(2)}x after ${lastTrade} trades, 90% range ${median.p5.toFixed(2)}x to ${median.p95.toFixed(2)}x`}
      >
        <svg viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`} preserveAspectRatio="none" className="absolute inset-0 h-full w-full" aria-hidden>
          <line x1={0} x2={VIEW_WIDTH} y1={y(1)} y2={y(1)} stroke="rgba(148,163,184,0.28)" strokeWidth={1} vectorEffect="non-scaling-stroke" />
          <path d={band("p5", "p95")} fill={LINE_COLOR} fillOpacity={0.1} />
          <path d={band("p25", "p75")} fill={LINE_COLOR} fillOpacity={0.22} />
          <path
            d={linePath(bands.map((item) => [x(item.trade_index), y(item.p50)]))}
            fill="none"
            stroke={LINE_COLOR}
            strokeWidth={2}
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
          {hovered ? (
            <line
              x1={x(hovered.trade_index)}
              x2={x(hovered.trade_index)}
              y1={0}
              y2={VIEW_HEIGHT}
              stroke="rgba(226,232,240,0.45)"
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            />
          ) : null}
        </svg>
        <span
          className="pointer-events-none absolute left-1 rounded bg-slate-950/80 px-1 text-[10px] text-slate-400"
          style={{ top: `${(y(1) / VIEW_HEIGHT) * 100}%`, transform: "translateY(-50%)" }}
        >
          1.00× start
        </span>
        <span
          className="pointer-events-none absolute right-0 rounded bg-slate-950/80 px-1 text-[10px] text-slate-200"
          style={{ top: `${(y(median.p50) / VIEW_HEIGHT) * 100}%`, transform: "translate(0, -130%)" }}
        >
          median {median.p50.toFixed(2)}×
        </span>
        {hovered ? (
          <div
            className="pointer-events-none absolute top-2 z-10 rounded-xl border border-white/10 bg-slate-950/95 px-3 py-2 text-xs shadow-lg"
            style={{
              left: `${(x(hovered.trade_index) / VIEW_WIDTH) * 100}%`,
              transform: hovered.trade_index / lastTrade > 0.6 ? "translateX(calc(-100% - 8px))" : "translateX(8px)",
            }}
          >
            <p className="text-slate-400">After {hovered.trade_index} trades</p>
            <p className="font-semibold text-white">median {formatMoney(hovered.p50 * startingBalance)}</p>
            <p className="text-slate-400">
              50%: {formatMoney(hovered.p25 * startingBalance)} – {formatMoney(hovered.p75 * startingBalance)}
            </p>
            <p className="text-slate-400">
              90%: {formatMoney(hovered.p5 * startingBalance)} – {formatMoney(hovered.p95 * startingBalance)}
            </p>
          </div>
        ) : null}
      </div>
      <div className="mt-2 flex flex-wrap gap-4 text-[11px] text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded bg-cyan-300" /> median path
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-4 rounded-sm bg-cyan-300/30" /> middle 50%
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-4 rounded-sm bg-cyan-300/10" /> middle 90%
        </span>
        <span className="ml-auto">trades →</span>
      </div>
    </div>
  );
}

export function KillReasonBars({ reasons }: { reasons: DeskKillReason[] }) {
  const top = reasons.slice(0, 8);
  const max = Math.max(...top.map((reason) => reason.count), 1);

  return (
    <ul className="space-y-3">
      {top.map((reason) => (
        <li key={`${reason.agent}-${reason.code}`} className="text-xs">
          <span className="block text-slate-300">
            {reason.label}
            <span className="ml-1 capitalize text-slate-500">· {reason.agent}</span>
          </span>
          <span className="mt-1 flex items-center gap-2">
            <span
              className="h-3 rounded-r bg-cyan-300/70"
              style={{ width: `${Math.max((reason.count / max) * 85, 2)}%` }}
            />
            <span className="tabular-nums text-slate-200">{reason.count.toLocaleString()}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

export function ScoutRadar({
  symbols,
  frame,
  active,
}: {
  symbols: string[];
  frame: DeskFrame | null;
  active: boolean;
}) {
  const center = 100;
  const radius = 70;
  const openBySymbol = new Map(frame?.positions.map((position) => [position.symbol, position]) ?? []);
  const scansBySymbol = new Map(frame?.scans.map((scan) => [scan.symbol, scan]) ?? []);

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 200" className="h-40 w-40" role="img" aria-label={`Scout radar over ${symbols.join(", ")}`}>
        <defs>
          <radialGradient id="radar-sweep" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(100 100) scale(90)">
            <stop offset="0" stopColor="#67e8f9" stopOpacity="0.35" />
            <stop offset="1" stopColor="#67e8f9" stopOpacity="0" />
          </radialGradient>
        </defs>
        {[30, 60, 90].map((ring) => (
          <circle key={ring} cx={center} cy={center} r={ring} fill="none" stroke="rgba(148,163,184,0.18)" strokeWidth={1} />
        ))}
        <line x1={10} x2={190} y1={center} y2={center} stroke="rgba(148,163,184,0.12)" />
        <line x1={center} x2={center} y1={10} y2={190} stroke="rgba(148,163,184,0.12)" />
        <g
          className={clsx(active && "motion-safe:animate-[spin_3.2s_linear_infinite]")}
          style={{ transformOrigin: "100px 100px", transformBox: "view-box" }}
        >
          <path d="M100 100 L100 10 A90 90 0 0 1 163.6 36.4 Z" fill="url(#radar-sweep)" />
          <line x1={center} y1={center} x2={center} y2={10} stroke="#67e8f9" strokeOpacity={0.7} strokeWidth={1.5} />
        </g>
        {symbols.map((symbol, index) => {
          const angle = (index / symbols.length) * Math.PI * 2 - Math.PI / 2;
          const position = openBySymbol.get(symbol);
          const scan = scansBySymbol.get(symbol);
          const distance = position ? radius * 0.55 : radius;
          const cx = center + Math.cos(angle) * distance;
          const cy = center + Math.sin(angle) * distance;
          const fill = position
            ? position.unrealized >= 0
              ? "#34d399"
              : "#fb7185"
            : scan?.status === "ordered"
              ? "#67e8f9"
              : "#475569";
          return (
            <g key={symbol}>
              {scan ? (
                <circle
                  cx={cx}
                  cy={cy}
                  r={9}
                  fill="none"
                  stroke={scan.status === "ordered" ? "#67e8f9" : "#fb7185"}
                  strokeOpacity={0.7}
                  strokeWidth={1.5}
                />
              ) : null}
              <circle cx={cx} cy={cy} r={position ? 5 : 4} fill={fill} stroke="#020617" strokeWidth={2} />
              <text
                x={cx}
                y={cy + (Math.sin(angle) > 0.3 ? 18 : -10)}
                textAnchor="middle"
                className="fill-slate-300 text-[9px] font-medium"
              >
                {symbol}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="mt-1 text-[10px] uppercase tracking-[0.2em] text-slate-500">Scout radar</p>
    </div>
  );
}
