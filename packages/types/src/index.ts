export type TradingStyle = "day" | "swing" | "options" | "mixed";
export type ReportType = "premarket" | "debrief" | "weekly_review";
export type SubscriptionPlan = "free" | "pro" | "elite";
export type SubscriptionStatus =
  | "active"
  | "trialing"
  | "past_due"
  | "canceled"
  | "incomplete"
  | "checkout_pending"
  | string;

export interface PricingTier {
  name: string;
  plan: SubscriptionPlan;
  price: string;
  description: string;
  features: string[];
  cta: string;
}

export interface SubscriptionSummary {
  plan: SubscriptionPlan;
  status: SubscriptionStatus;
  current_period_end: string | null;
  is_stub: boolean;
}

export interface BillingSessionResult {
  url: string;
  mode: string;
}

export interface DashboardMetric {
  label: string;
  value: string;
  detail: string;
}

export interface Profile {
  email: string;
  display_name: string | null;
  trading_style: TradingStyle;
  pain_points: string[];
  broker_platform: string | null;
  onboarding_completed: boolean;
}

export interface WatchlistSymbol {
  id: string;
  symbol: string;
  notes: string | null;
  display_order: number;
}

export interface Watchlist {
  id: string;
  name: string;
  is_default: boolean;
  symbols: WatchlistSymbol[];
}

export interface ChecklistRunItem {
  label_snapshot: string;
  completed: boolean;
}

export interface ChecklistTemplateItem {
  id: string;
  label: string;
  description: string | null;
  is_required: boolean;
  display_order: number;
}

export interface ChecklistTemplate {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  items: ChecklistTemplateItem[];
}

export interface ChecklistRun {
  id: string;
  template_id: string | null;
  session_date: string;
  symbol: string | null;
  setup_tag: string | null;
  reason_for_entry: string;
  confidence_score: number | null;
  items: ChecklistRunItem[];
}

export interface TradeEntry {
  id: string;
  trade_date: string;
  symbol: string;
  asset_type: "stock" | "option" | "other";
  side: "long" | "short" | "call" | "put" | "other";
  quantity: number | null;
  entry_price: number | null;
  exit_price: number | null;
  pnl: number | null;
  fees: number | null;
  tags: string[];
  notes: string | null;
  source_type: "manual" | "csv_upload";
}

export interface TradeImportPreviewRow {
  row_number: number;
  trade: Omit<TradeEntry, "id">;
}

export interface TradeImportError {
  row_number: number;
  message: string;
  raw_row: Record<string, unknown>;
}

export interface TradeImportResult {
  file_name: string;
  rows_received: number;
  imported_count: number;
  rejected_count: number;
  preview: TradeImportPreviewRow[];
  errors: TradeImportError[];
}

export interface ReportRecord {
  id: string;
  report_type: ReportType;
  title: string;
  report_date: string;
  status: string;
  input_summary: Record<string, unknown>;
  parsed_output: Record<string, unknown>;
  disclaimer: string;
  report_job_id?: string | null;
}

export type ReportJobStatus = "queued" | "processing" | "succeeded" | "failed";

