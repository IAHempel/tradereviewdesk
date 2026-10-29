import "server-only";

import type {
  BillingSessionResult,
  ChecklistRun,
  ChecklistTemplate,
  DeskConfig,
  DeskDataSourceInfo,
  DeskLiveSession,
  DeskRun,
  DeskRunSummary,
  Profile,
  ReportGenerationResult,
  ReportJobRecord,
  ReportRecord,
  SubscriptionSummary,
  TradeEntry,
  Watchlist,
} from "@tradenoc/types";

import { buildInternalAuthHeaders } from "@/lib/auth";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/+$/, "");
}

function resolveApiBaseUrl(): string {
  const configuredBaseUrl = process.env.API_BASE_URL?.trim();

  if (configuredBaseUrl) {
    return normalizeApiBaseUrl(configuredBaseUrl);
  }

  return DEFAULT_API_BASE_URL;
}

export function getResolvedApiBaseUrl(): string {
  return resolveApiBaseUrl();
}

export async function backendFetch(path: string, init?: RequestInit): Promise<Response> {
  const apiBaseUrl = resolveApiBaseUrl();
  const headers = new Headers(init?.headers);
  const authHeaders = await buildInternalAuthHeaders();

  authHeaders.forEach((value, key) => {
    headers.set(key, value);
  });

  if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  return fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
  });
}

export async function getBackendJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await backendFetch(path, init);

  if (!response.ok) {
    throw new Error(`Request failed for ${path}: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getProfileFromBackend(): Promise<Profile | null> {
  try {
    return await getBackendJson<Profile>("/api/v1/profile", { cache: "no-store" });
  } catch {
    return null;
  }
}

export async function getWatchlistsFromBackend(): Promise<Watchlist[]> {
  try {
    return await getBackendJson<Watchlist[]>("/api/v1/watchlists", { cache: "no-store" });
  } catch {
    return [];
  }
}

export async function getSubscriptionFromBackend(): Promise<SubscriptionSummary | null> {
  try {
    return await getBackendJson<SubscriptionSummary>("/api/v1/billing/subscription", { cache: "no-store" });
  } catch {
    return null;
  }
}

export async function getReportsFromBackend(): Promise<ReportRecord[]> {
  try {
    return await getBackendJson<ReportRecord[]>("/api/v1/reports", { cache: "no-store" });
  } catch {
    return [];
  }
}

export async function getReportJobsFromBackend(): Promise<ReportJobRecord[]> {
  try {
    return await getBackendJson<ReportJobRecord[]>("/api/v1/reports/jobs", { cache: "no-store" });
  } catch {
    return [];
  }
}

export async function postReportGenerationToBackend(
  path: string,
  body: Record<string, unknown>,
): Promise<ReportGenerationResult> {
  return await getBackendJson<ReportGenerationResult>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getTradesFromBackend(): Promise<TradeEntry[]> {
  try {
    return await getBackendJson<TradeEntry[]>("/api/v1/trades", { cache: "no-store" });
  } catch {
    return [];
  }
}

export async function getChecklistRunsFromBackend(): Promise<ChecklistRun[]> {
  try {
    return await getBackendJson<ChecklistRun[]>("/api/v1/checklist-runs", { cache: "no-store" });
  } catch {
    return [];
  }
}

export async function getChecklistTemplatesFromBackend(): Promise<ChecklistTemplate[]> {
  try {
    return await getBackendJson<ChecklistTemplate[]>("/api/v1/checklist-templates", { cache: "no-store" });
  } catch {
    return [];
  }
}

export async function createCheckoutSessionInBackend(
  plan: string,
  options?: { success_url?: string; cancel_url?: string },
): Promise<BillingSessionResult> {
  return getBackendJson<BillingSessionResult>("/api/v1/billing/create-checkout-session", {
    method: "POST",
    body: JSON.stringify({
      plan,
      success_url: options?.success_url ?? null,
      cancel_url: options?.cancel_url ?? null,
    }),
  });
}

export async function createPortalSessionInBackend(returnUrl?: string): Promise<BillingSessionResult> {
  return getBackendJson<BillingSessionResult>("/api/v1/billing/create-portal-session", {
    method: "POST",
    body: JSON.stringify({
      return_url: returnUrl ?? null,
    }),
  });
}

export async function getDeskDefaultsFromBackend(): Promise<DeskConfig | null> {
  try {
    return await getBackendJson<DeskConfig>("/api/v1/desk/defaults", { cache: "no-store" });
  } catch {
    return null;
  }
}

export async function getDeskSourcesFromBackend(): Promise<DeskDataSourceInfo[]> {
  try {
    return await getBackendJson<DeskDataSourceInfo[]>("/api/v1/desk/sources", { cache: "no-store" });
  } catch {
    return [];
  }
}

export async function getDeskRunsFromBackend(): Promise<DeskRunSummary[]> {
  try {
    return await getBackendJson<DeskRunSummary[]>("/api/v1/desk/runs", { cache: "no-store" });
  } catch {
    return [];
  }
}

export async function getDeskRunFromBackend(runId: string): Promise<DeskRun | null> {
  try {
    return await getBackendJson<DeskRun>(`/api/v1/desk/runs/${encodeURIComponent(runId)}`, { cache: "no-store" });
  } catch {
    return null;
  }
}

export async function getDeskLiveFromBackend(): Promise<DeskLiveSession | null> {
  try {
    return await getBackendJson<DeskLiveSession | null>("/api/v1/desk/live", { cache: "no-store" });
  } catch {
    return null;
  }
}
