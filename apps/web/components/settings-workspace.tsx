"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Card } from "@tradenoc/ui";
import type { Profile, SubscriptionSummary, TradingStyle, Watchlist } from "@tradenoc/types";

import { BillingPortalButton, CheckoutButton } from "@/components/billing-actions";
import { WatchlistPanel } from "@/components/watchlist-panel";

const tradingStyles: TradingStyle[] = ["day", "swing", "options", "mixed"];
const brokerPlatformOptions = [
  "Charles Schwab thinkorswim",
  "Fidelity",
  "Robinhood",
  "E*TRADE",
  "Interactive Brokers",
  "Merrill Edge",
  "Webull",
  "TradeStation",
  "Tastytrade",
  "Public",
  "SoFi Invest",
  "J.P. Morgan Self-Directed Investing",
  "Vanguard",
  "Ally Invest",
  "Moomoo",
  "Firstrade",
  "Lightspeed",
  "M1 Finance",
  "Cobra Trading",
  "CenterPoint Securities",
] as const;

const OTHER_BROKER_VALUE = "other";

async function readClientPayload(response: Response): Promise<{ detail?: string; message?: string }> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as { detail?: string; message?: string };
  }

  const text = await response.text();
  if (text.trim().startsWith("<!DOCTYPE") || text.trim().startsWith("<html")) {
    return {
      message:
        "The profile save request returned HTML instead of JSON. Check that the deployed web app is pointing at the live Railway API.",
    };
  }

  return { message: text || "The request returned an unexpected response." };
}

