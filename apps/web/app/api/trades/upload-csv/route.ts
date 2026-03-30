import { NextResponse } from "next/server";

import { getRouteAuthFailureResponse } from "@/lib/auth";
import { backendFetch } from "@/lib/backend";

export async function POST(request: Request) {
  try {
    const authFailure = await getRouteAuthFailureResponse();
    if (authFailure) {
      return authFailure;
    }

    const incoming = await request.formData();
    const file = incoming.get("file");

    if (!(file instanceof File)) {
      return NextResponse.json({ message: "Upload a CSV file." }, { status: 400 });
    }

    const formData = new FormData();
    formData.append("file", file, file.name);

    const response = await backendFetch("/api/v1/trades/upload-csv", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ message: "Unable to upload CSV." }, { status: 502 });
  }
}
