import { NextResponse } from "next/server";

import { getRouteAuthFailureResponse } from "@/lib/auth";
import {
  backendFetch,
  getChecklistRunsFromBackend,
  getProfileFromBackend,
  getTradesFromBackend,
} from "@/lib/backend";

export async function POST(request: Request) {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const body = (await request.json()) as {
      userNotes?: string[];
    };

    const [profile, trades, checklistRuns] = await Promise.all([
      getProfileFromBackend(),
      getTradesFromBackend(),
      getChecklistRunsFromBackend(),
    ]);

    if (!profile) {
      return NextResponse.json({ message: "Profile is required before generating a debrief." }, { status: 400 });
    }

    const response = await backendFetch("/api/v1/reports/debrief/generate", {
      method: "POST",
      body: JSON.stringify({
        report_date: new Date().toISOString().slice(0, 10),
        user_profile: profile,
        trade_entries: trades,
        checklist_runs: checklistRuns,
        user_notes: body.userNotes ?? [],
      }),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to generate debrief report." }, { status: 502 });
  }
}
