import { NextResponse } from "next/server";

import { getRouteAuthFailureResponse } from "@/lib/auth";
import { backendFetch } from "@/lib/backend";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ tradeId: string }> },
) {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const body = await request.json();
    const { tradeId } = await params;
    const response = await backendFetch(`/api/v1/trades/${tradeId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to update trade entry." }, { status: 502 });
  }
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ tradeId: string }> },
) {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const { tradeId } = await params;
    const response = await backendFetch(`/api/v1/trades/${tradeId}`, {
      method: "DELETE",
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to delete trade entry." }, { status: 502 });
  }
}
