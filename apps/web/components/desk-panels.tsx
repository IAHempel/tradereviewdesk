"use client";

import { useState, type ReactNode } from "react";
import clsx from "clsx";

import type {
  DeskAgent,
  DeskConfig,
  DeskDataSourceInfo,
  DeskEvent,
  DeskFrame,
  DeskRun,
  DeskRunSummary,
  DeskSetupEdge,
  DeskTrade,
} from "@tradenoc/types";
import {
  DESK_AGENTS,
  DESK_SETUPS,
  SETUP_LABELS,
  checkClaim,
  formatMoney,
  formatPercent,
  formatR,
  formatRunLabel,
  formatSigned,
  formatSignedMoney,
  latestReplayableDay,
} from "@/lib/desk";

const iconPaths: Record<DeskAgent, ReactNode> = {
  scout: (
    <>
      <circle cx="11" cy="11" r="6" />
      <path d="m20 20-4.5-4.5" />
    </>
  ),
  filter: <path d="M4 5h16l-6 7.5V19l-4 1.5v-8L4 5Z" />,
  analyst: <path d="M5 19V11M10 19V6M15 19v-5M20 19V9" />,
  risk: <path d="M12 3 5 6v5c0 4.5 3 8 7 10 4-2 7-5.5 7-10V6l-7-3Z" />,
  executor: <path d="M13 3 6 13h5l-1 8 7-10h-5l1-8Z" />,
  logger: (
    <>
      <path d="M7 3h7l4 4v14H7V3Z" />
      <path d="M10 11h5M10 15h5" />
    </>
  ),
};

export function AgentIcon({ agent, className }: { agent: DeskAgent; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={clsx("h-5 w-5", className)}
      aria-hidden
    >
      {iconPaths[agent]}
    </svg>
  );
}

function agentForScan(status: "killed" | "ordered"): DeskAgent {
  return status === "ordered" ? "executor" : "filter";
}

