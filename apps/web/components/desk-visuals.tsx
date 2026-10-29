"use client";

import { useState, type PointerEvent } from "react";
import clsx from "clsx";

import type { DeskAgent, DeskEvent, DeskFrame, DeskPipelineCounts, DeskRun, DeskTrade } from "@tradenoc/types";
import { AgentIcon } from "@/components/desk-panels";
import {
  DESK_AGENTS,
  formatMoney,
  formatPercent,
  formatR,
  formatSigned,
  formatSignedMoney,
  type DeskView,
} from "@/lib/desk";

const ALERT_KINDS = new Set(["veto", "halt", "cooldown"]);
const ALERT_WINDOW_BARS = 6;
const SPARK_BARS = 40;

function sessionWindow(run: DeskRun, step: number): { start: number; end: number; length: number } {
  const index = Math.max(0, Math.min(step, run.frames.length - 1));
  const session = run.frames[index].session;
  let start = index;
  while (start > 0 && run.frames[start - 1].session === session) {
    start -= 1;
  }
  let end = index;
  while (end < run.frames.length - 1 && run.frames[end + 1].session === session) {
    end += 1;
  }
  return { start, end, length: end - start + 1 };
}

/** One row of live numbers across the top of the console, like a terminal ticker. */
export function TickerStrip({ run, view, step }: { run: DeskRun; view: DeskView; step: number }) {
  const { start } = sessionWindow(run, step);
  const chips: Array<{ label: string; value: string; tone?: "up" | "down" }> = [
    { label: "Equity", value: `${view.multiple.toFixed(3)}×`, tone: view.pnl > 0 ? "up" : view.pnl < 0 ? "down" : undefined },
    { label: "P&L", value: formatSignedMoney(view.pnl), tone: view.pnl > 0 ? "up" : view.pnl < 0 ? "down" : undefined },
    { label: "Open", value: `${view.frame.positions.length}/${run.config.max_open_positions}` },
    { label: "Win", value: view.winRate === null ? "—" : formatPercent(view.winRate) },
    {
      label: "Exp",
      value: view.closedTrades.length
        ? formatR(view.closedTrades.reduce((total, trade) => total + trade.r_multiple, 0) / view.closedTrades.length)
        : "—",
    },
    { label: "DD", value: view.maxDrawdownPct > 0 ? `−${view.maxDrawdownPct.toFixed(1)}%` : "0.0%", tone: view.maxDrawdownPct > 0 ? "down" : undefined },
    { label: "Flagged", value: view.frame.pipeline.scout_flagged.toLocaleString() },
    { label: "AI", value: `${view.frame.pipeline.seat_ai_calls}/${run.config.use_ai_seat ? run.config.ai_seat_budget : 0}` },
  ];

  return (
    <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 font-mono text-[11px] sm:flex-wrap" aria-label="Live desk numbers">
      {chips.map((chip) => (
        <span key={chip.label} className="flex shrink-0 items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1">
          <span className="uppercase tracking-[0.14em] text-slate-500">{chip.label}</span>
          <span className={clsx("font-semibold", chip.tone === "up" ? "text-emerald-300" : chip.tone === "down" ? "text-rose-300" : "text-white")}>
            {chip.value}
          </span>
        </span>
      ))}
      {run.config.symbols.map((symbol) => {
        const bars = run.tape?.[symbol];
        const last = bars?.[Math.min(step, bars.length - 1)];
        const open = bars?.[start];
        if (!last || !open) {
          return null;
        }
        const change = (last[3] - open[0]) / open[0];
        const flow = view.frame.flow?.[symbol] ?? 0;
        return (
          <span key={symbol} className="flex shrink-0 items-center gap-1.5 rounded-full border border-white/10 bg-slate-950/60 px-2.5 py-1">
            <span className="font-semibold text-white">{symbol}</span>
            <span className="text-slate-300">{last[3].toFixed(2)}</span>
            <span className={change >= 0 ? "text-emerald-300" : "text-rose-300"}>{formatSigned(change * 100, 2, "%")}</span>
            <span className="text-slate-500" title={`Order flow imbalance ${formatSigned(flow, 2)}`}>
              {flow >= 0.2 ? "▲" : flow <= -0.2 ? "▼" : "•"}
            </span>
          </span>
        );
      })}
    </div>
  );
}

