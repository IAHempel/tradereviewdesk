import { Card } from "@tradenoc/ui";
import type { ChecklistRun, ReportRecord, TradeEntry } from "@tradenoc/types";

import { buildHistoryEntries, formatHistoryDate } from "@/lib/history";
import { StatePanel } from "@/components/state-panels";

export function HistoryWorkspace({
  reports,
  checklistRuns,
  trades,
}: {
  reports: ReportRecord[];
  checklistRuns: ChecklistRun[];
  trades: TradeEntry[];
}) {
  const entries = buildHistoryEntries({ reports, checklistRuns, trades });

  return (
    <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <Card>
        <h2 className="text-lg font-medium text-white">History summary</h2>
        <div className="mt-4 grid gap-3 text-sm text-slate-300">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
            <p className="text-slate-400">Reports</p>
            <p className="mt-1 text-xl font-semibold text-white">{reports.length}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
            <p className="text-slate-400">Checklist runs</p>
            <p className="mt-1 text-xl font-semibold text-white">{checklistRuns.length}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
            <p className="text-slate-400">Trades</p>
            <p className="mt-1 text-xl font-semibold text-white">{trades.length}</p>
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="text-lg font-medium text-white">Timeline</h2>
        <div className="mt-4 space-y-3">
          {entries.length === 0 ? (
            <StatePanel
              title="No history yet"
              message="Generate reports, create checklist runs, or add trades to populate this timeline and start building a review archive."
              actionLabel="Go to dashboard"
              actionHref="/app/dashboard"
            />
          ) : (
            entries.map((entry) => (
              <div key={`${entry.category}-${entry.id}`} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-base font-medium text-white">{entry.title}</p>
                    <p className="mt-1 text-sm text-slate-400">{entry.summary}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs uppercase tracking-[0.18em] text-cyan-300">{entry.category.replace("_", " ")}</p>
                    <p className="mt-1 text-sm text-slate-400">{formatHistoryDate(entry.date)}</p>
                  </div>
                </div>
                <p className="mt-3 text-sm text-slate-300">{entry.detail}</p>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
