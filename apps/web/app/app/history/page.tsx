import { getChecklistRuns, getReports, getTrades } from "@/lib/api";
import { AppShell } from "@/components/app-shell";
import { HistoryWorkspace } from "@/components/history-workspace";

export default async function HistoryPage() {
  const [reports, checklistRuns, trades] = await Promise.all([getReports(), getChecklistRuns(), getTrades()]);

  return (
    <AppShell
      title="History"
      description="Browse prior reports, checklist runs, and trade review artifacts."
    >
      <HistoryWorkspace reports={reports} checklistRuns={checklistRuns} trades={trades} />
    </AppShell>
  );
}
