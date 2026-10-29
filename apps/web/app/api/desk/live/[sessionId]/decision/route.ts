import { NextResponse } from "next/server";

import { getRouteAuthFailureResponse } from "@/lib/auth";
import { backendFetch } from "@/lib/backend";

export async function POST(request: Request, { params }: { params: Promise<{ sessionId: string }> }) {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const { sessionId } = await params;
    const body = await request.text();
    const response = await backendFetch(`/api/v1/desk/live/${encodeURIComponent(sessionId)}/decision`, {
      method: "POST",
      body: body || "{}",
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to update the live session." }, { status: 502 });
  }
}
