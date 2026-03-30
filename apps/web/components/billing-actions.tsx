"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { SubscriptionPlan } from "@tradenoc/types";

function getActionLabel(plan: SubscriptionPlan, currentPlan: SubscriptionPlan) {
  if (plan === currentPlan) {
    return "Current plan";
  }
  if (plan === "free") {
    return "Use Free";
  }
  return currentPlan === "free" ? `Start ${plan === "pro" ? "Pro" : "Elite"}` : `Switch to ${plan === "pro" ? "Pro" : "Elite"}`;
}

export function CheckoutButton({
  plan,
  currentPlan,
  isAuthenticated,
  authEnabled,
  className,
}: {
  plan: SubscriptionPlan;
  currentPlan: SubscriptionPlan;
  isAuthenticated: boolean;
  authEnabled: boolean;
  className?: string;
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState<string | null>(null);
  const isCurrentPlan = plan === currentPlan;

  function handleClick() {
    if (isCurrentPlan) {
      return;
    }

    if (authEnabled && !isAuthenticated) {
      router.push("/signup");
      return;
    }

    setMessage(null);
    startTransition(async () => {
      const response = await fetch("/api/billing/create-checkout-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan,
          success_url: `${window.location.origin}/app/settings?billing=success`,
          cancel_url: `${window.location.origin}/pricing?billing=cancelled`,
        }),
      });

      const data = (await response.json()) as { url?: string; message?: string; detail?: string };
      if (!response.ok || !data.url) {
        setMessage(data.detail ?? data.message ?? "Unable to start checkout.");
        return;
      }

      window.location.assign(data.url);
    });
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={isPending || isCurrentPlan}
        className={className}
      >
        {isPending ? "Opening..." : getActionLabel(plan, currentPlan)}
      </button>
      {message ? <p className="text-sm text-rose-300">{message}</p> : null}
      {authEnabled && !isAuthenticated ? (
        <p className="text-sm text-slate-400">
          Checkout requires an account. <Link href="/signup" className="text-cyan-300">Create one first.</Link>
        </p>
      ) : null}
    </div>
  );
}

export function BillingPortalButton({
  className,
}: {
  className?: string;
}) {
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState<string | null>(null);

  function handleClick() {
    setMessage(null);
    startTransition(async () => {
      const response = await fetch("/api/billing/create-portal-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          return_url: `${window.location.origin}/app/settings?billing=manage`,
        }),
      });

      const data = (await response.json()) as { url?: string; message?: string; detail?: string };
      if (!response.ok || !data.url) {
        setMessage(data.detail ?? data.message ?? "Unable to open billing management.");
        return;
      }

      window.location.assign(data.url);
    });
  }

  return (
    <div className="space-y-2">
      <button type="button" onClick={handleClick} disabled={isPending} className={className}>
        {isPending ? "Opening..." : "Manage billing"}
      </button>
      {message ? <p className="text-sm text-rose-300">{message}</p> : null}
    </div>
  );
}
