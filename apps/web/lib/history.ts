import type { ChecklistRun, ReportRecord, TradeEntry } from "@tradenoc/types";

export interface HistoryEntry {
  id: string;
  date: string;
  category: "report" | "checklist_run" | "trade";
  title: string;
  summary: string;
  detail: string;
}

export function buildHistoryEntries({
  reports,
  checklistRuns,
  trades,
}: {
  reports: ReportRecord[];
  checklistRuns: ChecklistRun[];
  trades: TradeEntry[];
}): HistoryEntry[] {
  const reportEntries: HistoryEntry[] = reports.map((report) => ({
    id: report.id,
    date: report.report_date,
    category: "report",
    title: report.title,
    summary: `${report.report_type.replace("_", " ")} | ${report.status}`,
    detail: report.disclaimer,
  }));

  const checklistEntries: HistoryEntry[] = checklistRuns.map((run) => ({
    id: run.id,
    date: run.session_date,
    category: "checklist_run",
    title: `${run.symbol ?? "No symbol"} checklist run`,
    summary: `${run.setup_tag ?? "No setup tag"} | confidence ${run.confidence_score ?? "n/a"}`,
    detail: run.reason_for_entry,
  }));

  const tradeEntries: HistoryEntry[] = trades.map((trade) => ({
    id: trade.id,
    date: trade.trade_date,
    category: "trade",
    title: `${trade.symbol} ${trade.side}`,
    summary: `PnL ${trade.pnl ?? "n/a"} | qty ${trade.quantity ?? "n/a"}`,
    detail: trade.notes ?? "No trade note recorded.",
  }));

  return [...reportEntries, ...checklistEntries, ...tradeEntries].sort((left, right) => {
    if (left.date === right.date) {
      return left.title.localeCompare(right.title);
    }

    return right.date.localeCompare(left.date);
  });
}

export function formatHistoryDate(date: string) {
  const parsed = new Date(`${date}T00:00:00`);
  return parsed.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
