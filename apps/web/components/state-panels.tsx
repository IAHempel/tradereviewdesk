import Link from "next/link";
import type { ReactNode } from "react";

import { Card } from "@tradenoc/ui";

type Tone = "default" | "warning" | "danger" | "success";

const toneClasses: Record<Tone, string> = {
  default: "border-white/10 bg-white/[0.03] text-slate-300",
  warning: "border-cyan-300/20 bg-cyan-300/10 text-cyan-50",
  danger: "border-rose-400/20 bg-rose-400/10 text-rose-50",
  success: "border-emerald-400/20 bg-emerald-400/10 text-emerald-50",
};

export function StatePanel({
  title,
  message,
  tone = "default",
  actionLabel,
  actionHref,
  inlineAction,
}: {
  title: string;
  message: string;
  tone?: Tone;
  actionLabel?: string;
  actionHref?: string;
  inlineAction?: ReactNode;
}) {
  return (
    <div className={`rounded-2xl border px-4 py-4 text-sm ${toneClasses[tone]}`}>
      <p className="font-medium text-white">{title}</p>
      <p className="mt-2">{message}</p>
      {actionLabel && actionHref ? (
        <Link
          href={actionHref}
          className="mt-4 inline-flex rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-cyan-300/60"
        >
          {actionLabel}
        </Link>
      ) : null}
      {inlineAction ? <div className="mt-4">{inlineAction}</div> : null}
    </div>
  );
}

export function LoadingShell({
  title = "Loading workspace",
  description = "Preparing the latest workflow state for this view.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="grid gap-4">
      <Card>
        <div className="animate-pulse space-y-4">
          <div className="h-5 w-40 rounded-full bg-white/10" />
          <div className="h-4 w-72 rounded-full bg-white/5" />
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="h-28 rounded-2xl bg-white/[0.03]" />
            <div className="h-28 rounded-2xl bg-white/[0.03]" />
          </div>
        </div>
      </Card>
      <StatePanel title={title} message={description} />
    </div>
  );
}
