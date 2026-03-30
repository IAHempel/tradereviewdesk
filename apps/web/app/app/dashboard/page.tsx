import { getChecklistRuns, getProfile, getReports, getTrades, getWatchlists } from "@/lib/api";
import { buildDashboardPriorities, buildDashboardStatus, buildRecentNotes } from "@/lib/dashboard";
import { MetricCard, ListCard } from "@/components/page-cards";
import { AppShell } from "@/components/app-shell";
import { StatePanel } from "@/components/state-panels";

export default async function DashboardPage() {
  const [profile, watchlists, reports, checklistRuns, trades] = await Promise.all([
    getProfile(),
    getWatchlists(),
    getReports(),
    getChecklistRuns(),
    getTrades(),
  ]);

  const priorities = buildDashboardPriorities(profile, watchlists);
  const notes = buildRecentNotes(profile, watchlists);
  const status = buildDashboardStatus({ profile, watchlists, reports, checklistRuns, trades });

  return (
    <AppShell
      title="Dashboard"
      description="Track today&apos;s workflow status across premarket planning, checklist usage, and review cadence."
    >
      {!profile || watchlists.length === 0 ? (
        <div className="mb-6">
          <StatePanel
            title="Setup is still incomplete"
            message="TradeReviewDesk can run, but the dashboard will feel much sharper once your profile and watchlist are configured."
            tone="warning"
            actionLabel="Open settings"
            actionHref="/app/settings"
          />
        </div>
      ) : null}
      <div className="grid gap-4 md:grid-cols-3">
        {status.metricCards.map((metric) => (
          <MetricCard key={metric.label} label={metric.label} value={metric.value} detail={metric.detail} />
        ))}
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <ListCard title="Today&apos;s priorities" items={priorities} />
        <ListCard title="Recent notes" items={notes} />
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <ListCard
          title="Recent activity"
          items={status.recentActivity.map((entry) => `${entry.date} | ${entry.category.replace("_", " ")} | ${entry.title}`)}
          emptyMessage="Generate reports, save checklist runs, or add trades to populate the command center."
          emptyActionLabel="Start premarket"
          emptyActionHref="/app/premarket"
        />
        <ListCard
          title="System readiness"
          items={[
            status.primaryWatchlist
              ? `Primary watchlist: ${status.primaryWatchlist.name} (${status.primaryWatchlist.symbols.length} symbols)`
              : "Primary watchlist not configured.",
            `Reports available: ${reports.length}`,
            `Checklist runs available: ${checklistRuns.length}`,
            `Trades available: ${trades.length}`,
          ]}
        />
      </div>
    </AppShell>
  );
}
