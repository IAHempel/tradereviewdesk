import { NextResponse } from "next/server";

import { getRouteAuthFailureResponse } from "@/lib/auth";
import { backendFetch } from "@/lib/backend";

export async function GET() {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const response = await backendFetch("/api/v1/profile", { cache: "no-store" });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to load profile." }, { status: 502 });
  }
}

export async function PUT(request: Request) {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const body = await request.json();
    const response = await backendFetch("/api/v1/profile", {
      method: "PUT",
      body: JSON.stringify(body),
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to update profile." }, { status: 502 });
  }
}
