"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import clsx from "clsx";

import type { BinaryAsset, BinaryConfig, BinaryRun, BinaryRunSummary } from "@tradenoc/types";
import { Card } from "@tradenoc/ui";
import { ColumnChart, LineChart, type ChartMarker } from "@/components/binary-charts";
import { MonteCarloFan } from "@/components/desk-charts";
import { StatTile } from "@/components/desk-panels";
import { StatePanel } from "@/components/state-panels";
import {
  ASSET_COLORS,
  BINARY_ASSETS,
  FALLBACK_BINARY_CONFIG,
  SERIES_COLORS,
  assumptionLine,
  cents,
  clockEt,
  dayEt,
  deriveBinaryView,
} from "@/lib/binary";
import { formatMoney, formatPercent, formatRunLabel, formatSigned, formatSignedMoney, splitMoney } from "@/lib/desk";

const TICK_MS = 110;
const SPEEDS = [
  { label: "1 min", minutes: 1 },
  { label: "5 min", minutes: 5 },
  { label: "1 window", minutes: 15 },
];

const fieldClass =
  "w-full rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-300/60";

function Panel({ title, subtitle, children, className }: { title: string; subtitle?: string; children: ReactNode; className?: string }) {
  return (
    <Card className={clsx("p-5", className)}>
      <h2 className="text-base font-semibold text-white">{title}</h2>
      {subtitle ? <p className="mt-1 text-xs text-slate-400">{subtitle}</p> : null}
      <div className="mt-4">{children}</div>
    </Card>
  );
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

function BinaryRulesForm({ config, onChange }: { config: BinaryConfig; onChange: (config: BinaryConfig) => void }) {
  const set = <K extends keyof BinaryConfig>(key: K, value: BinaryConfig[K]) => onChange({ ...config, [key]: value });
  const endLocal = config.end_at ? config.end_at.slice(0, 16) : "";

  return (
    <div className="grid gap-5">
      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-300">Markets</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {BINARY_ASSETS.map((asset) => {
            const checked = config.assets.includes(asset);
            return (
              <label
                key={asset}
                className={clsx(
                  "flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-xs transition",
                  checked ? "border-cyan-300/50 bg-cyan-300/10 text-white" : "border-white/10 text-slate-400",
                )}
              >
                <input
                  type="checkbox"
                  className="accent-cyan-300"
                  checked={checked}
                  onChange={() => set("assets", checked ? config.assets.filter((item) => item !== asset) : [...config.assets, asset])}
                />
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: ASSET_COLORS[asset] }} />
                {asset} 15m
              </label>
            );
          })}
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-4">
          <label className="grid gap-1 text-xs text-slate-400">
            Underlying prices
            <select
              value={config.data_source}
              onChange={(event) => set("data_source", event.target.value as BinaryConfig["data_source"])}
              className={fieldClass}
            >
              <option value="synthetic">Synthetic tape</option>
              <option value="coinbase">Coinbase 1-minute candles</option>
            </select>
          </label>
          <NumberField label="Hours" value={config.hours} onChange={(v) => set("hours", v)} step={1} min={1} max={12} />
          <label className="grid gap-1 text-xs text-slate-400" title="Blank uses the last completed 15-minute window.">
            End (UTC, optional)
            <input
              type="datetime-local"
              value={endLocal}
              onChange={(event) => set("end_at", event.target.value ? `${event.target.value}:00Z` : null)}
              className={fieldClass}
            />
          </label>
          <NumberField label="Starting balance ($)" value={config.starting_balance} onChange={(v) => set("starting_balance", v)} step={100} min={50} max={1000000} />
        </div>
      </div>

      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-300">Grid</p>
        <div className="mt-2 grid gap-3 sm:grid-cols-4">
          <NumberField label="Shares per level" value={config.shares_per_level} onChange={(v) => set("shares_per_level", v)} step={1} min={1} max={500} />
          <NumberField label="Levels per side" value={config.levels} onChange={(v) => set("levels", v)} step={1} min={1} max={5} />
          <NumberField label="Half spread (¢)" value={config.half_spread_cents} onChange={(v) => set("half_spread_cents", v)} step={0.5} min={0.5} max={10} hint="Each top bid sits this far under fair, so a quoted pair costs $1 minus twice this." />
          <NumberField label="Level step (¢)" value={config.level_step_cents} onChange={(v) => set("level_step_cents", v)} step={0.5} min={0.5} max={5} />
          <NumberField label="Max shares per side" value={config.max_shares_per_side} onChange={(v) => set("max_shares_per_side", v)} step={10} min={1} max={5000} />
          <NumberField label="Inventory skew (¢)" value={config.inventory_skew_cents} onChange={(v) => set("inventory_skew_cents", v)} step={0.5} min={0} max={20} hint="How far both bids shade away from the side you already hold too much of, at a full side." />
          <NumberField label="Stop quoting (min before close)" value={config.stop_quoting_minutes} onChange={(v) => set("stop_quoting_minutes", v)} step={1} min={0} max={10} />
          <NumberField label="Maker fee (bps)" value={config.maker_fee_bps} onChange={(v) => set("maker_fee_bps", v)} step={1} min={0} max={200} />
        </div>
      </div>

      <div className="rounded-2xl border border-amber-300/30 bg-amber-400/5 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-[10px] uppercase tracking-[0.2em] text-amber-200">Crowd assumptions (the model, not data)</p>
          <button
            type="button"
            onClick={() => onChange({ ...config, crowd_lag_minutes: 0, crowd_noise_cents: 0 })}
            className="rounded-full border border-white/15 px-3 py-1 text-xs text-white hover:border-cyan-300/60"
          >
            Make the crowd efficient
          </button>
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-5">
          <NumberField label="Crowd lag (min)" value={config.crowd_lag_minutes} onChange={(v) => set("crowd_lag_minutes", v)} step={1} min={0} max={5} hint="How many minutes behind the true price the crowd quotes. Most traders are not faster than the market; 0 is the honest default for them." />
          <NumberField label="Crowd noise (¢)" value={config.crowd_noise_cents} onChange={(v) => set("crowd_noise_cents", v)} step={0.5} min={0} max={10} />
          <NumberField label="Noise half-life (min)" value={config.dislocation_half_life_minutes} onChange={(v) => set("dislocation_half_life_minutes", v)} step={0.5} min={0.5} max={30} />
          <NumberField label="Crowd spread (¢)" value={config.crowd_spread_cents} onChange={(v) => set("crowd_spread_cents", v)} step={0.5} min={0.5} max={10} />
          <NumberField label="Queue fill odds" value={config.queue_fill_probability} onChange={(v) => set("queue_fill_probability", v)} step={0.05} min={0.05} max={1} hint="Chance a bid the crowd traded through actually fills, given others queued ahead of you." />
        </div>
        <label className="mt-3 grid max-w-[12rem] gap-1 text-xs text-slate-400">
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
    </div>
  );
}

