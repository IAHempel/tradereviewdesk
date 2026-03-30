import { NextResponse } from "next/server";

import { getRouteAuthFailureResponse } from "@/lib/auth";
import { backendFetch } from "@/lib/backend";

async function readProxyPayload(response: Response): Promise<Record<string, unknown>> {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return (await response.json()) as Record<string, unknown>;
  }

  const text = await response.text();
  if (text.trim().startsWith("<!DOCTYPE") || text.trim().startsWith("<html")) {
    return {
      message:
        "The profile API returned HTML instead of JSON. Check that API_BASE_URL points to the Railway API domain and that the API route is healthy.",
    };
  }

  return {
    message: text || "The profile API returned an unexpected response.",
  };
}

export async function GET() {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const response = await backendFetch("/api/v1/profile", { cache: "no-store" });
    const data = await readProxyPayload(response);
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { message: error instanceof Error ? error.message : "Unable to load profile." },
      { status: 502 },
    );
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
    const data = await readProxyPayload(response);
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { message: error instanceof Error ? error.message : "Unable to update profile." },
      { status: 502 },
    );
  }
}
