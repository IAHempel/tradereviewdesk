import { getChecklistRuns, getReportJobs, getReports, getSubscription, getTrades } from "@/lib/api";
import { getCurrentWeekRange, getLatestReportByType, getLatestReportJobByType } from "@/lib/reports";
import { AppShell } from "@/components/app-shell";
import { ComplianceNotice } from "@/components/compliance-notice";
import { ListCard } from "@/components/page-cards";
import { ReportGenerator } from "@/components/report-generator";
import { WeeklyReviewReportView } from "@/components/report-view";
import { StatePanel } from "@/components/state-panels";

export default async function WeeklyReviewPage() {
  const [subscription, reports, trades, checklistRuns, reportJobs] = await Promise.all([
    getSubscription(),
    getReports(),
    getTrades(),
    getChecklistRuns(),
    getReportJobs(),
  ]);
  const latestWeeklyReview = getLatestReportByType(reports, "weekly_review");
  const latestWeeklyReviewJob = getLatestReportJobByType(reportJobs, "weekly_review");
  const { weekStart, weekEnd } = getCurrentWeekRange();

  return (
    <AppShell
      title="Weekly Review"
      description="Summarize recurring strengths, repeated mistakes, and process adjustments for the next week."
    >
      {reports.filter((report) => report.report_type === "debrief").length === 0 ? (
        <div className="mb-4">
          <StatePanel
            title="Weekly review input is still thin"
            message="This page becomes much more useful after you have a few debriefs, trades, and checklist runs from the current week."
            tone="warning"
            actionLabel="Open debrief"
            actionHref="/app/debrief"
          />
        </div>
      ) : null}
      <div className="mb-4">
        <ReportGenerator
          endpoint="/api/reports/weekly-review"
          title="Generate this week&apos;s review"
          description="This composes the current week window with saved debriefs, trades, and checklist runs."
          textareaLabel="Weekly context"
          placeholder={"Keep watchlist tighter next week\nReview recurring mistakes in late-session entries"}
          buttonLabel="Generate weekly review"
          latestJob={latestWeeklyReviewJob}
          requiredPlan="pro"
          currentPlan={subscription?.plan ?? "free"}
        />
      </div>
      <div className="mb-4">
        <ComplianceNotice message="Weekly reviews summarize your own workflow patterns. They are not research reports, trade calls, or portfolio recommendations." />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ListCard
          title="Week window"
          items={[
            `Week start: ${weekStart}`,
            `Week end: ${weekEnd}`,
            `Trades available: ${trades.length}`,
            `Checklist runs available: ${checklistRuns.length}`,
          ]}
        />
        <ListCard
          title="Review inputs"
          items={[
            `Debriefs available: ${reports.filter((report) => report.report_type === "debrief").length}`,
            "Weekly reviews stay process-focused and avoid market calls.",
            "Use this page after several debriefs exist for stronger pattern detection.",
          ]}
        />
      </div>
      <div className="mt-6">
        <WeeklyReviewReportView report={latestWeeklyReview} latestJob={latestWeeklyReviewJob} />
      </div>
    </AppShell>
  );
}
