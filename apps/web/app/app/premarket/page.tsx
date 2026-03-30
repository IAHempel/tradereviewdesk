import { getProfile, getReportJobs, getReports, getWatchlists } from "@/lib/api";
import { buildDashboardPriorities, getPrimaryWatchlist } from "@/lib/dashboard";
import { getLatestReportByType, getLatestReportJobByType } from "@/lib/reports";
import { ListCard } from "@/components/page-cards";
import { AppShell } from "@/components/app-shell";
import { ComplianceNotice } from "@/components/compliance-notice";
import { ReportGenerator } from "@/components/report-generator";
import { PremarketReportView } from "@/components/report-view";
import { StatePanel } from "@/components/state-panels";

export default async function PremarketPage() {
  const [profile, watchlists, reports, reportJobs] = await Promise.all([
    getProfile(),
    getWatchlists(),
    getReports(),
    getReportJobs(),
  ]);
  const primaryWatchlist = getPrimaryWatchlist(watchlists);
  const latestPremarketReport = getLatestReportByType(reports, "premarket");
  const latestPremarketJob = getLatestReportJobByType(reportJobs, "premarket");
  const marketSnapshot = [
    primaryWatchlist
      ? `${primaryWatchlist.name} loaded with ${primaryWatchlist.symbols.length} symbol${primaryWatchlist.symbols.length === 1 ? "" : "s"}.`
      : "No watchlist data is available yet.",
    profile?.display_name
      ? `${profile.display_name}'s current style is ${profile.trading_style}.`
      : "Profile context is unavailable, so premarket personalization is limited.",
    profile?.broker_platform
      ? `Broker/platform context: ${profile.broker_platform}.`
      : "Add broker/platform context during onboarding for stronger reminders.",
  ];

  const focusChecklist = buildDashboardPriorities(profile, watchlists);

  return (
    <AppShell
      title="Premarket Brief"
      description="A process-first daily brief with watchlist triage, event reminders, and focus notes."
    >
      {!primaryWatchlist ? (
        <div className="mb-4">
          <StatePanel
            title="Watchlist needed for a stronger brief"
            message="You can still generate a premarket brief, but adding a default watchlist will make the output much more focused and useful."
            tone="warning"
            actionLabel="Open settings"
            actionHref="/app/settings"
          />
        </div>
      ) : null}
      <div className="mb-4">
        <ReportGenerator
          endpoint="/api/reports/premarket"
          title="Generate today&apos;s brief"
          description="Add manual events, priorities, or context notes. The app will combine them with your saved profile and watchlist."
          textareaLabel="Manual events and priorities"
          placeholder={"Fed speaker at 10:00 AM\nEarnings follow-through watch\nStay selective on watchlist size"}
          buttonLabel="Generate premarket brief"
          latestJob={latestPremarketJob}
        />
      </div>
      <div className="mb-4">
        <ComplianceNotice message="Premarket briefs are process-support summaries. They are not trade recommendations, price targets, or instructions to enter or avoid a position." />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ListCard title="Market snapshot" items={marketSnapshot} />
        <ListCard
          title="Focus checklist"
          items={focusChecklist}
          emptyMessage="Complete onboarding and add a watchlist to generate a stronger premarket focus list."
          emptyActionLabel="Go to settings"
          emptyActionHref="/app/settings"
        />
      </div>
      <div className="mt-6">
        <PremarketReportView report={latestPremarketReport} latestJob={latestPremarketJob} />
      </div>
    </AppShell>
  );
}
