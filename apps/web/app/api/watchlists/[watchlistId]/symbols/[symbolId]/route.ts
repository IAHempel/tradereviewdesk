import { NextResponse } from "next/server";

import { getRouteAuthFailureResponse } from "@/lib/auth";
import { backendFetch } from "@/lib/backend";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ watchlistId: string; symbolId: string }> },
) {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const body = await request.json();
    const { watchlistId, symbolId } = await params;
    const response = await backendFetch(`/api/v1/watchlists/${watchlistId}/symbols/${symbolId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to update watchlist symbol." }, { status: 502 });
  }
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ watchlistId: string; symbolId: string }> },
) {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const { watchlistId, symbolId } = await params;
    const response = await backendFetch(`/api/v1/watchlists/${watchlistId}/symbols/${symbolId}`, {
      method: "DELETE",
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to delete watchlist symbol." }, { status: 502 });
  }
}
