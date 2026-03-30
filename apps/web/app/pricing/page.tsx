import { Card } from "@tradenoc/ui";
import type { PricingTier } from "@tradenoc/types";

import { CheckoutButton } from "@/components/billing-actions";
import { ComplianceNotice } from "@/components/compliance-notice";
import { MarketingSection } from "@/components/marketing-section";
import { getSubscription } from "@/lib/api";
import { getServerUserContext, isClerkAuthEnabled } from "@/lib/auth";

const tiers: PricingTier[] = [
  {
    plan: "free",
    name: "Free",
    price: "$0/month",
    description: "For trying the workflow before committing.",
    features: ["1 daily brief", "Basic watchlist summary", "Limited journal entries", "7-day history"],
    cta: "Start free",
  },
  {
    plan: "pro",
    name: "Pro",
    price: "$24/month",
    description: "For active traders who want structure every day.",
    features: ["Full daily brief", "Checklist trade prep", "Full debriefs", "Weekly review", "90-day history"],
    cta: "Start Pro",
  },
  {
    plan: "elite",
    name: "Elite",
    price: "$59/month",
    description: "For traders who want deeper review and tighter risk awareness.",
    features: ["Advanced weekly analytics", "Event-risk summaries", "Custom rule sets", "Exportable reports"],
    cta: "Go Elite",
  },
];

export default async function PricingPage() {
  const userContext = await getServerUserContext();
  const subscription = userContext || !isClerkAuthEnabled() ? await getSubscription() : null;
  const currentPlan = subscription?.plan ?? "free";

  return (
    <main>
      <MarketingSection>
        <div className="max-w-3xl space-y-5">
          <p className="text-sm uppercase tracking-[0.24em] text-cyan-300">Pricing</p>
          <h1 className="text-5xl font-semibold text-white">Pick the workflow that fits your trading style.</h1>
          <p className="text-lg text-slate-300">
            From daily prep to weekly performance reviews, TradeReviewDesk helps you build a repeatable operating cadence.
          </p>
        </div>
        <div className="mt-10 grid gap-6 lg:grid-cols-3">
          {tiers.map((tier) => (
            <Card key={tier.name} className="flex h-full flex-col">
              <p className="text-sm uppercase tracking-[0.22em] text-cyan-300">{tier.name}</p>
              <p className="mt-4 text-4xl font-semibold text-white">{tier.price}</p>
              <p className="mt-3 text-slate-300">{tier.description}</p>
              <ul className="mt-6 space-y-3 text-sm text-slate-300">
                {tier.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              <div className="mt-8">
                <CheckoutButton
                  plan={tier.plan}
                  currentPlan={currentPlan}
                  authEnabled={isClerkAuthEnabled()}
                  isAuthenticated={Boolean(userContext)}
                  className="rounded-full bg-white px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-slate-100 disabled:opacity-60"
                />
              </div>
            </Card>
          ))}
        </div>
        <div className="mt-8">
          <ComplianceNotice title="All plans keep the same product boundary" message="Every tier is limited to workflow support, journaling, review, and operational reminders. No plan includes investment advice, signals, broker execution, or discretionary trading." />
        </div>
      </MarketingSection>
    </main>
  );
}
