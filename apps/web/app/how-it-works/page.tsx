import { Card } from "@tradenoc/ui";

import { MarketingSection } from "@/components/marketing-section";

export default function HowItWorksPage() {
  return (
    <main>
      <MarketingSection>
        <div className="max-w-3xl space-y-4">
          <p className="text-sm uppercase tracking-[0.24em] text-cyan-300">How it works</p>
          <h1 className="text-5xl font-semibold text-white">A disciplined workflow, not a prediction machine.</h1>
          <p className="text-lg text-slate-300">
            TradeReviewDesk organizes the work around a trading session so prep, execution, and review all reinforce each
            other.
          </p>
          <p className="text-sm text-slate-400">
            It does not provide investment advice, security recommendations, or order execution.
          </p>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-2">
          {[
            "Onboarding captures watchlists, trading style, setups, and pain points.",
            "Premarket briefs summarize priorities, events, and reminders.",
            "Checklist runs create a deliberate gate before entries.",
            "Debriefs and weekly reviews turn data into process improvements.",
          ].map((item) => (
            <Card key={item}>
              <p className="text-slate-200">{item}</p>
            </Card>
          ))}
        </div>
      </MarketingSection>
    </main>
  );
}
