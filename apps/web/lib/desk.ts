import type {
  DeskAgent,
  DeskConfig,
  DeskDataSource,
  DeskFrame,
  DeskPipelineCounts,
  DeskRun,
  DeskSetup,
  DeskSetupEdge,
  DeskTrade,
} from "@tradenoc/types";

export const DESK_SETUPS: DeskSetup[] = ["breakout", "sweep_reclaim", "trend_pullback", "mean_reversion"];

export const SETUP_LABELS: Record<DeskSetup, string> = {
  breakout: "Breakout",
  sweep_reclaim: "Sweep reclaim",
  trend_pullback: "Trend pullback",
  mean_reversion: "Mean reversion",
};

export const FALLBACK_DESK_CONFIG: DeskConfig = {
  data_source: "synthetic",
  end_date: null,
  symbols: ["SPY", "QQQ", "IWM", "AMD"],
  starting_balance: 500,
  risk_per_trade_pct: 1,
  kelly_fraction: 0.25,
  max_open_positions: 3,
  max_daily_loss_pct: 3,
  max_consecutive_losses: 3,
  min_reward_risk: 1.5,
  min_score: 55,
  trail_after_r: 1.5,
  max_leverage: 1,
  fee_bps: 1,
  slippage_bps: 2,
  sessions: 1,
  allowed_setups: DESK_SETUPS,
  use_journal_priors: true,
  seed: null,
};

export interface AgentMeta {
  id: DeskAgent;
  label: string;
  role: string;
  count: (pipeline: DeskPipelineCounts) => string;
}

export const DESK_AGENTS: AgentMeta[] = [
  {
    id: "scout",
    label: "Scout",
    role: "Scans each closed bar for breakouts, sweeps, pullbacks, and stretches.",
    count: (p) => `${p.scout_flagged.toLocaleString()} setups`,
  },
  {
    id: "filter",
    label: "Filter",
    role: "Applies your hard rules: time windows, limits, stop distance, reward:risk.",
    count: (p) => `${p.filter_killed.toLocaleString()} killed`,
  },
  {
    id: "analyst",
    label: "Analyst",
    role: "Scores survivors and keeps a Bayesian win-rate estimate per setup.",
    count: (p) => `${p.analyst_scored.toLocaleString()} scored`,
  },
  {
    id: "risk",
    label: "Risk",
    role: "Sizes by the smaller of your risk cap and fractional Kelly; halts on limits.",
    count: (p) => `${p.risk_sized.toLocaleString()} sized`,
  },
  {
    id: "executor",
    label: "Executor",
    role: "Paper fills at the next bar's open with slippage and fees. Never live.",
    count: (p) => `${p.executor_fills.toLocaleString()} fills`,
  },
  {
    id: "logger",
    label: "Logger",
    role: "Writes a reason for every decision so the run can be audited.",
    count: (p) => `${p.logger_reasons.toLocaleString()} reasons`,
  },
];

const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

export function formatMoney(value: number): string {
  return currency.format(value);
}

function signFor(rounded: string, value: number): string {
  // Decide the sign from the rounded text so a value that displays as zero never reads "−0.00".
  if (Number(rounded.replace(/[^0-9.]/g, "")) === 0) {
    return "";
  }
  return value > 0 ? "+" : "−";
}

export function formatSignedMoney(value: number): string {
  const text = currency.format(Math.abs(value));
  return `${signFor(text, value)}${text}`;
}

export function formatSigned(value: number, digits = 2, suffix = ""): string {
  const text = Math.abs(value).toFixed(digits);
  return `${signFor(text, value)}${text}${suffix}`;
}

export function formatR(value: number): string {
  return formatSigned(value, 2, "R");
}

export function formatPercent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function splitMoney(value: number): { whole: string; cents: string } {
  const [whole, cents = "00"] = currency.format(value).split(".");
  return { whole, cents };
}

export function toneFor(value: number): "up" | "down" | "flat" {
  if (value > 0.004) {
    return "up";
  }
  if (value < -0.004) {
    return "down";
  }
  return "flat";
}

export interface DeskView {
  frame: DeskFrame;
  equitySeries: number[];
  closedTrades: DeskTrade[];
  wins: number;
  losses: number;
  winRate: number | null;
  avgWinR: number | null;
  bestTrade: number | null;
  worstTrade: number | null;
  maxDrawdownPct: number;
  multiple: number;
  pnl: number;
  setupEdges: DeskSetupEdge[];
  isComplete: boolean;
}

function average(values: number[]): number | null {
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : null;
}

