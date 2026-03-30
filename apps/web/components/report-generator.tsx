"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Card } from "@tradenoc/ui";
import type { ReportJobRecord, SubscriptionPlan } from "@tradenoc/types";
import { StatePanel } from "@/components/state-panels";

const planOrder: Record<SubscriptionPlan, number> = {
  free: 0,
  pro: 1,
  elite: 2,
};

export function ReportGenerator({
  endpoint,
  title,
  description,
  textareaLabel,
  placeholder,
  buttonLabel,
  latestJob,
  requiredPlan = "free",
  currentPlan = "free",
}: {
  endpoint: string;
  title: string;
  description: string;
  textareaLabel: string;
  placeholder: string;
  buttonLabel: string;
  latestJob: ReportJobRecord | null;
  requiredPlan?: SubscriptionPlan;
  currentPlan?: SubscriptionPlan;
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState<string | null>(null);
  const isLocked = planOrder[currentPlan] < planOrder[requiredPlan];

  async function handleSubmit(formData: FormData) {
    const rawText = String(formData.get("notes") ?? "");
    const lines = rawText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    setMessage(null);

    if (isLocked) {
      setMessage(`${requiredPlan.toUpperCase()} plan required for this workflow.`);
      return;
    }

    startTransition(async () => {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(
          endpoint.includes("premarket")
            ? {
                manualEvents: lines,
                userPriorities: lines.slice(0, 3),
                priorNotes: lines.slice(3),
              }
            : {
                userNotes: lines,
              },
        ),
      });

      const data = (await response.json()) as {
        job?: {
          status?: string;
          error_message?: string | null;
        };
        detail?: string;
        message?: string;
      };

      if (response.status === 402) {
        setMessage(data.detail ?? "Upgrade required for this workflow.");
      } else if (!response.ok) {
        setMessage(data.detail ?? data.message ?? "Generation failed. Check API availability and try again.");
      } else if (data.job?.status === "failed") {
        setMessage(data.job.error_message ?? "Generation failed after validation.");
      } else if (data.job?.status === "succeeded") {
        setMessage("Report generated.");
      } else {
        setMessage(`Generation status: ${data.job?.status ?? "processing"}.`);
      }

      router.refresh();
    });
  }

  const latestStatus = latestJob ? `${latestJob.status} after ${latestJob.attempts} attempt${latestJob.attempts === 1 ? "" : "s"}.` : null;
  const latestError = latestJob?.status === "failed" ? latestJob.error_message : null;

  return (
    <Card>
      <h2 className="text-lg font-medium text-white">{title}</h2>
      <p className="mt-2 text-sm text-slate-300">{description}</p>
      {latestJob?.status === "failed" ? (
        <div className="mt-4">
          <StatePanel
            title="Latest generation needs attention"
            message={latestJob.error_message ?? "The latest report job failed validation. Adjust the input context and try again."}
            tone="danger"
          />
        </div>
      ) : null}
      <form action={handleSubmit} className="mt-6 grid gap-4">
        <label className="grid gap-2 text-sm text-slate-300">
          {textareaLabel}
          <textarea
            name="notes"
            rows={6}
            placeholder={placeholder}
            className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
          />
        </label>
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-slate-400">
            {message ??
              latestError ??
              latestStatus ??
              (isLocked
                ? `${requiredPlan.toUpperCase()} plan required. Upgrade in settings to enable this generator.`
                : "This sends a real request through the app proxy to the API and refreshes with the latest job state.")}
          </p>
          <div className="flex items-center gap-3">
            {isLocked ? (
              <Link
                href="/app/settings"
                className="rounded-full border border-white/15 px-5 py-3 text-sm font-medium text-white transition hover:border-cyan-300/60"
              >
                Upgrade plan
              </Link>
            ) : null}
            <button
              type="submit"
              disabled={isPending || isLocked}
              className="rounded-full bg-cyan-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-cyan-200 disabled:opacity-60"
            >
              {isPending ? "Generating..." : buttonLabel}
            </button>
          </div>
        </div>
      </form>
    </Card>
  );
}
