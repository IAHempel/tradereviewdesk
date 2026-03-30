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
