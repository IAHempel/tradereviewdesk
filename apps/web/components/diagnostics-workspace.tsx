"use client";

import type { ReportJobRecord, SubscriptionSummary } from "@tradenoc/types";

import { Card } from "@tradenoc/ui";

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  }).format(value);
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not available";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function getStatusTone(status: ReportJobRecord["status"]): string {
  if (status === "failed") {
    return "text-rose-300";
  }
  if (status === "succeeded") {
    return "text-emerald-300";
  }
  return "text-amber-300";
}

export function DiagnosticsWorkspace({
  reportJobs,
  subscription,
}: {
  reportJobs: ReportJobRecord[];
  subscription: SubscriptionSummary | null;
}) {
  const jobsWithUsage = reportJobs.filter((job) => job.usage_metrics);
  const totalInputTokens = jobsWithUsage.reduce((total, job) => total + (job.usage_metrics?.input_tokens ?? 0), 0);
  const totalOutputTokens = jobsWithUsage.reduce((total, job) => total + (job.usage_metrics?.output_tokens ?? 0), 0);
  const totalCost = jobsWithUsage.reduce((total, job) => total + (job.usage_metrics?.estimated_cost_usd ?? 0), 0);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <p className="text-sm uppercase tracking-[0.22em] text-slate-400">Tracked jobs</p>
          <p className="mt-3 text-3xl font-semibold text-white">{reportJobs.length}</p>
          <p className="mt-2 text-sm text-slate-300">Report jobs currently visible in your account history.</p>
        </Card>
        <Card>
          <p className="text-sm uppercase tracking-[0.22em] text-slate-400">Input tokens</p>
          <p className="mt-3 text-3xl font-semibold text-white">{totalInputTokens.toLocaleString()}</p>
          <p className="mt-2 text-sm text-slate-300">Prompt-side token volume across jobs that include usage metrics.</p>
        </Card>
        <Card>
          <p className="text-sm uppercase tracking-[0.22em] text-slate-400">Output tokens</p>
          <p className="mt-3 text-3xl font-semibold text-white">{totalOutputTokens.toLocaleString()}</p>
          <p className="mt-2 text-sm text-slate-300">Completion-side token volume across tracked model calls.</p>
        </Card>
        <Card>
          <p className="text-sm uppercase tracking-[0.22em] text-slate-400">Estimated cost</p>
          <p className="mt-3 text-3xl font-semibold text-white">{formatUsd(totalCost)}</p>
          <p className="mt-2 text-sm text-slate-300">
            Approximate usage spend based on the model price table currently configured in the API.
          </p>
        </Card>
      </div>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-medium text-white">Environment snapshot</h2>
            <p className="mt-2 text-sm text-slate-300">
              Use this view to confirm report generation is working, inspect failures, and keep an eye on token usage
              while the MVP is still under close observation.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-slate-300">
            Current plan: <span className="font-medium text-white">{subscription?.plan ?? "unknown"}</span>
            <br />
            Billing status: <span className="font-medium text-white">{subscription?.status ?? "unknown"}</span>
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="text-lg font-medium text-white">Recent report jobs</h2>
        {reportJobs.length === 0 ? (
          <p className="mt-4 text-sm text-slate-300">
            No report jobs have been recorded yet. Generate a premarket, debrief, or weekly review to populate this
            surface.
          </p>
        ) : (
          <div className="mt-4 space-y-3">
            {reportJobs.map((job) => (
              <div key={job.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm uppercase tracking-[0.18em] text-slate-400">{job.report_type.replace("_", " ")}</p>
                    <p className={`mt-2 text-lg font-semibold ${getStatusTone(job.status)}`}>{job.status}</p>
                  </div>
                  <div className="text-right text-sm text-slate-300">
                    <p>Attempts: {job.attempts}</p>
                    <p>Updated: {formatDate(job.updated_at)}</p>
                  </div>
                </div>
                {job.usage_metrics ? (
                  <div className="mt-4 grid gap-3 md:grid-cols-4">
                    <div className="rounded-2xl border border-white/5 bg-slate-950/60 px-3 py-3 text-sm text-slate-300">
                      <p className="text-slate-400">Model</p>
                      <p className="mt-1 font-medium text-white">{job.usage_metrics.model}</p>
                    </div>
                    <div className="rounded-2xl border border-white/5 bg-slate-950/60 px-3 py-3 text-sm text-slate-300">
                      <p className="text-slate-400">Tokens</p>
                      <p className="mt-1 font-medium text-white">{job.usage_metrics.total_tokens.toLocaleString()}</p>
                    </div>
                    <div className="rounded-2xl border border-white/5 bg-slate-950/60 px-3 py-3 text-sm text-slate-300">
                      <p className="text-slate-400">Input / output</p>
                      <p className="mt-1 font-medium text-white">
                        {job.usage_metrics.input_tokens.toLocaleString()} / {job.usage_metrics.output_tokens.toLocaleString()}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/5 bg-slate-950/60 px-3 py-3 text-sm text-slate-300">
                      <p className="text-slate-400">Estimated cost</p>
                      <p className="mt-1 font-medium text-white">{formatUsd(job.usage_metrics.estimated_cost_usd)}</p>
                    </div>
                  </div>
                ) : (
                  <p className="mt-4 text-sm text-slate-300">
                    Usage metrics are not available for this job yet. Older jobs and local fallback runs may not include
                    model telemetry.
                  </p>
                )}
                {job.error_message ? (
                  <div className="mt-4 rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                    {job.error_message}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
