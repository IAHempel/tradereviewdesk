import { NextResponse } from "next/server";

import { getRouteAuthFailureResponse } from "@/lib/auth";
import { backendFetch } from "@/lib/backend";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ watchlistId: string }> },
) {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const body = await request.json();
    const { watchlistId } = await params;
    const response = await backendFetch(`/api/v1/watchlists/${watchlistId}/symbols`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to add watchlist symbol." }, { status: 502 });
  }
}
