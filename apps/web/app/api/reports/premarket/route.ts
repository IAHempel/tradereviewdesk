import { NextResponse } from "next/server";

import { getRouteAuthFailureResponse } from "@/lib/auth";
import { backendFetch, getProfileFromBackend, getWatchlistsFromBackend } from "@/lib/backend";

export async function POST(request: Request) {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const body = (await request.json()) as {
      manualEvents?: string[];
      userPriorities?: string[];
      priorNotes?: string[];
    };

    const [profile, watchlists] = await Promise.all([getProfileFromBackend(), getWatchlistsFromBackend()]);
    const symbols = watchlists.flatMap((watchlist) => watchlist.symbols.map((symbol) => symbol.symbol));

    if (!profile) {
      return NextResponse.json({ message: "Profile is required before generating a premarket brief." }, { status: 400 });
    }

    const response = await backendFetch("/api/v1/reports/premarket/generate", {
      method: "POST",
      body: JSON.stringify({
        report_date: new Date().toISOString().slice(0, 10),
        user_profile: profile,
        watchlist_symbols: symbols,
        prior_notes: body.priorNotes ?? [],
        manual_events: body.manualEvents ?? [],
        user_priorities: body.userPriorities ?? [],
      }),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to generate premarket report." }, { status: 502 });
  }
}
