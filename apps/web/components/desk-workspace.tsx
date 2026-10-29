"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import clsx from "clsx";

import type { DeskConfig, DeskDataSourceInfo, DeskRun, DeskRunSummary } from "@tradenoc/types";
import { Card } from "@tradenoc/ui";
import { EquityChart, KillReasonBars, MonteCarloFan, ScoutRadar } from "@/components/desk-charts";
import { AgentCards, AlertBanner, CandlestickChart, MilestoneLadder, TickerStrip } from "@/components/desk-visuals";
import {
  ActivityFeed,
  ClaimCheckCard,
  ClosedTradesPanel,
  DeskRulesForm,
  PipelineStrip,
  PositionsPanel,
  RunHistory,
  SeatVerdicts,
  SetupEdgeBoard,
  StatTile,
} from "@/components/desk-panels";
import { StatePanel } from "@/components/state-panels";
import {
  DESK_AGENTS,
  FALLBACK_DESK_CONFIG,
  PROVIDER_NAMES,
  TAPE_LABELS,
  deriveView,
  formatMoney,
  formatPercent,
  formatR,
  formatSigned,
  formatSignedMoney,
  replayRangeLabel,
  sessionLabel,
  shortSessionLabel,
  splitMoney,
  toneFor,
} from "@/lib/desk";

const TICK_MS = 90;
const SPEEDS = [
  { label: "1×", bars: 1 },
  { label: "4×", bars: 4 },
  { label: "12×", bars: 12 },
];
const KELLY_LABELS: Record<number, string> = { 0.1: "1/10", 0.25: "1/4", 0.5: "1/2", 1: "full" };
const FALLBACK_SOURCES: DeskDataSourceInfo[] = [
  { id: "synthetic", label: "Synthetic tape", available: true, detail: "Seeded random market with no edge built in." },
];

function summarySkeleton(run: DeskRun): DeskRunSummary {
  return {
    id: run.id,
    created_at: run.created_at,
    mode: run.mode,
    data_source: run.data_source,
    config: run.config,
    summary: run.summary,
  };
}

function Panel({ title, subtitle, children, className }: { title: string; subtitle?: string; children: ReactNode; className?: string }) {
  return (
    <Card className={clsx("p-5", className)}>
      <h2 className="text-base font-semibold text-white">{title}</h2>
      {subtitle ? <p className="mt-1 text-xs text-slate-400">{subtitle}</p> : null}
      <div className="mt-4">{children}</div>
    </Card>
  );
}