/** The most recent veto, halt, or cooldown within the last few bars. */
export function AlertBanner({ events, step }: { events: DeskEvent[]; step: number }) {
  const alert = [...events]
    .reverse()
    .find((event) => event.step <= step && event.step > step - ALERT_WINDOW_BARS && ALERT_KINDS.has(event.kind));
  if (!alert) {
    return null;
  }
  const severe = alert.kind === "halt";

  return (
    <div
      className={clsx(
        "flex items-start gap-3 rounded-2xl border px-4 py-3",
        severe ? "border-rose-300/40 bg-rose-500/10" : "border-amber-300/30 bg-amber-400/10",
      )}
      role="status"
    >
      <span
        className={clsx(
          "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-xs font-bold",
          severe ? "bg-rose-400 text-slate-950" : "bg-amber-300 text-slate-950",
        )}
        aria-hidden
      >
        !
      </span>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-white">
          Flagged for review · <span className="capitalize">{alert.agent === "seat" ? "Skeptic" : alert.agent}</span>
          {alert.symbol ? ` · ${alert.symbol}` : ""}
        </p>
        <p className="mt-0.5 text-xs text-slate-300">{alert.message}</p>
      </div>
      <span className="ml-auto shrink-0 font-mono text-xs text-slate-400">{alert.clock}</span>
    </div>
  );
}

export function MilestoneLadder({ run, view }: { run: DeskRun; view: DeskView }) {
  const milestones = run.config.milestones?.length ? run.config.milestones : [1.01, 1.02, 1.05, 1.1];
  // Evenly spaced rungs (like a 2x/3x/5x/10x ladder); progress interpolates within the current rung.
  const fraction = (multiple: number) => {
    const rungs = [1, ...milestones];
    if (multiple <= 1) {
      return 0;
    }
    for (let index = 1; index < rungs.length; index += 1) {
      if (multiple <= rungs[index]) {
        return (index - 1 + (multiple - rungs[index - 1]) / (rungs[index] - rungs[index - 1])) / milestones.length;
      }
    }
    return 1;
  };
  const position = (multiple: number) => `${fraction(multiple) * 100}%`;
  const next = milestones.find((milestone) => view.multiple < milestone);
  const start = run.summary.starting_balance;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-white">
          Milestones {next ? <span className="text-slate-400">· next {next}×</span> : <span className="text-emerald-300">· all reached</span>}
        </p>
        <p className="text-xs text-slate-400">
          {view.multiple < 1
            ? `${formatMoney(start - view.frame.equity)} below start`
            : next
              ? `${formatMoney(next * start - view.frame.equity)} to go`
              : "Checkpoints, not targets"}
        </p>
      </div>
      <div className="relative mt-5 h-6">
        <span className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-white/10" />
        <span
          className="absolute left-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-emerald-400"
          style={{ width: position(view.multiple) }}
        />
        {milestones.map((milestone) => {
          const reached = view.multiple >= milestone;
          return (
            <span key={milestone} className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2" style={{ left: position(milestone) }}>
              <span
                className={clsx(
                  "block h-3.5 w-3.5 rounded-full border-2",
                  reached ? "border-emerald-300 bg-emerald-400" : "border-slate-500 bg-slate-950",
                )}
              />
              <span className="absolute left-1/2 top-5 -translate-x-1/2 font-mono text-[10px] text-slate-400">{milestone}×</span>
            </span>
          );
        })}
        <span
          className="absolute top-1/2 rounded-full bg-white px-1.5 font-mono text-[10px] font-bold text-slate-950"
          style={{ left: position(view.multiple), transform: `translate(-${fraction(view.multiple) * 100}%, -50%)` }}
        >
          {view.multiple.toFixed(3)}×
        </span>
      </div>
      <p className="mt-6 text-[11px] text-slate-500">Checkpoints, not targets. In live mode each one pauses new entries until you choose to continue.</p>
    </div>
  );
}

