"use client";

import { useEffect } from "react";

import { AppShell } from "@/components/app-shell";
import { StatePanel } from "@/components/state-panels";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <AppShell
      title="Something Went Wrong"
      description="This view hit an unexpected issue while loading or saving workflow data."
    >
      <StatePanel
        title="View unavailable"
        message="Try the action again. If the problem keeps happening, the API or billing/auth state may need attention."
        tone="danger"
        inlineAction={
          <button
            type="button"
            onClick={reset}
            className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-rose-300/60"
          >
            Retry view
          </button>
        }
      />
    </AppShell>
  );
}