export function DeskWorkspace({
  defaults,
  runs: initialRuns,
  sources,
  initialRun,
}: {
  defaults: DeskConfig | null;
  runs: DeskRunSummary[];
  sources: DeskDataSourceInfo[];
  initialRun: DeskRun | null;
}) {
  const [config, setConfig] = useState<DeskConfig>(() => ({ ...(initialRun?.config ?? defaults ?? FALLBACK_DESK_CONFIG), seed: null }));
  const [runs, setRuns] = useState(initialRuns);
  const [run, setRun] = useState<DeskRun | null>(initialRun);
  const [step, setStep] = useState(() => (initialRun ? initialRun.frames.length - 1 : 0));
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(SPEEDS[0].bars);
  const [rulesOpen, setRulesOpen] = useState(!initialRun);
  const [pending, setPending] = useState(false);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const lastStep = run ? run.frames.length - 1 : 0;

  useEffect(() => {
    if (!playing || !run) {
      return;
    }
    const timer = window.setInterval(() => {
      setStep((current) => Math.min(current + speed, lastStep));
    }, TICK_MS);
    return () => window.clearInterval(timer);
  }, [playing, speed, run, lastStep]);

  useEffect(() => {
    if (playing && step >= lastStep) {
      setPlaying(false);
    }
  }, [playing, step, lastStep]);

  const view = useMemo(() => (run ? deriveView(run, step) : null), [run, step]);

  function rememberRun(runId: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("run", runId);
    window.history.replaceState(null, "", url);
  }

  async function startRun() {
    setError(null);
    if (config.allowed_setups.length === 0) {
      setError("Enable at least one setup for the Scout to look for.");
      return;
    }
    setPending(true);
    try {
      const response = await fetch("/api/desk/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      const data = (await response.json()) as DeskRun & { detail?: unknown; message?: string };
      if (!response.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join("; ")
          : typeof data.detail === "string"
            ? data.detail
            : data.message;
        setError(detail || "The desk could not run. Check that the API is reachable.");
        return;
      }
      setRun(data);
      setRuns((current) => [summarySkeleton(data), ...current.filter((item) => item.id !== data.id)]);
      setStep(0);
      setPlaying(true);
      setRulesOpen(false);
      rememberRun(data.id);
    } catch {
      setError("The desk could not run. Check that the API is reachable.");
    } finally {
      setPending(false);
    }
  }

  async function openRun(runId: string) {
    if (runId === run?.id) {
      return;
    }
    setError(null);
    setLoadingId(runId);
    try {
      const response = await fetch(`/api/desk/runs/${encodeURIComponent(runId)}`);
      if (!response.ok) {
        setError("That run could not be loaded.");
        return;
      }
      const data = (await response.json()) as DeskRun;
      setRun(data);
      setPlaying(false);
      setStep(data.frames.length - 1);
      setConfig({ ...data.config, seed: null });
      rememberRun(data.id);
    } catch {
      setError("That run could not be loaded.");
    } finally {
      setLoadingId(null);
    }
  }

  function replay() {
    setStep(0);
    setPlaying(true);
  }

  const frame = view?.frame ?? null;
  const balance = view ? view.frame.equity : config.starting_balance;
  const { whole, cents } = splitMoney(balance);
  const pnlTone = view ? toneFor(view.pnl) : "flat";
  const sessionCount = run?.config.sessions ?? config.sessions;
  const statusLabel = !run ? "Idle" : playing ? "Live replay" : view?.isComplete ? "Session closed" : "Paused";
  const replayRange = run ? replayRangeLabel(run) : null;
  const tapeLabel = run
    ? `${TAPE_LABELS[run.data_source]}${replayRange ? ` · ${replayRange}` : ""}`
    : TAPE_LABELS[config.data_source];

  return (
    <div className="grid gap-4">
      {defaults === null ? (
        <StatePanel
          title="Desk API not reachable"
          message="Showing default rules. Runs need the API to be up; check Diagnostics if this persists."
          tone="warning"
          actionLabel="Open diagnostics"
          actionHref="/app/diagnostics"
        />
      ) : null}

      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-white">Desk rules</h2>
            <p className="mt-1 text-xs text-slate-400">
              {config.data_source === "synthetic"
                ? "Synthetic tape"
                : `${PROVIDER_NAMES[config.data_source]} bars through ${config.end_date ?? "yesterday"}`}{" "}
              ·{" "}
              {config.symbols.length ? config.symbols.join(" · ") : "Watchlist symbols"} · {config.risk_per_trade_pct}% risk ·{" "}
              {KELLY_LABELS[config.kelly_fraction] ?? config.kelly_fraction} Kelly · max {config.max_open_positions} open ·{" "}
              {config.max_daily_loss_pct}% daily stop · {config.sessions} session{config.sessions === 1 ? "" : "s"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setRulesOpen((open) => !open)}
              className="whitespace-nowrap rounded-full border border-white/15 px-4 py-2 text-sm text-white transition hover:border-cyan-300/60"
              aria-expanded={rulesOpen}
            >
              {rulesOpen ? "Hide rules" : "Edit rules"}
            </button>
            <button
              type="button"
              onClick={startRun}
              disabled={pending}
              className="whitespace-nowrap rounded-full bg-cyan-300 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:opacity-60"
            >
              {pending ? "Agents working…" : "Run paper session"}
            </button>
          </div>
        </div>
        {rulesOpen ? (
          <div className="mt-5 border-t border-white/10 pt-5">
            <DeskRulesForm config={config} sources={sources.length ? sources : FALLBACK_SOURCES} onChange={setConfig} />
          </div>
        ) : null}
        {error ? (
          <div className="mt-4">
            <StatePanel title="Run failed" message={error} tone="danger" />
          </div>
        ) : null}
      </Card>

      <section
        className="relative overflow-hidden rounded-3xl border border-white/10 bg-[radial-gradient(circle_at_20%_0%,rgba(52,211,153,0.16),transparent_45%),radial-gradient(circle_at_90%_10%,rgba(103,232,249,0.14),transparent_40%),linear-gradient(180deg,#0b1424,#050a14)] p-5 shadow-[0_24px_80px_rgba(15,23,42,0.55)]"
        aria-label="Agent desk console"
      >
        {run && view ? (
          <div className="mb-4">
            <TickerStrip run={run} view={view} step={step} />
          </div>
        ) : null}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="font-mono text-2xl font-semibold tabular-nums text-white">{frame?.clock ?? "09:30"}</p>
          <span className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 font-mono text-xs text-slate-300">
            <span className={clsx("h-1.5 w-1.5 rounded-full", playing ? "bg-cyan-300 motion-safe:animate-pulse" : "bg-slate-500")} />
            {frame && run ? `${sessionLabel(run, frame.session)} · ${frame.session} of ${sessionCount}` : "paper session"}
          </span>
          <p className="text-sm text-slate-300">
            <span className="font-semibold text-white">{DESK_AGENTS.length}</span> agents
          </p>
        </div>

        {run && view ? (
        <div className="mt-3 flex flex-wrap items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-2.5">
          <button
            type="button"
            onClick={() => (view.isComplete ? replay() : setPlaying((value) => !value))}
            className="rounded-full border border-white/15 px-4 py-1.5 text-sm font-medium text-white transition hover:border-cyan-300/60"
          >
            {view.isComplete ? "Replay" : playing ? "Pause" : "Play"}
          </button>
          <div className="flex rounded-full border border-white/10 p-0.5" role="group" aria-label="Replay speed">
            {SPEEDS.map((option) => (
              <button
                key={option.label}
                type="button"
                onClick={() => setSpeed(option.bars)}
                aria-pressed={speed === option.bars}
                className={clsx(
                  "rounded-full px-3 py-1 text-xs transition",
                  speed === option.bars ? "bg-white/10 text-white" : "text-slate-400 hover:text-white",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
          <input
            type="range"
            min={0}
            max={lastStep}
            value={step}
            onChange={(event) => {
              setPlaying(false);
              setStep(event.target.valueAsNumber);
            }}
            className="min-w-[10rem] flex-1 accent-cyan-300"
            aria-label="Replay position"
          />
          <span className="font-mono text-xs tabular-nums text-slate-400">
            bar {step + 1}/{lastStep + 1}
          </span>
          <button
            type="button"
            onClick={() => {
              setPlaying(false);
              setStep(lastStep);
            }}
            className="text-xs text-slate-400 underline-offset-2 hover:text-white hover:underline"
          >
            Skip to end
          </button>
        </div>
        ) : null}

        {run ? (
          <div className="mt-3">
            <AlertBanner events={run.events} step={frame?.step ?? 0} />
          </div>
        ) : null}

        <div className="mt-4 grid gap-5 md:grid-cols-[1fr_auto]">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-300/40 bg-cyan-300/10 text-cyan-200">
                <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
                  <path d="M12 2.5 20.5 7v10L12 21.5 3.5 17V7L12 2.5Z" />
                  <circle cx="12" cy="12" r="3.2" />
                </svg>
              </span>
              <div>
                <p className="text-2xl font-semibold text-white">Agent Desk</p>
                <p className="text-xs text-slate-400">
                  Paper · {tapeLabel} · {(run?.config ?? config).risk_per_trade_pct}% risk · max{" "}
                  {(run?.config ?? config).max_open_positions} open
                </p>
              </div>
              <span
                className={clsx(
                  "ml-auto rounded-full border px-3 py-1 text-xs font-medium",
                  frame?.halted
                    ? "border-rose-300/40 bg-rose-400/10 text-rose-100"
                    : playing
                      ? "border-emerald-300/40 bg-emerald-400/10 text-emerald-100"
                      : "border-white/15 bg-white/5 text-slate-300",
                )}
              >
                {frame?.halted ? "Halted · daily limit" : statusLabel}
              </span>
            </div>

            <p className="mt-6 text-xs text-slate-400">
              Balance · {formatMoney(run?.summary.starting_balance ?? config.starting_balance)} at 09:30
            </p>
            <div className="mt-1 flex flex-wrap items-end gap-3">
              <p className="text-5xl font-semibold tracking-tight text-white sm:text-6xl">
                {whole}
                <span className="text-2xl text-slate-400 sm:text-3xl">.{cents}</span>
              </p>
              {view ? (
                <span
                  className={clsx(
                    "mb-2 rounded-full px-3 py-1 text-base font-bold",
                    pnlTone === "up" && "bg-emerald-400 text-slate-950",
                    pnlTone === "down" && "bg-rose-400 text-slate-950",
                    pnlTone === "flat" && "bg-slate-200 text-slate-950",
                  )}
                >
                  {view.multiple.toFixed(3)}×
                </span>
              ) : null}
            </div>
            {view ? (
              <>
                <p
                  className={clsx(
                    "mt-1 text-sm font-semibold",
                    pnlTone === "up" && "text-emerald-300",
                    pnlTone === "down" && "text-rose-300",
                    pnlTone === "flat" && "text-slate-300",
                  )}
                >
                  {formatSignedMoney(view.pnl)} ({formatSigned((view.multiple - 1) * 100, 2, "%")})
                </p>
                <p className="mt-1 font-mono text-xs text-slate-400">
                  best {view.bestTrade !== null ? formatSignedMoney(view.bestTrade) : "—"} · worst{" "}
                  {view.worstTrade !== null ? formatSignedMoney(view.worstTrade) : "—"} · {view.wins}W / {view.losses}L
                </p>
              </>
            ) : (
              <p className="mt-2 text-sm text-slate-400">Run a paper session to arm the desk.</p>
            )}
          </div>
          <ScoutRadar symbols={run?.config.symbols ?? config.symbols} frame={frame} active={playing} />
        </div>

        {run && view ? (
          <div className="mt-4">
            <EquityChart
              frames={run.frames}
              currentIndex={step}
              startingBalance={run.summary.starting_balance}
              trades={view.closedTrades}
              sessionMarker={(session) => shortSessionLabel(run, session)}
            />
          </div>
        ) : (
          <div className="mt-4 flex h-36 items-center justify-center rounded-2xl border border-dashed border-white/10 text-sm text-slate-500">
            The equity curve draws here as the session replays.
          </div>
        )}

        {run && view ? (
          <div className="mt-4">
            <MilestoneLadder run={run} view={view} />
          </div>
        ) : null}

        <div className="mt-4">
          <PipelineStrip frame={frame} events={run?.events ?? []} active={playing} />
        </div>

        {run && view ? (
          <>
            <div className="mt-4">
              <AgentCards run={run} step={step} />
            </div>
            <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
                <p className="text-sm font-semibold text-white">Tape</p>
                <p className="text-xs text-slate-400">
                  5-minute candles · {sessionLabel(run, frame?.session ?? 1)} · flow from {run.flow_source ?? "bar proxy"}
                </p>
              </div>
              <CandlestickChart run={run} step={step} />
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <PositionsPanel frame={frame} run={run} />
              <ClosedTradesPanel trades={view.closedTrades} wins={view.wins} losses={view.losses} />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatTile label="Win rate" value={view.winRate === null ? "—" : formatPercent(view.winRate)} />
              <StatTile
                label="Avg win"
                value={view.avgWinR === null ? "—" : formatR(view.avgWinR)}
                tone={view.avgWinR === null ? "default" : "up"}
              />
              <StatTile
                label="Max drawdown"
                value={view.maxDrawdownPct > 0 ? `−${view.maxDrawdownPct.toFixed(1)}%` : "0.0%"}
                tone={view.maxDrawdownPct > 0 ? "down" : "default"}
              />
              <StatTile
                label="Stops widened"
                value={String(frame?.pipeline.stops_widened ?? 0)}
                hint="Audited per trade: a stop that ends looser than it started counts here. Trailing only tightens."
              />
            </div>

          </>
        ) : null}

        <div className="mt-4 flex flex-wrap justify-between gap-2 font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">
          <span>Paper session · {tapeLabel} · not financial advice</span>
          <span>
            TradeReviewDesk · {(run?.config ?? config).risk_per_trade_pct}% rule
            {run?.data_source === "synthetic" ? ` · seed ${run.config.seed}` : ""}
          </span>
        </div>
      </section>

      {run && view ? (
        <>
          <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
            <Panel title="Activity" subtitle="Every decision with its reason, up to the current bar.">
              <ActivityFeed events={run.events} step={frame?.step ?? 0} />
            </Panel>
            <Panel title="Why setups died" subtitle="Kill reasons across the whole run, by count.">
              {run.kill_reasons.length ? (
                <KillReasonBars reasons={run.kill_reasons} />
              ) : (
                <p className="text-sm text-slate-500">Nothing was killed.</p>
              )}
            </Panel>
          </div>

          <Panel
            title="Skeptic seat"
            subtitle={`Four risk questions on every sized order; a ${formatPercent(run.config.seat_veto)} answer vetoes it. ${run.pipeline.seat_ai_calls} AI call${run.pipeline.seat_ai_calls === 1 ? "" : "s"} this run.`}
          >
            <SeatVerdicts verdicts={run.seat_verdicts ?? []} step={frame?.step ?? 0} threshold={run.config.seat_veto} />
          </Panel>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel
              title="Setup edge board"
              subtitle="The Analyst's Bayesian win-rate estimate: starting assumption + your journal + this run's results so far."
            >
              <SetupEdgeBoard edges={view.setupEdges} />
            </Panel>
            <Panel
              title="Expectancy fan"
              subtitle={
                run.monte_carlo
                  ? `${run.monte_carlo.paths} resampled paths of the next ${run.monte_carlo.trades_per_path} trades, built from this run's ${run.monte_carlo.sample_size} paper trades.`
                  : "Needs at least 5 closed trades in the run."
              }
            >
              {run.monte_carlo && view.isComplete ? (
                <>
                  <MonteCarloFan monteCarlo={run.monte_carlo} startingBalance={run.summary.starting_balance} />
                  <div className="mt-4 grid grid-cols-3 gap-3">
                    <StatTile label="Median" value={`${run.monte_carlo.median_multiple.toFixed(2)}×`} />
                    <StatTile
                      label="Ends below start"
                      value={formatPercent(run.monte_carlo.probability_below_start)}
                      tone={run.monte_carlo.probability_below_start > 0.5 ? "down" : "default"}
                    />
                    <StatTile label="20%+ drawdown" value={formatPercent(run.monte_carlo.probability_drawdown_20)} />
                  </div>
                </>
              ) : run.monte_carlo ? (
                <p className="text-sm text-slate-500">
                  The fan is built from the full run, so it unlocks when the replay reaches the closing bell.
                </p>
              ) : (
                <p className="text-sm text-slate-500">Too few trades to say anything about the spread of outcomes.</p>
              )}
            </Panel>
          </div>
        </>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Panel title="Screenshot reality check" subtitle="Viral bot posts rarely show the math. This does.">
          <ClaimCheckCard run={run} />
        </Panel>
        <Panel title="Saved sessions" subtitle="The same rules on the same seed or dates replay exactly.">
          <RunHistory runs={runs} activeId={run?.id ?? null} onSelect={openRun} loadingId={loadingId} />
        </Panel>
      </div>

      <StatePanel
        title="Paper only, on purpose"
        message={
          run?.disclaimer ??
          "The desk runs your rules with paper fills on a synthetic tape or real historical bars. It never places real orders, and its results are not evidence of future profitability."
        }
        tone="warning"
      />
    </div>
  );
}