const COUNTERS: Partial<Record<DeskAgent, keyof DeskPipelineCounts>> = {
  scout: "scout_flagged",
  filter: "filter_killed",
  analyst: "analyst_scored",
  risk: "risk_sized",
  seat: "seat_reviews",
  executor: "executor_fills",
  logger: "logger_reasons",
};

const STATUS_WORDS: Record<DeskAgent, string> = {
  scout: "scan",
  flow: "signal",
  filter: "gate",
  analyst: "score",
  risk: "size",
  seat: "review",
  executor: "paper",
  logger: "log",
};

function formulaFor(agent: DeskAgent, run: DeskRun): string {
  const config = run.config;
  switch (agent) {
    case "scout":
      return "C > max(H₂₀) ∧ V ≥ 1.3·V̄";
    case "flow":
      return "F = Σλᵏ·sᵥ / Σλᵏ·v · 24 lags";
    case "filter":
      return `R:R ≥ ${config.min_reward_risk} · open < ${config.max_open_positions} · |F| veto ${config.flow_veto}`;
    case "analyst":
      return "p = (α+w)/(α+β+n) · EV = p·b − q";
    case "risk":
      return `f = min(${config.risk_per_trade_pct}%, ${config.kelly_fraction}·(p − q/b))`;
    case "seat":
      return `veto if max P(yes) ≥ ${config.seat_veto.toFixed(2)}`;
    case "executor":
      return `fill = open·(1 ± ${config.slippage_bps}bp) · ${config.fee_bps}bp fee`;
    case "logger":
      return "every decision → a reason";
  }
}

function headlineFor(agent: DeskAgent, frame: DeskFrame): string {
  const p = frame.pipeline;
  switch (agent) {
    case "flow": {
      const entries = Object.entries(frame.flow ?? {});
      if (!entries.length) {
        return "no readings";
      }
      const [symbol, value] = entries.reduce((best, entry) => (Math.abs(entry[1]) > Math.abs(best[1]) ? entry : best));
      return `${symbol} ${formatSigned(value, 2)} · ${p.flow_vetoes} vetoes`;
    }
    case "seat":
      return `${p.seat_reviews} reviewed · ${p.seat_vetoes} vetoed`;
    case "risk":
      return `${p.risk_sized} sized · ${p.risk_rejected} rejected`;
    case "executor":
      return `${p.executor_fills} fills · ${p.executor_exits} exits`;
    default: {
      const meta = DESK_AGENTS.find((item) => item.id === agent);
      return meta ? meta.count(p) : "";
    }
  }
}