export interface ReportUsageMetrics {
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

export interface ReportJobRecord {
  id: string;
  report_type: ReportType;
  status: ReportJobStatus;
  attempts: number;
  input_payload: Record<string, unknown>;
  error_message: string | null;
  raw_model_output: string | null;
  parsed_output: Record<string, unknown> | null;
  usage_metrics: ReportUsageMetrics | null;
  report_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ReportGenerationResult {
  job: ReportJobRecord;
  report: ReportRecord | null;
}

export type DeskSetup = "breakout" | "sweep_reclaim" | "trend_pullback" | "mean_reversion";
export type DeskAgent = "scout" | "flow" | "filter" | "analyst" | "risk" | "seat" | "executor" | "logger";
export type DeskSide = "long" | "short";
export type DeskDataSource = "synthetic" | "polygon" | "alpaca";

export interface DeskDataSourceInfo {
  id: DeskDataSource;
  label: string;
  available: boolean;
  detail: string;
}

export interface DeskConfig {
  data_source: DeskDataSource;
  end_date: string | null;
  symbols: string[];
  starting_balance: number;
  risk_per_trade_pct: number;
  kelly_fraction: number;
  max_open_positions: number;
  max_daily_loss_pct: number;
  max_consecutive_losses: number;
  min_reward_risk: number;
  min_score: number;
  trail_after_r: number;
  max_leverage: number;
  fee_bps: number;
  slippage_bps: number;
  sessions: number;
  allowed_setups: DeskSetup[];
  use_journal_priors: boolean;
  use_trade_flow: boolean;
  flow_veto: number;
  use_ai_seat: boolean;
  ai_seat_budget: number;
  seat_veto: number;
  seed: number | null;
}

export interface DeskPipelineCounts {
  scout_flagged: number;
  filter_killed: number;
  analyst_scored: number;
  analyst_killed: number;
  risk_sized: number;
  risk_rejected: number;
  executor_fills: number;
  executor_cancels: number;
  executor_exits: number;
  stops_trailed: number;
  stops_widened: number;
  logger_reasons: number;
  flow_vetoes: number;
  seat_reviews: number;
  seat_vetoes: number;
  seat_ai_calls: number;
}

export interface DeskPosition {
  trade_id: string;
  symbol: string;
  side: DeskSide;
  setup: DeskSetup;
  entry: number;
  stop: number;
  target: number;
  last: number;
  r_now: number;
  unrealized: number;
}

export interface DeskScanMark {
  symbol: string;
  setup: DeskSetup;
  side: DeskSide;
  status: "killed" | "ordered";
}

export interface DeskFrame {
  step: number;
  session: number;
  clock: string;
  equity: number;
  positions: DeskPosition[];
  scans: DeskScanMark[];
  pipeline: DeskPipelineCounts;
  halted: boolean;
  flow: Record<string, number>;
}

export interface DeskEvent {
  step: number;
  session: number;
  clock: string;
  agent: DeskAgent;
  symbol: string | null;
  kind: string;
  message: string;
}

export interface DeskTrade {
  id: string;
  symbol: string;
  side: DeskSide;
  setup: DeskSetup;
  session: number;
  open_step: number;
  close_step: number;
  opened_at: string;
  closed_at: string;
  entry: number;
  exit: number;
  stop_initial: number;
  stop_final: number;
  target: number;
  quantity: number;
  risk_dollars: number;
  fees: number;
  pnl: number;
  r_multiple: number;
  exit_reason: "stop" | "trail" | "target" | "bell";
  score: number;
  win_probability: number;
  thesis: string;
}

export interface DeskSeatAnswer {
  id: string;
  question: string;
  probability: number;
  reason: string;
}

export interface DeskSeatVerdict {
  step: number;
  session: number;
  clock: string;
  symbol: string;
  setup: DeskSetup;
  side: DeskSide;
  trade_id: string | null;
  source: "llm" | "heuristic";
  model: string | null;
  answers: DeskSeatAnswer[];
  thesis: string;
  vetoed: boolean;
}

export interface DeskSetupEdge {
  setup: DeskSetup;
  enabled: boolean;
  prior_wins: number;
  prior_losses: number;
  journal_wins: number;
  journal_losses: number;
  live_wins: number;
  live_losses: number;
  posterior_win_rate: number;
  trades: number;
  avg_r: number | null;
}

export interface DeskKillReason {
  agent: DeskAgent;
  code: string;
  label: string;
  count: number;
}

export interface DeskMonteCarloBand {
  trade_index: number;
  p5: number;
  p25: number;
  p50: number;
  p75: number;
  p95: number;
}

export interface DeskMonteCarlo {
  paths: number;
  trades_per_path: number;
  sample_size: number;
  bands: DeskMonteCarloBand[];
  probability_below_start: number;
  probability_drawdown_20: number;
  median_multiple: number;
}

export interface DeskSummary {
  starting_balance: number;
  ending_balance: number;
  net_pnl: number;
  return_pct: number;
  multiple: number;
  trades: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  avg_win_r: number | null;
  avg_loss_r: number | null;
  expectancy_r: number | null;
  profit_factor: number | null;
  max_drawdown_pct: number;
  best_trade: number | null;
  worst_trade: number | null;
  fees_paid: number;
  sessions: number;
  halted_sessions: number;
}

export interface DeskRunSummary {
  id: string;
  created_at: string;
  mode: "paper";
  data_source: DeskDataSource;
  config: DeskConfig;
  summary: DeskSummary;
}

export interface DeskRun extends DeskRunSummary {
  session_labels: string[];
  pipeline: DeskPipelineCounts;
  setup_edges: DeskSetupEdge[];
  kill_reasons: DeskKillReason[];
  trades: DeskTrade[];
  frames: DeskFrame[];
  events: DeskEvent[];
  monte_carlo: DeskMonteCarlo | null;
  disclaimer: string;
  flow_source: string;
  seat_verdicts: DeskSeatVerdict[];
}