function summarySkeleton(run: BinaryRun): BinaryRunSummary {
  return {
    id: run.id,
    created_at: run.created_at,
    mode: run.mode,
    data_source: run.data_source,
    config: run.config,
    summary: run.summary,
    baseline: run.baseline,
  };
}

export function BinaryWorkspace({
  defaults,
  runs: initialRuns,
  initialRun,
}: {
  defaults: BinaryConfig | null;
  runs: BinaryRunSummary[];
  initialRun: BinaryRun | null;
}) {
  const [config, setConfig] = useState<BinaryConfig>(() => ({ ...(initialRun?.config ?? defaults ?? FALLBACK_BINARY_CONFIG), seed: null, end_at: null }));
  const [runs, setRuns] = useState(initialRuns);
  const [run, setRun] = useState<BinaryRun | null>(initialRun);
  const [minute, setMinute] = useState(() => (initialRun ? initialRun.minutes.length - 1 : 0));
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(SPEEDS[0].minutes);
  const [rulesOpen, setRulesOpen] = useState(!initialRun);
  const [pending, setPending] = useState(false);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<BinaryAsset | null>(null);

  const lastMinute = run ? run.minutes.length - 1 : 0;
  useEffect(() => {
    if (!playing || !run) {
      return;
    }
    const timer = window.setInterval(() => setMinute((current) => Math.min(current + speed, lastMinute)), TICK_MS);
    return () => window.clearInterval(timer);
  }, [playing, speed, run, lastMinute]);
  useEffect(() => {
    if (playing && minute >= lastMinute) {
      setPlaying(false);
    }
  }, [playing, minute, lastMinute]);

  const view = useMemo(() => (run ? deriveBinaryView(run, minute) : null), [run, minute]);
  const asset = run ? (selected && run.config.assets.includes(selected) ? selected : run.config.assets[0]) : null;
  const assetSeries = run && asset ? run.series.find((item) => item.asset === asset) ?? null : null;

  function remember(runId: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("run", runId);
    window.history.replaceState(null, "", url);
  }

  async function startRun() {
    setError(null);
    if (config.assets.length === 0) {
      setError("Pick at least one market.");
      return;
    }
    setPending(true);
    try {
      const response = await fetch("/api/binary/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      const data = (await response.json()) as BinaryRun & { detail?: unknown; message?: string };
      if (!response.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join("; ")
          : typeof data.detail === "string"
            ? data.detail
            : data.message;
        setError(detail || "The binary desk could not run. Check that the API is reachable.");
        return;
      }
      setRun(data);
      setRuns((current) => [summarySkeleton(data), ...current.filter((item) => item.id !== data.id)]);
      setMinute(0);
      setPlaying(true);
      setRulesOpen(false);
      remember(data.id);
    } catch {
      setError("The binary desk could not run. Check that the API is reachable.");
    } finally {
      setPending(false);
    }
  }

  async function openRun(runId: string) {
    if (runId === run?.id) {
      return;
    }
    setLoadingId(runId);
    setError(null);
    try {
      const response = await fetch(`/api/binary/runs/${encodeURIComponent(runId)}`);
      if (!response.ok) {
        setError("That run could not be loaded.");
        return;
      }
      const data = (await response.json()) as BinaryRun;
      setRun(data);
      setPlaying(false);
      setMinute(data.minutes.length - 1);
      setConfig({ ...data.config, seed: null, end_at: null });
      remember(data.id);
    } catch {
      setError("That run could not be loaded.");
    } finally {
      setLoadingId(null);
    }
  }

  const quotedPairCost = 1 - (2 * (run?.config ?? config).half_spread_cents) / 100;
  const equity = view ? run!.minutes[view.minute].equity : config.starting_balance;
  const { whole, cents: centsPart } = splitMoney(equity);

  // The current window for the selected asset: fair, crowd, and our bids, all as P(up).
  const windowLength = 15;
  const windowSlice = <T,>(values: T[]) => (view ? values.slice(view.windowStart, Math.min(view.minute + 1, view.windowStart + windowLength)) : []);
  const windowFills = view && asset ? view.fills.filter((fill) => fill.asset === asset && fill.window_index === view.windowIndex) : [];
  const windowMarkers: ChartMarker[] = windowFills.map((fill) => ({
    x: fill.minute - (view?.windowStart ?? 0),
    y: fill.side === "up" ? fill.price : 1 - fill.price,
    color: fill.side === "up" ? SERIES_COLORS.bidUp : SERIES_COLORS.bidDown,
    hollow: fill.side === "down",
    label: `${fill.side === "up" ? "Up" : "Down"} filled ${fill.shares} @ ${cents(fill.price)}`,
  }));
  const currentWindow = run && asset && view ? run.windows.find((window) => window.asset === asset && window.index === view.windowIndex) : null;

  return (
    <div className="grid gap-4">
      {defaults === null ? (
        <StatePanel title="Binary desk API not reachable" message="Showing default rules. Runs need the API to be up." tone="warning" />
      ) : null}

      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-white">Grid rules</h2>
            <p className="mt-1 text-xs text-slate-400">
              {config.assets.join(" · ")} 15m Up/Down · {config.data_source === "coinbase" ? "Coinbase candles" : "synthetic tape"} ·{" "}
              {config.hours}h · {config.levels}×{config.shares_per_level} shares · quoted pair cost ${(1 - config.half_spread_cents / 50).toFixed(3)}
            </p>
            <p className="mt-1 text-xs text-amber-200/80">{assumptionLine(config)}</p>
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
              {pending ? "Simulating…" : "Run simulation"}
            </button>
          </div>
        </div>
        {rulesOpen ? (
          <div className="mt-5 border-t border-white/10 pt-5">
            <BinaryRulesForm config={config} onChange={setConfig} />
          </div>
        ) : null}
        {error ? (
          <div className="mt-4">
            <StatePanel title="Run failed" message={error} tone="danger" />
          </div>
        ) : null}
      </Card>

      {run && view && asset ? (
        <section
          className="relative overflow-hidden rounded-3xl border border-white/10 bg-[radial-gradient(circle_at_15%_0%,rgba(57,135,229,0.18),transparent_45%),radial-gradient(circle_at_95%_10%,rgba(217,89,38,0.12),transparent_40%),linear-gradient(180deg,#0b1424,#050a14)] p-5"
          aria-label="Binary desk console"
        >
          <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 font-mono text-[11px] sm:flex-wrap">
            {[
              ["Mode", "two-sided grid"],
              ["Markets", `${run.config.assets.join("/")} 15m`],
              ["Quoted pair", `$${quotedPairCost.toFixed(3)}`],
              ["Maker", `${run.config.maker_fee_bps}bp`],
              ["Fills/hr", run.summary.fills_per_hour.toFixed(0)],
              ["Paired", run.summary.paired_share_pct === null ? "—" : `${run.summary.paired_share_pct.toFixed(0)}%`],
              ["Windows", String(run.summary.windows)],
              ["Prices", run.data_source === "coinbase" ? "Coinbase 1m" : "synthetic"],
            ].map(([label, value]) => (
              <span key={label} className="flex shrink-0 items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1">
                <span className="uppercase tracking-[0.14em] text-slate-500">{label}</span>
                <span className="font-semibold text-white">{value}</span>
              </span>
            ))}
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="font-mono text-2xl font-semibold tabular-nums text-white">{clockEt(run.minutes[view.minute].t)} ET</p>
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 font-mono text-xs text-slate-300">
              {dayEt(run.minutes[view.minute].t)} · window {view.windowIndex + 1} of {run.minutes.length / 15}
            </span>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-2.5">
            <button
              type="button"
              onClick={() => {
                if (view.isComplete) {
                  setMinute(0);
                  setPlaying(true);
                } else {
                  setPlaying((value) => !value);
                }
              }}
              className="rounded-full border border-white/15 px-4 py-1.5 text-sm font-medium text-white transition hover:border-cyan-300/60"
            >
              {view.isComplete ? "Replay" : playing ? "Pause" : "Play"}
            </button>
            <div className="flex rounded-full border border-white/10 p-0.5" role="group" aria-label="Replay speed">
              {SPEEDS.map((option) => (
                <button
                  key={option.label}
                  type="button"
                  onClick={() => setSpeed(option.minutes)}
                  aria-pressed={speed === option.minutes}
                  className={clsx("rounded-full px-3 py-1 text-xs transition", speed === option.minutes ? "bg-white/10 text-white" : "text-slate-400 hover:text-white")}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <input
              type="range"
              min={0}
              max={lastMinute}
              value={minute}
              onChange={(event) => {
                setPlaying(false);
                setMinute(event.target.valueAsNumber);
              }}
              className="min-w-[10rem] flex-1 accent-cyan-300"
              aria-label="Replay position"
            />
            <span className="font-mono text-xs tabular-nums text-slate-400">
              min {minute + 1}/{lastMinute + 1}
            </span>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
            <div>
              <p className="text-xs text-slate-400">Balance · {formatMoney(run.summary.starting_balance)} at start</p>
              <p className="mt-1 text-5xl font-semibold tracking-tight text-white sm:text-6xl">
                {whole}
                <span className="text-2xl text-slate-400 sm:text-3xl">.{centsPart}</span>
              </p>
              <p className={clsx("mt-1 text-sm font-semibold", view.pnl >= 0 ? "text-emerald-300" : "text-rose-300")}>
                {formatSignedMoney(view.pnl)} ({formatSigned((view.pnl / run.summary.starting_balance) * 100, 2, "%")}) · {view.fillsSoFar} fills ·{" "}
                {view.pairsSoFar} pairs locked
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-3">
                <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Modeled crowd · full run</p>
                <p className={clsx("mt-1 text-2xl font-semibold", run.summary.net_pnl >= 0 ? "text-emerald-300" : "text-rose-300")}>
                  {formatSignedMoney(run.summary.net_pnl)}
                </p>
                <p className="mt-1 text-[11px] text-amber-200/80">{assumptionLine(run.config)}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-3">
                <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Efficient crowd · same rules</p>
                <p className={clsx("mt-1 text-2xl font-semibold", run.baseline.net_pnl >= 0 ? "text-emerald-300" : "text-rose-300")}>
                  {formatSignedMoney(run.baseline.net_pnl)}
                </p>
                <p className="mt-1 text-[11px] text-slate-400">No lag, no noise. The gap between the two is what the assumptions are worth.</p>
              </div>
            </div>
          </div>

          <div className="mt-4">
            <LineChart
              series={[{ key: "equity", label: "Equity", color: SERIES_COLORS.fair, values: view.equitySeries }]}
              length={run.minutes.length}
              xLabel={(index) => `${clockEt(run.minutes[index].t)} ET`}
              format={formatMoney}
              refLines={[{ y: run.summary.starting_balance, label: `start ${formatMoney(run.summary.starting_balance)}` }]}
              height={140}
              ariaLabel="Equity over the run"
            />
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Market">
            {run.config.assets.map((item) => (
              <button
                key={item}
                type="button"
                role="tab"
                aria-selected={item === asset}
                onClick={() => setSelected(item)}
                className={clsx(
                  "flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition",
                  item === asset ? "border-cyan-300/60 bg-cyan-300/10 text-white" : "border-white/10 text-slate-400 hover:text-white",
                )}
              >
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: ASSET_COLORS[item] }} />
                {item} 15m
              </button>
            ))}
            {currentWindow ? (
              <span className="ml-auto font-mono text-[11px] text-slate-400">
                opened {currentWindow.open.toLocaleString(undefined, { maximumFractionDigits: 4 })} ·{" "}
                {view.minute >= currentWindow.start_minute + 14 ? `closed ${currentWindow.outcome.toUpperCase()}` : "resolving"}
              </span>
            ) : null}
          </div>

          <div className="mt-3 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <p className="text-sm font-semibold text-white">This window · P(up)</p>
              <p className="text-[11px] text-slate-500">Down bids drawn as 1 − price so both sides share one scale. Filled dots are Up fills, rings are Down fills.</p>
              <div className="mt-3">
                {assetSeries ? (
                  <LineChart
                    series={[
                      { key: "fair", label: "Fair P(up)", color: SERIES_COLORS.fair, values: windowSlice(assetSeries.fair_up) },
                      { key: "crowd", label: "Crowd P(up)", color: SERIES_COLORS.crowd, values: windowSlice(assetSeries.crowd_up) },
                      { key: "up", label: "Our Up bid", color: SERIES_COLORS.bidUp, values: windowSlice(assetSeries.bid_up), step: true },
                      {
                        key: "down",
                        label: "1 − our Down bid",
                        color: SERIES_COLORS.bidDown,
                        values: windowSlice(assetSeries.bid_down).map((value) => (value === null ? null : 1 - value)),
                        step: true,
                      },
                    ]}
                    length={windowLength}
                    yDomain={[0, 1]}
                    xLabel={(index) => `${clockEt(run.minutes[Math.min(view.windowStart + index, lastMinute)].t)} ET · min ${index}`}
                    format={cents}
                    markers={windowMarkers}
                    refLines={[{ y: 0.5, label: "50¢" }]}
                    height={200}
                    ariaLabel={`${asset} current window: fair and crowd probability with this desk's bids`}
                  />
                ) : null}
              </div>
            </div>
            <div className="grid gap-4">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm font-semibold text-white">{asset} price · this window</p>
                {assetSeries ? (
                  <div className="mt-2">
                    <LineChart
                      series={[{ key: "price", label: asset, color: ASSET_COLORS[asset], values: windowSlice(assetSeries.price) }]}
                      length={windowLength}
                      xLabel={(index) => `min ${index}`}
                      format={(value) => value.toLocaleString(undefined, { maximumFractionDigits: 4 })}
                      refLines={currentWindow ? [{ y: currentWindow.open, label: "open" }] : []}
                      height={90}
                      ariaLabel={`${asset} price during the current window`}
                    />
                  </div>
                ) : null}
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm font-semibold text-white">Fills tape</p>
                <ul className="mt-2 max-h-36 space-y-1 overflow-y-auto font-mono text-[11px]">
                  {view.fills.length === 0 ? <li className="text-slate-500">No fills yet.</li> : null}
                  {view.fills
                    .slice(-14)
                    .reverse()
                    .map((fill, index) => (
                      <li key={`${fill.minute}-${fill.asset}-${fill.side}-${fill.level}-${index}`} className="grid grid-cols-[3rem_3rem_2.5rem_1fr] gap-2">
                        <span className="text-slate-500">{clockEt(fill.t)}</span>
                        <span className="flex items-center gap-1 text-white">
                          <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: ASSET_COLORS[fill.asset] }} />
                          {fill.asset}
                        </span>
                        <span className={fill.side === "up" ? "text-emerald-300" : "text-rose-300"}>{fill.side === "up" ? "UP" : "DN"}</span>
                        <span className="text-slate-300">
                          {cents(fill.price)} ×{fill.shares} · L{fill.level}
                        </span>
                      </li>
                    ))}
                </ul>
              </div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Fills / hour" value={run.summary.fills_per_hour.toFixed(0)} />
            <StatTile label="Avg pair cost" value={run.summary.avg_pair_cost === null ? "—" : `$${run.summary.avg_pair_cost.toFixed(3)}`} hint="Pairs filled in different minutes can cost more than $1 when fair value moved in between." />
            <StatTile label="Paired P&L" value={formatSignedMoney(run.summary.paired_pnl)} tone={run.summary.paired_pnl >= 0 ? "up" : "down"} />
            <StatTile label="Unpaired P&L" value={formatSignedMoney(run.summary.unpaired_pnl)} tone={run.summary.unpaired_pnl >= 0 ? "up" : "down"} hint="Leftover one-sided shares that rode to resolution: the directional risk the grid took." />
            <StatTile label="Windows won" value={run.summary.window_win_rate === null ? "—" : formatPercent(run.summary.window_win_rate)} />
            <StatTile label="Pairs locked" value={run.summary.pairs_locked.toLocaleString()} />
            <StatTile label="Max drawdown" value={`−${run.summary.max_drawdown_pct.toFixed(1)}%`} tone={run.summary.max_drawdown_pct > 0 ? "down" : "default"} />
            <StatTile label="Fees" value={formatMoney(run.summary.fees)} />
          </div>

          <div className="mt-4 flex flex-wrap justify-between gap-2 font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">
            <span>Paper simulation · modeled market · not financial advice</span>
            <span>TradeReviewDesk · seed {run.config.seed}</span>
          </div>
        </section>
      ) : (
        <Card className="p-8 text-center">
          <p className="text-sm text-slate-400">Run a simulation to see the grid work 15-minute Up/Down windows.</p>
        </Card>
      )}

      {run && view ? (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Inventory skew" subtitle="Up minus Down shares held in the current window, per market. The grid shades its bids against this.">
              <LineChart
                series={run.config.assets.map((item) => ({
                  key: item,
                  label: item,
                  color: ASSET_COLORS[item],
                  values: run.minutes.slice(0, view.minute + 1).map((entry) => entry.inventory[item] ?? 0),
                }))}
                length={run.minutes.length}
                xLabel={(index) => `${clockEt(run.minutes[index].t)} ET`}
                format={(value) => `${value > 0 ? "+" : ""}${value} sh`}
                refLines={[{ y: 0, label: "flat" }]}
                height={150}
                ariaLabel="Net inventory per market over the run"
              />
            </Panel>
            <Panel
              title="Dislocation · crowd − fair"
              subtitle={`${asset} over the run. Observed half-life ${
                run.dislocation_half_life_minutes === null ? "n/a (lag dominates)" : `${run.dislocation_half_life_minutes} min`
              }.`}
            >
              {assetSeries ? (
                <LineChart
                  series={[
                    {
                      key: "dislocation",
                      label: "Crowd − fair",
                      color: SERIES_COLORS.crowd,
                      values: assetSeries.crowd_up.slice(0, view.minute + 1).map((value, index) => value - assetSeries.fair_up[index]),
                    },
                  ]}
                  length={run.minutes.length}
                  xLabel={(index) => `${clockEt(run.minutes[index].t)} ET`}
                  format={(value) => `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}¢`}
                  refLines={[{ y: 0, label: "0" }]}
                  height={150}
                  ariaLabel={`${asset} crowd minus fair probability over the run`}
                />
              ) : null}
            </Panel>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
            <Panel title="Fill arrival" subtitle="Fills by minute of the 15-minute window, across the whole run.">
              <ColumnChart values={run.fill_arrival} labels={run.fill_arrival.map((_, index) => String(index))} ariaLabel="Fills by minute of window" />
            </Panel>
            <Panel title="Resolved windows" subtitle="Latest first, up to the replay position.">
              <div className="max-h-64 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-slate-950 text-[10px] uppercase tracking-[0.14em] text-slate-500">
                    <tr>
                      <th className="pb-2 font-medium">Window</th>
                      <th className="pb-2 font-medium">Result</th>
                      <th className="hidden pb-2 font-medium sm:table-cell">Up / Down</th>
                      <th className="pb-2 font-medium">Pair cost</th>
                      <th className="pb-2 text-right font-medium">P&amp;L</th>
                    </tr>
                  </thead>
                  <tbody className="tabular-nums">
                    {view.resolved.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-3 text-slate-500">
                          No window has closed yet.
                        </td>
                      </tr>
                    ) : null}
                    {[...view.resolved].reverse().slice(0, 40).map((window) => (
                      <tr key={`${window.asset}-${window.index}`} className="border-t border-white/5">
                        <td className="py-1.5 text-slate-300">
                          <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full" style={{ backgroundColor: ASSET_COLORS[window.asset] }} />
                          {window.asset} {clockEt(window.start)}
                        </td>
                        <td className={window.outcome === "up" ? "text-emerald-300" : "text-rose-300"}>{window.outcome === "up" ? "▲ Up" : "▼ Down"}</td>
                        <td className="hidden text-slate-400 sm:table-cell">
                          {window.up_shares} / {window.down_shares}
                        </td>
                        <td className="text-slate-300">{window.avg_pair_cost === null ? "—" : `$${window.avg_pair_cost.toFixed(3)}`}</td>
                        <td className={clsx("text-right font-semibold", window.pnl >= 0 ? "text-emerald-300" : "text-rose-300")}>{formatSignedMoney(window.pnl)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel
              title="Expectancy fan"
              subtitle={
                run.monte_carlo
                  ? `${run.monte_carlo.paths} resampled paths of the next ${run.monte_carlo.trades_per_path} traded windows, from this run's ${run.monte_carlo.sample_size}. The model's assumptions are baked into every path.`
                  : "Needs at least 5 traded windows."
              }
            >
              {run.monte_carlo && view.isComplete ? (
                <MonteCarloFan monteCarlo={run.monte_carlo} startingBalance={run.summary.starting_balance} />
              ) : run.monte_carlo ? (
                <p className="text-sm text-slate-500">Unlocks when the replay reaches the end of the run.</p>
              ) : (
                <p className="text-sm text-slate-500">Too few traded windows to say anything about the spread of outcomes.</p>
              )}
            </Panel>
            <Panel title="Saved simulations" subtitle="The same seed, prices, and rules replay exactly.">
              {runs.length === 0 ? (
                <p className="text-sm text-slate-500">Saved simulations show up here.</p>
              ) : (
                <ul className="space-y-2">
                  {runs.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        onClick={() => void openRun(item.id)}
                        className={clsx(
                          "grid w-full grid-cols-[1fr_auto] gap-x-3 rounded-xl border px-3 py-2 text-left text-xs transition",
                          item.id === run.id ? "border-cyan-300/50 bg-cyan-300/10" : "border-white/10 hover:border-white/25",
                        )}
                      >
                        <span className="font-medium text-white">{formatRunLabel(item.created_at)}</span>
                        <span className={clsx("text-right font-semibold tabular-nums", item.summary.net_pnl >= 0 ? "text-emerald-300" : "text-rose-300")}>
                          {formatSignedMoney(item.summary.net_pnl)}
                        </span>
                        <span className="text-slate-400">
                          {loadingId === item.id ? "Loading…" : `${item.config.assets.join("/")} · ${item.config.hours}h · ${item.data_source}`}
                        </span>
                        <span className="text-right tabular-nums text-slate-500">efficient {formatSignedMoney(item.baseline.net_pnl)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
          {run.notes.length ? <StatePanel title="Data notes" message={run.notes.join(" ")} tone="warning" /> : null}
        </>
      ) : null}

      <StatePanel
        title="Modeled market, on purpose"
        message={
          run?.disclaimer ??
          "Underlying prices are real or synthetic; the prediction market and its fills are modeled. Compare every result with the efficient-crowd baseline."
        }
        tone="warning"
      />
    </div>
  );
}
