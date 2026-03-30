import type { ChecklistRun, Profile, ReportRecord, TradeEntry, Watchlist } from "@tradenoc/types";

import { buildHistoryEntries } from "@/lib/history";
import { getLatestReportByType } from "@/lib/reports";

export function getPrimaryWatchlist(watchlists: Watchlist[]): Watchlist | null {
  return watchlists.find((watchlist) => watchlist.is_default) ?? watchlists[0] ?? null;
}

export function buildDashboardPriorities(profile: Profile | null, watchlists: Watchlist[]): string[] {
  const primaryWatchlist = getPrimaryWatchlist(watchlists);
  const symbols = primaryWatchlist?.symbols.slice(0, 3).map((item) => item.symbol) ?? [];
  const painPoints = profile?.pain_points ?? [];

  return [
    symbols.length > 0
      ? `Focus the session on ${symbols.join(", ")}.`
      : "Add symbols to the default watchlist to generate a tighter daily focus.",
    painPoints[0]
      ? `Watch for your primary challenge: ${painPoints[0]}.`
      : "Document the main behavior risk you want to avoid before the open.",
    profile?.broker_platform
      ? `Keep execution notes aligned with your ${profile.broker_platform} workflow.`
      : "Capture broker or platform context during onboarding for more tailored reminders.",
  ];
}

export function buildRecentNotes(profile: Profile | null, watchlists: Watchlist[]): string[] {
  const notes = watchlists
    .flatMap((watchlist) => watchlist.symbols)
    .map((symbol) => symbol.notes)
    .filter((note): note is string => Boolean(note))
    .slice(0, 3);

  if (notes.length > 0) {
    return notes;
  }

  return [
    profile?.onboarding_completed
      ? "Start adding setup notes to watchlist symbols so future briefs can be more specific."
      : "Complete onboarding to personalize briefs and checklist defaults.",
    "TradeReviewDesk will surface behavior patterns here once report history is connected.",
  ];
}

export function buildDashboardStatus({
  profile,
  watchlists,
  reports,
  checklistRuns,
  trades,
}: {
  profile: Profile | null;
  watchlists: Watchlist[];
  reports: ReportRecord[];
  checklistRuns: ChecklistRun[];
  trades: TradeEntry[];
}) {
  const primaryWatchlist = getPrimaryWatchlist(watchlists);
  const latestPremarket = getLatestReportByType(reports, "premarket");
  const latestDebrief = getLatestReportByType(reports, "debrief");
  const latestWeekly = getLatestReportByType(reports, "weekly_review");
  const recentActivity = buildHistoryEntries({ reports, checklistRuns, trades }).slice(0, 4);

  return {
    primaryWatchlist,
    metricCards: [
      {
        label: "Premarket",
        value: latestPremarket ? "Generated" : primaryWatchlist?.symbols.length ? "Ready" : "Needs setup",
        detail: latestPremarket
          ? `Latest brief generated for ${latestPremarket.report_date}.`
          : primaryWatchlist?.symbols.length
            ? `${primaryWatchlist.symbols.length} symbol${primaryWatchlist.symbols.length === 1 ? "" : "s"} staged in ${primaryWatchlist.name}.`
            : "Add watchlist symbols to power your daily prep.",
      },
      {
        label: "Execution",
        value: trades.length > 0 ? String(trades.length) : "0",
        detail:
          trades.length > 0
            ? `${checklistRuns.length} checklist run${checklistRuns.length === 1 ? "" : "s"} and ${trades.length} trade ${trades.length === 1 ? "entry" : "entries"} saved.`
            : "No trades recorded yet. Use Debrief to log manual trades or upload CSV exports.",
      },
      {
        label: "Weekly review",
        value: latestWeekly ? "Generated" : profile?.onboarding_completed ? "Ready" : "Pending",
        detail: latestWeekly
          ? `Latest weekly review covers week ending ${latestWeekly.report_date}.`
          : profile?.onboarding_completed
            ? `${latestDebrief ? "Debrief history is available" : "Generate debriefs"} to strengthen the weekly review.`
            : "Finish onboarding to unlock more personalized weekly review context.",
      },
    ],
    recentActivity,
  };
}
