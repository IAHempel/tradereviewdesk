import { NextResponse } from "next/server";

import { getRouteAuthFailureResponse } from "@/lib/auth";
import {
  backendFetch,
  getChecklistRunsFromBackend,
  getProfileFromBackend,
  getReportsFromBackend,
  getTradesFromBackend,
} from "@/lib/backend";
import { getCurrentWeekRange } from "@/lib/reports";

export async function POST() {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const [profile, reports, trades, checklistRuns] = await Promise.all([
      getProfileFromBackend(),
      getReportsFromBackend(),
      getTradesFromBackend(),
      getChecklistRunsFromBackend(),
    ]);

    if (!profile) {
      return NextResponse.json({ message: "Profile is required before generating a weekly review." }, { status: 400 });
    }

    const { weekStart, weekEnd } = getCurrentWeekRange();
    const debriefSummaries = reports
      .filter((report) => report.report_type === "debrief")
      .map((report) => String(report.parsed_output.session_summary ?? ""))
      .filter(Boolean);
    const checklistRunSummaries = checklistRuns.map((run) =>
      `${run.symbol ?? "Unknown symbol"} checklist scored ${run.confidence_score ?? "n/a"} with ${run.items.filter((item) => item.completed).length}/${run.items.length} items completed.`,
    );

    const response = await backendFetch("/api/v1/reports/weekly-review/generate", {
      method: "POST",
      body: JSON.stringify({
        week_start: weekStart,
        week_end: weekEnd,
        user_profile: profile,
        debrief_summaries: debriefSummaries,
        trade_entries: trades,
        checklist_run_summaries: checklistRunSummaries,
      }),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to generate weekly review." }, { status: 502 });
  }
}