/** Everything the desk shows at a replay step, using only what had happened by then. */
export function deriveView(run: DeskRun, step: number): DeskView {
  const index = Math.max(0, Math.min(step, run.frames.length - 1));
  const frame = run.frames[index];
  const equitySeries = run.frames.slice(0, index + 1).map((item) => item.equity);
  const closedTrades = run.trades.filter((trade) => trade.close_step <= frame.step);
  const winners = closedTrades.filter((trade) => trade.pnl > 0);
  const start = run.summary.starting_balance;

  let peak = start;
  let maxDrawdown = 0;
  for (const equity of equitySeries) {
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, (peak - equity) / peak);
  }

  const setupEdges = run.setup_edges.map((edge) => {
    const setupTrades = closedTrades.filter((trade) => trade.setup === edge.setup);
    const liveWins = setupTrades.filter((trade) => trade.pnl > 0).length;
    const liveLosses = setupTrades.length - liveWins;
    const wins = edge.prior_wins + edge.journal_wins + liveWins;
    const total = wins + edge.prior_losses + edge.journal_losses + liveLosses;
    return {
      ...edge,
      live_wins: liveWins,
      live_losses: liveLosses,
      trades: setupTrades.length,
      posterior_win_rate: total > 0 ? wins / total : 0,
      avg_r: average(setupTrades.map((trade) => trade.r_multiple)),
    };
  });

  return {
    frame,
    equitySeries,
    closedTrades,
    wins: winners.length,
    losses: closedTrades.length - winners.length,
    winRate: closedTrades.length ? winners.length / closedTrades.length : null,
    avgWinR: average(winners.map((trade) => trade.r_multiple)),
    bestTrade: closedTrades.length ? Math.max(...closedTrades.map((trade) => trade.pnl)) : null,
    worstTrade: closedTrades.length ? Math.min(...closedTrades.map((trade) => trade.pnl)) : null,
    maxDrawdownPct: maxDrawdown * 100,
    multiple: frame.equity / start,
    pnl: frame.equity - start,
    setupEdges,
    isComplete: index === run.frames.length - 1,
  };
}

export interface ClaimCheck {
  multiple: number;
  dailyReturn: number;
  perTradeGrowth: number | null;
  tradesNeeded: number | null;
  daysAtThisPace: number | null;
}

/**
 * What a "start → end in N days" claim requires, and how long this run's own
 * expectancy would take to get there if it held exactly (it won't: see the fan).
 */
export function checkClaim(start: number, end: number, days: number, run: DeskRun | null): ClaimCheck | null {
  if (!(start > 0) || !(end > 0) || !(days > 0)) {
    return null;
  }

  const multiple = end / start;
  const dailyReturn = multiple ** (1 / days) - 1;
  if (!run || run.trades.length === 0 || run.summary.expectancy_r === null) {
    return { multiple, dailyReturn, perTradeGrowth: null, tradesNeeded: null, daysAtThisPace: null };
  }

  const averageRiskFraction =
    run.trades.reduce((total, trade) => total + trade.risk_dollars, 0) / run.trades.length / run.summary.starting_balance;
  const perTradeGrowth = 1 + run.summary.expectancy_r * averageRiskFraction;
  if (perTradeGrowth <= 1 || multiple <= 1) {
    return { multiple, dailyReturn, perTradeGrowth, tradesNeeded: null, daysAtThisPace: null };
  }

  const tradesNeeded = Math.log(multiple) / Math.log(perTradeGrowth);
  const tradesPerSession = run.trades.length / run.summary.sessions;
  return {
    multiple,
    dailyReturn,
    perTradeGrowth,
    tradesNeeded,
    daysAtThisPace: tradesPerSession > 0 ? tradesNeeded / tradesPerSession : null,
  };
}

const MARKET_TIME_ZONE = "America/New_York";
// Fixed time zones keep server and browser rendering identical, so hydration never disagrees.
const runTimeFormat = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZone: MARKET_TIME_ZONE,
});
const sessionDayFormat = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
const shortDayFormat = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
const isoDayFormat = new Intl.DateTimeFormat("en-CA", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  timeZone: MARKET_TIME_ZONE,
});

export function formatRunLabel(createdAt: string): string {
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) {
    return createdAt;
  }
  return `${runTimeFormat.format(date)} ET`;
}

export const TAPE_LABELS: Record<DeskDataSource, string> = {
  synthetic: "synthetic tape",
  polygon: "Polygon 5-min bars",
};

function parseDay(isoDay: string): Date | null {
  const date = new Date(`${isoDay}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** "Tue, Nov 25" for a replayed trading day; "Session 2" on the synthetic tape. */
export function sessionLabel(run: Pick<DeskRun, "data_source" | "session_labels">, session: number): string {
  const label = run.session_labels?.[session - 1];
  const day = run.data_source === "polygon" && label ? parseDay(label) : null;
  return day ? sessionDayFormat.format(day) : `Session ${session}`;
}

/** Compact marker for chart session dividers: "Nov 25" or "S2". */
export function shortSessionLabel(run: Pick<DeskRun, "data_source" | "session_labels">, session: number): string {
  const label = run.session_labels?.[session - 1];
  const day = run.data_source === "polygon" && label ? parseDay(label) : null;
  return day ? shortDayFormat.format(day) : `S${session}`;
}

export function replayRangeLabel(run: Pick<DeskRun, "data_source" | "session_labels">): string | null {
  if (run.data_source !== "polygon" || !run.session_labels?.length) {
    return null;
  }
  const first = parseDay(run.session_labels[0]);
  const last = parseDay(run.session_labels[run.session_labels.length - 1]);
  if (!first || !last) {
    return null;
  }
  return first.getTime() === last.getTime()
    ? shortDayFormat.format(first)
    : `${shortDayFormat.format(first)} – ${shortDayFormat.format(last)}`;
}

/** The last calendar day before today in New York, as YYYY-MM-DD: the newest day that can be replayed. */
export function latestReplayableDay(): string {
  const today = parseDay(isoDayFormat.format(new Date()));
  if (!today) {
    return "";
  }
  return new Date(today.getTime() - 86_400_000).toISOString().slice(0, 10);
}