export function SettingsWorkspace({
  profile,
  watchlists,
  subscription,
  authEnabled,
  isAuthenticated,
}: {
  profile: Profile | null;
  watchlists: Watchlist[];
  subscription: SubscriptionSummary | null;
  authEnabled: boolean;
  isAuthenticated: boolean;
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [selectedBrokerPlatform, setSelectedBrokerPlatform] = useState<string>(
    profile?.broker_platform && brokerPlatformOptions.includes(profile.broker_platform as (typeof brokerPlatformOptions)[number])
      ? profile.broker_platform
      : profile?.broker_platform
        ? OTHER_BROKER_VALUE
        : "",
  );
  const [customBrokerPlatform, setCustomBrokerPlatform] = useState<string>(
    profile?.broker_platform && !brokerPlatformOptions.includes(profile.broker_platform as (typeof brokerPlatformOptions)[number])
      ? profile.broker_platform
      : "",
  );

  const currentPlan = subscription?.plan ?? "free";
  const billingStatus = subscription?.status ?? "active";
  const onboardingComplete = profile?.onboarding_completed ?? false;

  async function handleProfileSubmit(formData: FormData) {
    setProfileMessage(null);

    const payload = {
      display_name: String(formData.get("display_name") ?? "").trim() || null,
      trading_style: String(formData.get("trading_style") ?? "mixed"),
      pain_points: String(formData.get("pain_points") ?? "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      broker_platform:
        (() => {
          const selectedValue = String(formData.get("broker_platform_selection") ?? "").trim();
          const customValue = String(formData.get("broker_platform_other") ?? "").trim();
          if (selectedValue === OTHER_BROKER_VALUE) {
            return customValue || null;
          }
          return selectedValue || null;
        })(),
      onboarding_completed: formData.get("onboarding_completed") === "on",
    };

    startTransition(async () => {
      const response = await fetch("/api/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await readClientPayload(response);
      if (!response.ok) {
        setProfileMessage(data.detail ?? data.message ?? "Profile update failed. Check the API connection and try again.");
        return;
      }

      setProfileMessage("Profile updated.");
      router.refresh();
    });
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <Card>
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-lg font-medium text-white">Profile and onboarding</h2>
              <span
                className={`rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] ${
                  onboardingComplete
                    ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-200"
                    : "border-amber-400/20 bg-amber-400/10 text-amber-200"
                }`}
              >
                {onboardingComplete ? "Complete" : "Incomplete"}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-300">
              Save the core context TradeReviewDesk uses to personalize daily prep and reviews.
            </p>
            <p className="mt-2 text-sm text-slate-400">
              Changes are not saved until you click <span className="font-medium text-white">Save profile &amp; onboarding</span>.
            </p>
          </div>
        </div>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-amber-300/45 bg-amber-300/10 px-4 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-200">Save Required</p>
            <p className="mt-1 text-sm text-slate-200">Profile and onboarding changes stay local to this form until you save them.</p>
          </div>
          <button
            type="submit"
            form="profile-settings-form"
            disabled={isPending}
            className="inline-flex items-center justify-center rounded-full border border-amber-100 bg-amber-300 px-5 py-3 text-sm font-bold uppercase tracking-[0.14em] text-slate-950 shadow-[0_12px_30px_rgba(251,191,36,0.22)] transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-60"
            style={{ backgroundColor: "#fbbf24", color: "#020617", borderColor: "#fef3c7" }}
          >
            {isPending ? "Saving..." : "Save Profile & Onboarding"}
          </button>
        </div>
        <form id="profile-settings-form" action={handleProfileSubmit} className="grid gap-4">
          <label className="grid gap-2 text-sm text-slate-300">
            Display name
            <input
              name="display_name"
              defaultValue={profile?.display_name ?? ""}
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            Trading style
            <select
              name="trading_style"
              defaultValue={profile?.trading_style ?? "mixed"}
              className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
            >
              {tradingStyles.map((style) => (
                <option key={style} value={style}>
                  {style}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            Pain points
            <input
              name="pain_points"
              defaultValue={profile?.pain_points.join(", ") ?? ""}
              placeholder="discipline, risk sizing, overtrading"
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            Broker or platform
            <select
              name="broker_platform_selection"
              value={selectedBrokerPlatform}
              onChange={(event) => setSelectedBrokerPlatform(event.target.value)}
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
              style={{ colorScheme: "dark" }}
            >
              <option value="" className="bg-slate-950 text-white">Select a broker or platform</option>
              {brokerPlatformOptions.map((option) => (
                <option key={option} value={option} className="bg-slate-950 text-white">{option}</option>
              ))}
              <option value={OTHER_BROKER_VALUE} className="bg-slate-950 text-white">Other</option>
            </select>
          </label>
          {selectedBrokerPlatform === OTHER_BROKER_VALUE ? (
            <label className="grid gap-2 text-sm text-slate-300">
              Other broker or platform
              <input
                name="broker_platform_other"
                value={customBrokerPlatform}
                onChange={(event) => setCustomBrokerPlatform(event.target.value)}
                placeholder="Enter another broker or platform"
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
              />
            </label>
          ) : (
            <input name="broker_platform_other" type="hidden" value="" />
          )}
          <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-slate-300">
            <input
              type="checkbox"
              name="onboarding_completed"
              defaultChecked={profile?.onboarding_completed ?? false}
              className="size-4 accent-cyan-300"
            />
            Mark onboarding as complete
          </label>
          <p className="text-sm text-slate-400">{profileMessage ?? "Profile changes save through the backend API."}</p>
        </form>
      </Card>

      <WatchlistPanel watchlists={watchlists} />

      <Card className="xl:col-span-2">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-medium text-white">Billing and access</h2>
            <p className="mt-2 text-sm text-slate-300">
              Subscription state controls premium workflows like checklists, debriefs, and weekly reviews.
            </p>
          </div>
          <div className="rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-slate-300">
            Plan <span className="font-medium text-white">{currentPlan}</span> | Status{" "}
            <span className="font-medium text-white">{billingStatus}</span>
          </div>
        </div>
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr_1fr]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <p className="text-sm uppercase tracking-[0.18em] text-cyan-300">Free</p>
            <p className="mt-3 text-sm text-slate-300">Premarket prep, manual trades, and baseline workflow access.</p>
            <div className="mt-4">
              <CheckoutButton plan="free" currentPlan={currentPlan} authEnabled={authEnabled} isAuthenticated={isAuthenticated} className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-cyan-300/60 disabled:opacity-60" />
            </div>
          </div>
          <div className="rounded-2xl border border-cyan-300/30 bg-cyan-300/10 p-4">
            <p className="text-sm uppercase tracking-[0.18em] text-cyan-300">Pro</p>
            <p className="mt-3 text-sm text-slate-300">Unlock checklists, full debriefs, and weekly review workflows.</p>
            <div className="mt-4">
              <CheckoutButton plan="pro" currentPlan={currentPlan} authEnabled={authEnabled} isAuthenticated={isAuthenticated} className="rounded-full bg-cyan-300 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-200 disabled:opacity-60" />
            </div>
          </div>
          <div className="rounded-2xl border border-emerald-300/30 bg-emerald-300/10 p-4">
            <p className="text-sm uppercase tracking-[0.18em] text-emerald-300">Elite</p>
            <p className="mt-3 text-sm text-slate-300">Reserve advanced analytics and export-ready reporting for later expansion.</p>
            <div className="mt-4">
              <CheckoutButton plan="elite" currentPlan={currentPlan} authEnabled={authEnabled} isAuthenticated={isAuthenticated} className="rounded-full bg-emerald-300 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-200 disabled:opacity-60" />
            </div>
          </div>
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
          <p className="text-sm text-slate-400">
            {subscription?.is_stub
              ? "Stripe keys are still in stub mode locally, so checkout and billing management resolve to safe in-app redirects."
              : "Billing actions route through Stripe and subscription state syncs back into the app."}
          </p>
          <BillingPortalButton className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-cyan-300/60" />
        </div>
      </Card>
    </div>
  );
}
