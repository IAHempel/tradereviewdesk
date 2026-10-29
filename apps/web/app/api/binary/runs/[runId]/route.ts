import { NextResponse } from "next/server";

import { getRouteAuthFailureResponse } from "@/lib/auth";
import { backendFetch } from "@/lib/backend";

export async function GET(_request: Request, { params }: { params: Promise<{ runId: string }> }) {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const { runId } = await params;
    const response = await backendFetch(`/api/v1/binary/runs/${encodeURIComponent(runId)}`, { cache: "no-store" });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to load binary run." }, { status: 502 });
  }
}
