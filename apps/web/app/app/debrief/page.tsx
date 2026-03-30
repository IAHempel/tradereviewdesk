import { getReportJobs, getReports, getSubscription, getTrades } from "@/lib/api";
import { getLatestReportByType, getLatestReportJobByType } from "@/lib/reports";
import { AppShell } from "@/components/app-shell";
import { ComplianceNotice } from "@/components/compliance-notice";
import { ListCard } from "@/components/page-cards";
import { ReportGenerator } from "@/components/report-generator";
import { DebriefReportView } from "@/components/report-view";
import { StatePanel } from "@/components/state-panels";
import { TradeWorkspace } from "@/components/trade-workspace";

export default async function DebriefPage() {
  const [reports, trades, reportJobs, subscription] = await Promise.all([
    getReports(),
    getTrades(),
    getReportJobs(),
    getSubscription(),
  ]);
  const latestDebriefReport = getLatestReportByType(reports, "debrief");
  const latestDebriefJob = getLatestReportJobByType(reportJobs, "debrief");

  return (
    <AppShell
      title="Post-Close Debrief"
      description="Review the session through behavior, execution quality, and checklist adherence."
    >
      {trades.length === 0 ? (
        <div className="mb-4">
          <StatePanel
            title="No trades saved yet"
            message="You can still write a reflective debrief, but saved trades make the review much more concrete and trustworthy."
            tone="warning"
          />
        </div>
      ) : null}
      <div className="mb-4">
        <TradeWorkspace trades={trades} />
      </div>
      <div className="mb-4">
        <ReportGenerator
          endpoint="/api/reports/debrief"
          title="Generate today&apos;s debrief"
          description="Add session notes and the app will combine them with your saved trades and checklist runs."
          textareaLabel="Session notes"
          placeholder={"Felt patient in the first hour\nExit discipline slipped into the close\nNeed clearer setup tags"}
          buttonLabel="Generate debrief"
          latestJob={latestDebriefJob}
          requiredPlan="pro"
          currentPlan={subscription?.plan ?? "free"}
        />
      </div>
      <div className="mb-4">
        <ComplianceNotice message="Debriefs are reflective workflow summaries based on your saved journal inputs. They do not provide investment advice or instruct future trades." />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ListCard
          title="Trade context"
          items={trades.map((trade) => `${trade.symbol} ${trade.side} | PnL ${trade.pnl ?? "n/a"}`)}
          emptyMessage="No trades are available yet. Add manual trades or import a CSV first to give this debrief better evidence."
        />
        <ListCard
          title="Debrief focus"
          items={[
            "Review discipline, not prediction quality.",
            "Compare checklist adherence against actual execution.",
            "Turn repeated mistakes into next-session actions.",
          ]}
        />
      </div>
      <div className="mt-6">
        <DebriefReportView report={latestDebriefReport} latestJob={latestDebriefJob} />
      </div>
    </AppShell>
  );
}