function Sparkline({ values, signed = false }: { values: number[]; signed?: boolean }) {
  if (!values.length) {
    return <div className="h-7" />;
  }
  if (signed) {
    const points = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${14 - value * 12}`).join(" ");
    return (
      <svg viewBox="0 0 100 28" preserveAspectRatio="none" className="h-7 w-full" aria-hidden>
        <line x1={0} x2={100} y1={14} y2={14} stroke="rgba(148,163,184,0.25)" strokeWidth={1} vectorEffect="non-scaling-stroke" />
        <polyline points={points} fill="none" stroke="#67e8f9" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      </svg>
    );
  }
  const max = Math.max(...values, 1);
  const width = 100 / SPARK_BARS;
  return (
    <svg viewBox="0 0 100 28" preserveAspectRatio="none" className="h-7 w-full" aria-hidden>
      {values.map((value, index) => (
        <rect
          key={index}
          x={(SPARK_BARS - values.length + index) * width}
          y={28 - (value / max) * 26}
          width={width * 0.7}
          height={(value / max) * 26}
          fill={value > 0 ? "#67e8f9" : "rgba(148,163,184,0.2)"}
          fillOpacity={value > 0 ? 0.75 : 1}
        />
      ))}
    </svg>
  );
}

/** Per-agent module cards: formula, live status, headline number, and recent activity. */
export function AgentCards({ run, step }: { run: DeskRun; step: number }) {
  const index = Math.max(0, Math.min(step, run.frames.length - 1));
  const frame = run.frames[index];
  const recent = run.frames.slice(Math.max(0, index - SPARK_BARS), index + 1);
  const activeAgents = new Set(run.events.filter((event) => event.step === frame.step).map((event) => event.agent));
  const strongest = Object.entries(frame.flow ?? {}).reduce<[string, number] | null>(
    (best, entry) => (!best || Math.abs(entry[1]) > Math.abs(best[1]) ? entry : best),
    null,
  );

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {DESK_AGENTS.map((agent) => {
        const counter = COUNTERS[agent.id];
        const values =
          agent.id === "flow"
            ? recent.slice(1).map((item) => (strongest ? (item.flow?.[strongest[0]] ?? 0) : 0))
            : counter
              ? recent.slice(1).map((item, offset) => Math.max(0, (item.pipeline[counter] as number) - (recent[offset].pipeline[counter] as number)))
              : [];
        const active = activeAgents.has(agent.id) || (agent.id === "flow" && strongest !== null && Math.abs(strongest[1]) >= 0.5);
        return (
          <div
            key={agent.id}
            className={clsx(
              "rounded-2xl border bg-slate-950/50 p-3 transition",
              active ? "border-cyan-300/50 shadow-[0_0_24px_rgba(103,232,249,0.12)]" : "border-white/10",
            )}
            title={agent.role}
          >
            <div className="flex items-center gap-2">
              <span className={clsx("flex h-7 w-7 items-center justify-center rounded-lg", active ? "bg-cyan-300/15 text-cyan-200" : "bg-white/5 text-slate-300")}>
                <AgentIcon agent={agent.id} className="h-4 w-4" />
              </span>
              <span className="text-sm font-semibold text-white">{agent.label}</span>
              <span
                className={clsx(
                  "ml-auto rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                  active ? "bg-cyan-300/15 text-cyan-100" : "bg-white/5 text-slate-500",
                )}
              >
                {active ? STATUS_WORDS[agent.id] : "idle"}
              </span>
            </div>
            <p className="mt-2 truncate font-mono text-[10px] text-slate-500" title={formulaFor(agent.id, run)}>
              {formulaFor(agent.id, run)}
            </p>
            <div className="mt-2">
              <Sparkline values={values} signed={agent.id === "flow"} />
            </div>
            <p className="mt-1 text-xs text-slate-300">{headlineFor(agent.id, frame)}</p>
          </div>
        );
      })}
    </div>
  );
}

const CHART_HEIGHT = 220;
const PRICE_BAND = 0.78;

function tradeMarkers(trades: DeskTrade[], symbol: string, start: number, end: number) {
  return trades.filter((trade) => trade.symbol === symbol && trade.close_step >= start && trade.open_step <= end);
}

/** Candles for the current session of one symbol, with paper entries, exits, and live stop/target lines. */
export function CandlestickChart({ run, step }: { run: DeskRun; step: number }) {
  const symbols = run.config.symbols.filter((symbol) => run.tape?.[symbol]?.length);
  const [selected, setSelected] = useState<string | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const symbol = selected && symbols.includes(selected) ? selected : (symbols[0] ?? null);
  if (!symbol) {
    return <p className="text-sm text-slate-500">This run has no bar data to chart. Re-run it to include candles.</p>;
  }

  const index = Math.max(0, Math.min(step, run.frames.length - 1));
  const { start, length } = sessionWindow(run, index);
  const bars = run.tape[symbol].slice(start, index + 1);
  const position = run.frames[index].positions.find((item) => item.symbol === symbol);
  const trades = tradeMarkers(run.trades, symbol, start, run.frames[index].step);
  const lows = bars.map((bar) => bar[2]);
  const highs = bars.map((bar) => bar[1]);
  const levels = position ? [position.stop, position.target, position.entry] : [];
  const min = Math.min(...lows, ...levels);
  const max = Math.max(...highs, ...levels);
  const pad = (max - min) * 0.08 || max * 0.002;
  const yMin = min - pad;
  const yMax = max + pad;
  const width = length * 10;
  const priceHeight = CHART_HEIGHT * PRICE_BAND;
  const y = (price: number) => priceHeight - ((price - yMin) / (yMax - yMin)) * priceHeight;
  const maxVolume = Math.max(...bars.map((bar) => bar[4]), 1);
  const stepToX = (frameStep: number) => (frameStep - run.frames[start].step) * 10 + 5;
  const hovered = hover !== null ? bars[hover] : null;
  const hoverFrame = hover !== null ? run.frames[start + hover] : null;

  function handlePointer(event: PointerEvent<HTMLDivElement>) {
    const bounds = event.currentTarget.getBoundingClientRect();
    const slot = Math.floor(((event.clientX - bounds.left) / bounds.width) * length);
    setHover(slot >= 0 && slot < bars.length ? slot : null);
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Chart symbol">
        {symbols.map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={item === symbol}
            onClick={() => setSelected(item)}
            className={clsx(
              "rounded-full border px-2.5 py-1 text-xs transition",
              item === symbol ? "border-cyan-300/60 bg-cyan-300/10 text-white" : "border-white/10 text-slate-400 hover:text-white",
            )}
          >
            {item}
          </button>
        ))}
        <span className="ml-auto flex items-center gap-3 text-[11px] text-slate-400">
          <span className="flex items-center gap-1"><span className="text-emerald-300">▲</span>long entry</span>
          <span className="flex items-center gap-1"><span className="text-rose-300">▼</span>short entry</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full border border-white bg-emerald-400" />exit</span>
        </span>
      </div>
      <div
        className="relative mt-3 w-full touch-none select-none"
        style={{ height: CHART_HEIGHT }}
        onPointerMove={handlePointer}
        onPointerLeave={() => setHover(null)}
        role="img"
        aria-label={`${symbol} 5-minute candles for the current session with paper trade markers`}
      >
        <svg viewBox={`0 0 ${width} ${CHART_HEIGHT}`} preserveAspectRatio="none" className="absolute inset-0 h-full w-full" aria-hidden>
          {bars.map((bar, slot) => {
            const [open, high, low, close, volume] = bar;
            const up = close >= open;
            const x = slot * 10;
            const bodyTop = y(Math.max(open, close));
            const bodyHeight = Math.max(Math.abs(y(open) - y(close)), 0.6);
            const color = up ? "#34d399" : "#fb7185";
            return (
              <g key={slot}>
                <rect
                  x={x + 2}
                  y={CHART_HEIGHT - ((volume / maxVolume) * CHART_HEIGHT * (1 - PRICE_BAND) * 0.9)}
                  width={6}
                  height={(volume / maxVolume) * CHART_HEIGHT * (1 - PRICE_BAND) * 0.9}
                  fill="rgba(148,163,184,0.28)"
                />
                <line x1={x + 5} x2={x + 5} y1={y(high)} y2={y(low)} stroke={color} strokeWidth={1} vectorEffect="non-scaling-stroke" />
                <rect
                  x={x + 2}
                  y={bodyTop}
                  width={6}
                  height={bodyHeight}
                  fill={up ? "#050a14" : color}
                  stroke={color}
                  strokeWidth={1}
                  vectorEffect="non-scaling-stroke"
                />
              </g>
            );
          })}
          {position
            ? [
                { price: position.entry, color: "rgba(226,232,240,0.6)" },
                { price: position.stop, color: "#fb7185" },
                { price: position.target, color: "#34d399" },
              ].map((line) => (
                <line
                  key={line.color}
                  x1={0}
                  x2={width}
                  y1={y(line.price)}
                  y2={y(line.price)}
                  stroke={line.color}
                  strokeWidth={1}
                  vectorEffect="non-scaling-stroke"
                />
              ))
            : null}
          {hover !== null ? (
            <line x1={hover * 10 + 5} x2={hover * 10 + 5} y1={0} y2={CHART_HEIGHT} stroke="rgba(226,232,240,0.4)" strokeWidth={1} vectorEffect="non-scaling-stroke" />
          ) : null}
        </svg>

        {trades.map((trade) => {
          const entryX = stepToX(trade.open_step);
          const showExit = trade.close_step <= run.frames[index].step;
          const exitX = stepToX(trade.close_step);
          return (
            <span key={trade.id}>
              {entryX >= 0 ? (
                <span
                  className={clsx("absolute -translate-x-1/2 text-[11px] leading-none", trade.side === "long" ? "text-emerald-300" : "text-rose-300")}
                  style={{
                    left: `${(entryX / width) * 100}%`,
                    top: `${(y(trade.entry) / CHART_HEIGHT) * 100}%`,
                    transform: `translate(-50%, ${trade.side === "long" ? "40%" : "-140%"})`,
                  }}
                  title={`${trade.id} ${trade.side} entry ${trade.entry.toFixed(2)}`}
                >
                  {trade.side === "long" ? "▲" : "▼"}
                </span>
              ) : null}
              {showExit ? (
                <span
                  className={clsx("absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-slate-950", trade.pnl > 0 ? "bg-emerald-400" : "bg-rose-400")}
                  style={{ left: `${(exitX / width) * 100}%`, top: `${(y(trade.exit) / CHART_HEIGHT) * 100}%` }}
                  title={`${trade.id} exit ${trade.exit.toFixed(2)} on ${trade.exit_reason}: ${formatSignedMoney(trade.pnl)} (${formatR(trade.r_multiple)})`}
                />
              ) : null}
            </span>
          );
        })}

        {position
          ? [
              { label: "stop", price: position.stop, className: "text-rose-200 border-rose-300/40" },
              { label: "target", price: position.target, className: "text-emerald-200 border-emerald-300/40" },
            ].map((line) => (
              <span
                key={line.label}
                className={clsx("pointer-events-none absolute right-0 -translate-y-1/2 rounded border bg-slate-950/90 px-1 font-mono text-[10px]", line.className)}
                style={{ top: `${(y(line.price) / CHART_HEIGHT) * 100}%` }}
              >
                {line.label} {line.price.toFixed(2)}
              </span>
            ))
          : null}

        {hovered && hoverFrame ? (
          <div
            className="pointer-events-none absolute top-2 z-10 rounded-xl border border-white/10 bg-slate-950/95 px-3 py-2 font-mono text-[11px] shadow-lg"
            style={{
              left: `${((hover! * 10 + 5) / width) * 100}%`,
              transform: (hover! + 1) / length > 0.6 ? "translateX(calc(-100% - 8px))" : "translateX(8px)",
            }}
          >
            <p className="font-sans text-xs font-semibold text-white">
              {symbol} · {hoverFrame.clock}
            </p>
            <p className="text-slate-300">
              O {hovered[0].toFixed(2)} H {hovered[1].toFixed(2)}
            </p>
            <p className="text-slate-300">
              L {hovered[2].toFixed(2)} C {hovered[3].toFixed(2)}
            </p>
            <p className="text-slate-500">vol {Math.round(hovered[4]).toLocaleString()}</p>
            <p className="text-slate-500">flow {formatSigned(hoverFrame.flow?.[symbol] ?? 0, 2)}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