export function PipelineStrip({ frame, events, active }: { frame: DeskFrame | null; events: DeskEvent[]; active: boolean }) {
  const chips = new Map<DeskAgent, string[]>();
  for (const scan of frame?.scans ?? []) {
    const agent = agentForScan(scan.status);
    const symbols = chips.get(agent) ?? [];
    if (!symbols.includes(scan.symbol)) {
      chips.set(agent, [...symbols, scan.symbol]);
    }
  }
  const stepEvents = frame ? events.filter((event) => event.step === frame.step) : [];
  const busy = new Set(stepEvents.map((event) => event.agent));
  const pipeline = frame?.pipeline;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-sm font-semibold text-white">Desk pipeline</p>
        {pipeline ? (
          <p className="text-xs text-slate-400">
            {pipeline.scout_flagged.toLocaleString()} flagged ·{" "}
            <span className="font-semibold text-emerald-300">{pipeline.executor_fills.toLocaleString()} traded</span>
          </p>
        ) : null}
      </div>
      <div className="relative mt-4">
        <div className="absolute left-[8%] right-[8%] top-7 h-px bg-gradient-to-r from-cyan-300/10 via-cyan-300/40 to-cyan-300/10" />
        {active ? (
          <div className="absolute left-[8%] right-[8%] top-[27px] h-[3px] overflow-hidden">
            <span className="block h-full w-10 rounded-full bg-cyan-300/80 blur-[1px] motion-safe:animate-[desk-flow_1.6s_linear_infinite]" />
          </div>
        ) : null}
        <ol className="relative grid grid-cols-3 gap-y-4 sm:grid-cols-6">
          {DESK_AGENTS.map((agent) => (
            <li key={agent.id} className="flex flex-col items-center text-center" title={agent.role}>
              <div className="flex h-5 items-end gap-1">
                {(chips.get(agent.id) ?? []).slice(0, 2).map((symbol) => (
                  <span
                    key={symbol}
                    className={clsx(
                      "rounded-full border px-1.5 text-[9px] font-semibold leading-4",
                      agent.id === "executor"
                        ? "border-emerald-300/50 bg-emerald-400/15 text-emerald-100"
                        : "border-rose-300/40 bg-rose-400/10 text-rose-100",
                    )}
                  >
                    {symbol}
                  </span>
                ))}
              </div>
              <span
                className={clsx(
                  "mt-1 flex h-11 w-11 items-center justify-center rounded-full border bg-slate-950 transition",
                  busy.has(agent.id)
                    ? "border-cyan-300/80 text-cyan-200 shadow-[0_0_18px_rgba(103,232,249,0.45)]"
                    : "border-white/15 text-slate-300",
                )}
              >
                <AgentIcon agent={agent.id} />
              </span>
              <span className="mt-2 text-xs font-semibold text-white">{agent.label}</span>
              <span className="text-[10px] text-slate-400">{pipeline ? agent.count(pipeline) : "idle"}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

export function PositionsPanel({ frame, run }: { frame: DeskFrame | null; run: DeskRun }) {
  const positions = frame?.positions ?? [];
  const tradesById = new Map(run.trades.map((trade) => [trade.id, trade]));

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="whitespace-nowrap text-sm font-semibold text-white">Open positions</p>
        <p className="text-right text-xs text-slate-400">
          {positions.length}/{run.config.max_open_positions} open · stop −1R · trail +{run.config.trail_after_r}R
        </p>
      </div>
      {positions.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">{frame?.halted ? "Desk halted for the session. Flat." : "Flat. Waiting for a setup that survives the filter."}</p>
      ) : (
        <ul className="mt-3 space-y-3">
          {positions.map((position) => {
            const trade = tradesById.get(position.trade_id);
            const riskUnit = trade ? Math.abs(position.entry - trade.stop_initial) : Math.abs(position.entry - position.stop);
            const targetR = riskUnit > 0 ? Math.abs(position.target - position.entry) / riskUnit : 2;
            const stopR = riskUnit > 0 ? ((position.side === "long" ? 1 : -1) * (position.stop - position.entry)) / riskUnit : -1;
            const span = targetR + 1;
            const at = (r: number) => `${((Math.max(-1, Math.min(targetR, r)) + 1) / span) * 100}%`;
            const zero = at(0);
            const now = at(position.r_now);
            return (
              <li key={position.trade_id} className="grid grid-cols-[3.25rem_3.5rem_1fr_4.5rem] items-center gap-3">
                <span
                  className={clsx(
                    "rounded-md px-1.5 py-0.5 text-center text-[10px] font-bold tracking-wider",
                    position.side === "long" ? "bg-emerald-400/15 text-emerald-200" : "bg-rose-400/15 text-rose-200",
                  )}
                >
                  {position.side.toUpperCase()}
                </span>
                <span className="truncate text-sm font-semibold text-white" title={SETUP_LABELS[position.setup]}>
                  {position.symbol}
                </span>
                <span className="relative h-6" title={`Stop ${position.stop.toFixed(2)} · entry ${position.entry.toFixed(2)} · target ${position.target.toFixed(2)}`}>
                  <span className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-white/10" />
                  <span
                    className={clsx(
                      "absolute top-1/2 h-1 -translate-y-1/2 rounded-full",
                      position.r_now >= 0 ? "bg-emerald-400" : "bg-rose-400",
                    )}
                    style={
                      position.r_now >= 0
                        ? { left: zero, width: `calc(${now} - ${zero})` }
                        : { left: now, width: `calc(${zero} - ${now})` }
                    }
                  />
                  <span className="absolute top-1/2 h-3 w-px -translate-y-1/2 bg-slate-400" style={{ left: zero }} />
                  <span className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-rose-300" style={{ left: at(stopR) }} />
                  <span className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-emerald-300" style={{ left: "100%" }} />
                  <span
                    className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white ring-2 ring-slate-950"
                    style={{ left: now }}
                  />
                  <span className="absolute -top-2 -translate-x-1/2 text-[9px] text-slate-300" style={{ left: now }}>
                    {formatR(position.r_now)}
                  </span>
                </span>
                <span
                  className={clsx(
                    "text-right text-sm font-semibold tabular-nums",
                    position.unrealized >= 0 ? "text-emerald-300" : "text-rose-300",
                  )}
                >
                  {formatSignedMoney(position.unrealized)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

const exitLabels: Record<DeskTrade["exit_reason"], string> = {
  stop: "stop −1R",
  trail: "trailed stop",
  target: "target",
  bell: "flat at bell",
};

export function ClosedTradesPanel({ trades, wins, losses }: { trades: DeskTrade[]; wins: number; losses: number }) {
  const latest = trades.slice(-5).reverse();
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-sm font-semibold text-white">Closed trades</p>
        <p className="text-xs font-semibold text-slate-300">
          {wins}W / {losses}L
        </p>
      </div>
      {latest.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">No closed trades yet.</p>
      ) : (
        <ul className="mt-3 space-y-1.5 text-xs">
          {latest.map((trade) => (
            <li
              key={trade.id}
              className="grid grid-cols-[3rem_3.5rem_1fr_4.5rem] items-center gap-2 sm:grid-cols-[3rem_3.5rem_3.5rem_1fr_4.5rem]"
              title={trade.thesis}
            >
              <span className="tabular-nums text-slate-500">{trade.closed_at}</span>
              <span className="font-semibold text-white">{trade.symbol}</span>
              <span className={clsx("tabular-nums", trade.r_multiple >= 0 ? "text-emerald-300" : "text-rose-300")}>
                {formatR(trade.r_multiple)}
              </span>
              <span className="hidden truncate text-slate-400 sm:block">
                {trade.side} · {SETUP_LABELS[trade.setup].toLowerCase()} · {exitLabels[trade.exit_reason]}
              </span>
              <span
                className={clsx("text-right font-semibold tabular-nums", trade.pnl >= 0 ? "text-emerald-300" : "text-rose-300")}
              >
                {formatSignedMoney(trade.pnl)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function StatTile({ label, value, tone = "default", hint }: { label: string; value: string; tone?: "default" | "up" | "down"; hint?: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2" title={hint}>
      <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p
        className={clsx(
          "mt-1 text-lg font-semibold",
          tone === "up" && "text-emerald-300",
          tone === "down" && "text-rose-300",
          tone === "default" && "text-white",
        )}
      >
        {value}
      </p>
    </div>
  );
}

export function ActivityFeed({ events, step }: { events: DeskEvent[]; step: number }) {
  const [agentFilter, setAgentFilter] = useState<DeskAgent | "all">("all");
  const visible = events
    .filter((event) => event.step <= step && (agentFilter === "all" || event.agent === agentFilter))
    .slice(-60)
    .reverse();

  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        {(["all", ...DESK_AGENTS.map((agent) => agent.id)] as const).map((agent) => (
          <button
            key={agent}
            type="button"
            onClick={() => setAgentFilter(agent)}
            className={clsx(
              "rounded-full border px-2.5 py-1 text-[11px] capitalize transition",
              agentFilter === agent
                ? "border-cyan-300/60 bg-cyan-300/10 text-white"
                : "border-white/10 text-slate-400 hover:border-white/25 hover:text-slate-200",
            )}
          >
            {agent}
          </button>
        ))}
      </div>
      <ol className="mt-3 max-h-80 space-y-1.5 overflow-y-auto pr-1 text-xs" aria-live="off">
        {visible.length === 0 ? <li className="text-slate-500">No activity yet.</li> : null}
        {visible.map((event, index) => (
          <li key={`${event.step}-${index}-${event.kind}`} className="grid grid-cols-[3.5rem_1fr] gap-2 sm:grid-cols-[3.5rem_5.5rem_1fr]">
            <span className="tabular-nums text-slate-500">
              {event.session > 0 ? `S${event.session} ` : ""}
              {event.clock}
            </span>
            <span className="hidden items-center gap-1 capitalize text-slate-300 sm:flex">
              <AgentIcon agent={event.agent} className="h-3.5 w-3.5 text-slate-400" />
              {event.agent}
            </span>
            <span className="text-slate-300">
              <AgentIcon agent={event.agent} className="mr-1 inline h-3.5 w-3.5 align-[-2px] text-slate-400 sm:hidden" />
              {event.symbol ? <span className="mr-1 font-semibold text-white">{event.symbol}</span> : null}
              {event.message}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function SetupEdgeBoard({ edges }: { edges: DeskSetupEdge[] }) {
  return (
    <div>
      <table className="w-full text-left text-xs">
        <thead className="whitespace-nowrap text-[10px] uppercase tracking-[0.16em] text-slate-500">
          <tr>
            <th className="pb-2 font-medium">Setup</th>
            <th className="hidden pb-2 font-medium sm:table-cell" title="Starting assumption, in pseudo-trades">Prior</th>
            <th className="hidden pb-2 font-medium sm:table-cell" title="Your tagged journal trades">Journal</th>
            <th className="pb-2 font-medium">This run</th>
            <th className="pb-2 text-right font-medium">Win est.</th>
            <th className="pb-2 text-right font-medium">Avg R</th>
          </tr>
        </thead>
        <tbody className="whitespace-nowrap tabular-nums">
          {edges.map((edge) => (
            <tr key={edge.setup} className={clsx("border-t border-white/5", !edge.enabled && "opacity-40")}>
              <td className="whitespace-normal py-2 pr-2 font-medium text-white">
                {SETUP_LABELS[edge.setup]}
                {!edge.enabled ? <span className="ml-1 text-slate-500">(off)</span> : null}
              </td>
              <td className="hidden py-2 text-slate-400 sm:table-cell">
                {edge.prior_wins.toFixed(1)}W / {edge.prior_losses.toFixed(1)}L
              </td>
              <td className="hidden py-2 text-slate-400 sm:table-cell">
                {edge.journal_wins}W / {edge.journal_losses}L
              </td>
              <td className="py-2 text-slate-300">
                {edge.live_wins}W / {edge.live_losses}L
              </td>
              <td className="py-2 text-right font-semibold text-white">{formatPercent(edge.posterior_win_rate, 1)}</td>
              <td
                className={clsx(
                  "py-2 text-right",
                  edge.avg_r === null ? "text-slate-500" : edge.avg_r >= 0 ? "text-emerald-300" : "text-rose-300",
                )}
              >
                {edge.avg_r === null ? "—" : formatR(edge.avg_r)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const fieldClass =
  "w-full rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-300/60";

export function ClaimCheckCard({ run }: { run: DeskRun | null }) {
  const [start, setStart] = useState("142");
  const [end, setEnd] = useState("2870");
  const [days, setDays] = useState("6");
  const claim = checkClaim(Number(start), Number(end), Number(days), run);

  return (
    <div>
      <p className="text-sm text-slate-300">
        Paste the numbers from a screenshot you saw. This shows what they imply and how they compare with what your rules
        actually did.
      </p>
      <div className="mt-4 grid grid-cols-3 gap-3">
        <label className="grid gap-1 text-xs text-slate-400">
          Start ($)
          <input inputMode="decimal" value={start} onChange={(event) => setStart(event.target.value)} className={fieldClass} />
        </label>
        <label className="grid gap-1 text-xs text-slate-400">
          End ($)
          <input inputMode="decimal" value={end} onChange={(event) => setEnd(event.target.value)} className={fieldClass} />
        </label>
        <label className="grid gap-1 text-xs text-slate-400">
          Days
          <input inputMode="decimal" value={days} onChange={(event) => setDays(event.target.value)} className={fieldClass} />
        </label>
      </div>
      {claim ? (
        <ul className="mt-4 space-y-2 text-sm text-slate-300">
          <li>
            That is a <span className="font-semibold text-white">{claim.multiple.toFixed(1)}×</span> account, or{" "}
            <span className="font-semibold text-white">{formatSigned(claim.dailyReturn * 100, 1, "%")} every day</span>, compounded
            without a single down day.
          </li>
          {claim.dailyReturn > 0 ? (
            <li>
              Sustained for a year of 252 sessions, that rate would turn $1 into{" "}
              <span className="font-semibold text-white">
                {(1 + claim.dailyReturn) ** 252 > 1e12
                  ? "more than a trillion dollars"
                  : formatMoney((1 + claim.dailyReturn) ** 252)}
              </span>
              .
            </li>
          ) : null}
          {run ? (
            claim.tradesNeeded !== null ? (
              <li>
                At this run&apos;s expectancy ({formatR(run.summary.expectancy_r ?? 0)} per trade at your risk size), reaching{" "}
                {claim.multiple.toFixed(1)}× takes about{" "}
                <span className="font-semibold text-white">{Math.ceil(claim.tradesNeeded).toLocaleString()} trades</span>
                {claim.daysAtThisPace !== null ? ` (~${Math.ceil(claim.daysAtThisPace).toLocaleString()} sessions at this pace)` : ""}, and
                only if the edge holds exactly, which the fan above says it won&apos;t.
              </li>
            ) : (
              <li>
                This run&apos;s expectancy is{" "}
                <span className="font-semibold text-white">{formatR(run.summary.expectancy_r ?? 0)}</span> per trade, so at
                this pace your rules never get there.
              </li>
            )
          ) : (
            <li className="text-slate-500">Run a paper session to compare the claim with your own rules.</li>
          )}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-slate-500">Enter a positive start, end, and number of days.</p>
      )}
    </div>
  );
}

export function RunHistory({
  runs,
  activeId,
  onSelect,
  loadingId,
}: {
  runs: DeskRunSummary[];
  activeId: string | null;
  onSelect: (runId: string) => void;
  loadingId: string | null;
}) {
  if (runs.length === 0) {
    return <p className="text-sm text-slate-500">Saved paper sessions show up here.</p>;
  }

  return (
    <ul className="space-y-2">
      {runs.map((run) => (
        <li key={run.id}>
          <button
            type="button"
            onClick={() => onSelect(run.id)}
            className={clsx(
              "grid w-full grid-cols-[1fr_auto] gap-x-3 rounded-xl border px-3 py-2 text-left text-xs transition",
              run.id === activeId ? "border-cyan-300/50 bg-cyan-300/10" : "border-white/10 hover:border-white/25",
            )}
          >
            <span className="font-medium text-white">{formatRunLabel(run.created_at)}</span>
            <span
              className={clsx("text-right font-semibold tabular-nums", run.summary.net_pnl >= 0 ? "text-emerald-300" : "text-rose-300")}
            >
              {formatSignedMoney(run.summary.net_pnl)}
            </span>
            <span className="text-slate-400">
              {loadingId === run.id
                ? "Loading…"
                : `${runTapeSummary(run)} · ${run.summary.trades} trades`}
            </span>
            <span className="text-right tabular-nums text-slate-400">{run.summary.multiple.toFixed(3)}×</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function runTapeSummary(run: DeskRunSummary): string {
  const sessions = `${run.config.sessions} session${run.config.sessions === 1 ? "" : "s"}`;
  if (run.data_source === "polygon") {
    return `Polygon · ${sessions} to ${run.config.end_date ?? "?"}`;
  }
  return `Synthetic · ${sessions} · seed ${run.config.seed}`;
}

function NumberField({
  label,
  value,
  onChange,
  step,
  min,
  max,
  hint,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  step: number;
  min: number;
  max: number;
  hint?: string;
}) {
  return (
    <label className="grid gap-1 text-xs text-slate-400" title={hint}>
      {label}
      <input
        type="number"
        value={Number.isFinite(value) ? value : ""}
        step={step}
        min={min}
        max={max}
        onChange={(event) => onChange(event.target.valueAsNumber)}
        className={fieldClass}
      />
    </label>
  );
}

const POLYGON_FREE_REQUESTS_PER_MINUTE = 5;

export function DeskRulesForm({
  config,
  sources,
  onChange,
}: {
  config: DeskConfig;
  sources: DeskDataSourceInfo[];
  onChange: (config: DeskConfig) => void;
}) {
  const [symbolsText, setSymbolsText] = useState(config.symbols.join(", "));
  const set = <K extends keyof DeskConfig>(key: K, value: DeskConfig[K]) => onChange({ ...config, [key]: value });
  const latestDay = latestReplayableDay();

  return (
    <div className="grid gap-5">
      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-300">Market data</p>
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          {sources.map((source) => {
            const selected = config.data_source === source.id;
            return (
              <button
                key={source.id}
                type="button"
                disabled={!source.available}
                aria-pressed={selected}
                onClick={() =>
                  onChange({
                    ...config,
                    data_source: source.id,
                    end_date: source.id === "polygon" ? (config.end_date ?? latestDay) : null,
                  })
                }
                className={clsx(
                  "rounded-2xl border px-4 py-3 text-left transition disabled:cursor-not-allowed disabled:opacity-50",
                  selected ? "border-cyan-300/60 bg-cyan-300/10" : "border-white/10 hover:border-white/25",
                )}
              >
                <span className="block text-sm font-semibold text-white">{source.label}</span>
                <span className="mt-1 block text-xs text-slate-400">{source.detail}</span>
              </button>
            );
          })}
        </div>
        {config.data_source === "polygon" ? (
          <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_2fr] sm:items-end">
            <label className="grid gap-1 text-xs text-slate-400">
              Replay through (last session)
              <input
                type="date"
                value={config.end_date ?? latestDay}
                max={latestDay}
                onChange={(event) => set("end_date", event.target.value || null)}
                className={fieldClass}
              />
            </label>
            <p className="text-xs text-slate-400">
              Replays the {config.sessions} trading day{config.sessions === 1 ? "" : "s"} up to this date, plus the day before
              as indicator warmup. Weekends and holidays are skipped.
              {config.symbols.length > POLYGON_FREE_REQUESTS_PER_MINUTE
                ? ` Polygon's free plan loads ${POLYGON_FREE_REQUESTS_PER_MINUTE} symbols a minute; extra symbols may need a second run a minute later.`
                : ""}
            </p>
          </div>
        ) : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-[2fr_1fr_1fr]">
        <label className="grid gap-1 text-xs text-slate-400">
          Symbols (up to 8; blank uses your watchlist)
          <input
            value={symbolsText}
            onChange={(event) => {
              setSymbolsText(event.target.value);
              set(
                "symbols",
                event.target.value
                  .split(/[\s,]+/)
                  .map((symbol) => symbol.trim().toUpperCase())
                  .filter(Boolean)
                  .slice(0, 8),
              );
            }}
            className={fieldClass}
          />
        </label>
        <NumberField label="Starting balance ($)" value={config.starting_balance} onChange={(v) => set("starting_balance", v)} step={50} min={50} max={1000000} />
        <NumberField label="Sessions" value={config.sessions} onChange={(v) => set("sessions", v)} step={1} min={1} max={5} hint="Each session is one 09:30–16:00 trading day." />
      </div>

      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-300">Risk</p>
        <div className="mt-2 grid gap-3 sm:grid-cols-4">
          <NumberField label="Risk per trade (%)" value={config.risk_per_trade_pct} onChange={(v) => set("risk_per_trade_pct", v)} step={0.25} min={0.1} max={3} />
          <label className="grid gap-1 text-xs text-slate-400" title="Kelly sizing is a ceiling, never a floor: the smaller of this and your risk cap wins.">
            Kelly fraction
            <select value={config.kelly_fraction} onChange={(event) => set("kelly_fraction", Number(event.target.value))} className={fieldClass}>
              <option value={0.1}>1/10 Kelly</option>
              <option value={0.25}>1/4 Kelly</option>
              <option value={0.5}>1/2 Kelly</option>
              <option value={1}>Full Kelly</option>
            </select>
          </label>
          <NumberField label="Max open positions" value={config.max_open_positions} onChange={(v) => set("max_open_positions", v)} step={1} min={1} max={6} />
          <label className="grid gap-1 text-xs text-slate-400" title="Cash accounts have 1×. Tight intraday stops often need more notional than that, so many entries get capped.">
            Buying power
            <select value={config.max_leverage} onChange={(event) => set("max_leverage", Number(event.target.value))} className={fieldClass}>
              <option value={1}>1× cash</option>
              <option value={2}>2× margin</option>
              <option value={4}>4× day-trading</option>
            </select>
          </label>
          <NumberField label="Daily loss limit (%)" value={config.max_daily_loss_pct} onChange={(v) => set("max_daily_loss_pct", v)} step={0.5} min={0.5} max={10} />
          <NumberField label="Cool down after N losses" value={config.max_consecutive_losses} onChange={(v) => set("max_consecutive_losses", v)} step={1} min={1} max={10} />
          <NumberField label="Trail stop after (R)" value={config.trail_after_r} onChange={(v) => set("trail_after_r", v)} step={0.25} min={0.5} max={5} />
          <NumberField label="Min reward:risk" value={config.min_reward_risk} onChange={(v) => set("min_reward_risk", v)} step={0.25} min={1} max={5} />
        </div>
      </div>

      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-300">Setups & scoring</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {DESK_SETUPS.map((setup) => {
            const checked = config.allowed_setups.includes(setup);
            return (
              <label
                key={setup}
                className={clsx(
                  "flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-xs transition",
                  checked ? "border-cyan-300/50 bg-cyan-300/10 text-white" : "border-white/10 text-slate-400",
                )}
              >
                <input
                  type="checkbox"
                  className="accent-cyan-300"
                  checked={checked}
                  onChange={() =>
                    set(
                      "allowed_setups",
                      checked ? config.allowed_setups.filter((item) => item !== setup) : [...config.allowed_setups, setup],
                    )
                  }
                />
                {SETUP_LABELS[setup]}
              </label>
            );
          })}
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-4">
          <NumberField label="Min analyst score" value={config.min_score} onChange={(v) => set("min_score", v)} step={5} min={0} max={100} />
          <NumberField label="Fees (bps per side)" value={config.fee_bps} onChange={(v) => set("fee_bps", v)} step={0.5} min={0} max={50} />
          <NumberField label="Slippage (bps)" value={config.slippage_bps} onChange={(v) => set("slippage_bps", v)} step={0.5} min={0} max={50} />
          <label className="grid gap-1 text-xs text-slate-400" title="Same seed + same rules = the exact same tape and decisions.">
            Seed (blank = random)
            <input
              type="number"
              value={config.seed ?? ""}
              min={0}
              onChange={(event) => set("seed", event.target.value === "" ? null : event.target.valueAsNumber)}
              className={fieldClass}
            />
          </label>
        </div>
        <label className="mt-3 flex items-center gap-2 text-xs text-slate-300">
          <input
            type="checkbox"
            className="accent-cyan-300"
            checked={config.use_journal_priors}
            onChange={(event) => set("use_journal_priors", event.target.checked)}
          />
          Seed the Analyst&apos;s win-rate estimates with my tagged journal trades
        </label>
      </div>
    </div>
  );
}
