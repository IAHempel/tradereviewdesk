import type { BinaryAsset, BinaryConfig, BinaryFill, BinaryRun, BinaryWindow } from "@tradenoc/types";

export const BINARY_ASSETS: BinaryAsset[] = ["BTC", "ETH", "SOL", "XRP", "DOGE"];

// Validated categorical steps for the dark surface (slots 1-5, fixed order). Color follows the entity.
export const ASSET_COLORS: Record<BinaryAsset, string> = {
  BTC: "#3987e5",
  ETH: "#d95926",
  SOL: "#199e70",
  XRP: "#c98500",
  DOGE: "#d55181",
};

export const SERIES_COLORS = {
  fair: "#3987e5",
  crowd: "#d95926",
  bidUp: "#199e70",
  bidDown: "#c98500",
};

export const FALLBACK_BINARY_CONFIG: BinaryConfig = {
  assets: ["BTC", "ETH", "SOL"],
  data_source: "synthetic",
  end_at: null,
  hours: 4,
  starting_balance: 1000,
  shares_per_level: 10,
  levels: 3,
  level_step_cents: 1,
  half_spread_cents: 2,
  max_shares_per_side: 100,
  inventory_skew_cents: 3,
  stop_quoting_minutes: 2,
  queue_fill_probability: 0.3,
  maker_fee_bps: 0,
  crowd_lag_minutes: 1,
  crowd_noise_cents: 1,
  dislocation_half_life_minutes: 3,
  crowd_spread_cents: 2,
  seed: null,
};

const etClock = new Intl.DateTimeFormat("en-US", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "America/New_York" });
const etDay = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "America/New_York" });

export function clockEt(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : etClock.format(date);
}

export function dayEt(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : etDay.format(date);
}

export function cents(probability: number): string {
  return `${(probability * 100).toFixed(1)}¢`;
}

export interface BinaryView {
  minute: number;
  equitySeries: number[];
  resolved: BinaryWindow[];
  fills: BinaryFill[];
  pnl: number;
  fillsSoFar: number;
  pairsSoFar: number;
  windowIndex: number;
  windowStart: number;
  isComplete: boolean;
}

/** Everything the binary desk shows at a replay minute, using only what had happened by then. */
export function deriveBinaryView(run: BinaryRun, minute: number): BinaryView {
  const index = Math.max(0, Math.min(minute, run.minutes.length - 1));
  const resolved = run.windows.filter((window) => window.start_minute + 15 <= index + 1);
  const equitySeries = run.minutes.slice(0, index + 1).map((item) => item.equity);
  const windowIndex = Math.floor(index / 15);
  return {
    minute: index,
    equitySeries,
    resolved,
    fills: run.fills.filter((fill) => fill.minute <= index),
    pnl: run.minutes[index].equity - run.summary.starting_balance,
    fillsSoFar: run.minutes.slice(0, index + 1).reduce((total, item) => total + item.fills, 0),
    pairsSoFar: resolved.reduce((total, window) => total + window.pairs, 0),
    windowIndex,
    windowStart: windowIndex * 15,
    isComplete: index === run.minutes.length - 1,
  };
}

export function assumptionLine(config: BinaryConfig): string {
  const lag = config.crowd_lag_minutes === 0 ? "as fast as you" : `${config.crowd_lag_minutes} min behind you`;
  return `Crowd ${lag}, ±${config.crowd_noise_cents}¢ noise (half-life ${config.dislocation_half_life_minutes} min), ${Math.round(
    config.queue_fill_probability * 100,
  )}% queue odds`;
}
