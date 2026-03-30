import Link from "next/link";

import { Badge, Card, SectionHeading } from "@tradenoc/ui";

import { MarketingSection } from "@/components/marketing-section";

const features = [
  "Premarket briefs that prioritize attention, reminders, and daily focus.",
  "Checklist-based trade preparation so execution follows a routine, not emotion.",
  "Post-close debriefs that turn trades and notes into useful review output.",
  "Weekly reviews that surface recurring strengths, mistakes, and next actions.",
];

export default function HomePage() {
  return (
    <main>
      <MarketingSection className="grid items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-8">
          <Badge>Discipline over noise</Badge>
          <div className="space-y-6">
            <h1 className="max-w-4xl text-5xl font-semibold tracking-tight text-white sm:text-6xl">
              Run your trading like an operating system.
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-slate-300">
              TradeReviewDesk helps self-directed traders plan better, trade calmer, and review smarter with AI-powered
              workflow support. It is not a signal engine, not copy trading, and not auto-execution.
            </p>
            <p className="max-w-2xl text-sm leading-7 text-slate-400">
              Any references to symbols, setups, or session priorities are for journaling and workflow context only,
              not recommendations to buy, sell, hold, or size a position.
            </p>
          </div>
          <div className="flex flex-wrap gap-4">
            <Link
              href="/signup"
              className="rounded-full bg-cyan-300 px-6 py-3 text-sm font-medium text-slate-950 transition hover:bg-cyan-200"
            >
              Start free
            </Link>
            <Link
              href="/pricing"
              className="rounded-full border border-white/15 px-6 py-3 text-sm font-medium text-white transition hover:bg-white/5"
            >
              View pricing
            </Link>
          </div>
        </div>
        <Card className="grid gap-4">
          <div className="rounded-3xl border border-cyan-300/10 bg-cyan-300/5 p-5">
            <p className="text-sm uppercase tracking-[0.2em] text-cyan-200">Today&apos;s control plane</p>
            <p className="mt-3 text-2xl font-semibold text-white">Premarket brief ready</p>
            <p className="mt-2 text-sm text-slate-300">3 symbols need focus. 2 event reminders. Checklist staged.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl border border-white/10 p-5">
              <p className="text-sm text-slate-400">Weekly cadence</p>
              <p className="mt-2 text-3xl font-semibold text-white">3x</p>
              <p className="mt-2 text-sm text-slate-300">Target usage per week for consistent behavior review.</p>
            </div>
            <div className="rounded-3xl border border-white/10 p-5">
              <p className="text-sm text-slate-400">Positioning</p>
              <p className="mt-2 text-3xl font-semibold text-white">Ops layer</p>
              <p className="mt-2 text-sm text-slate-300">Your broker places trades. TradeReviewDesk runs the process.</p>
            </div>
          </div>
        </Card>
      </MarketingSection>

      <MarketingSection>
        <SectionHeading
          eyebrow="Problem"
          title="Most retail trading problems are process problems."
          body="Inconsistent premarket prep, impulsive entries, weak journaling, and poor review habits create avoidable mistakes. TradeReviewDesk gives those habits an operating cadence."
        />
      </MarketingSection>

      <MarketingSection className="grid gap-6 lg:grid-cols-2">
        <SectionHeading
          eyebrow="How it works"
          title="A command center built around the moments that matter."
          body="TradeReviewDesk focuses on the daily and weekly workflow touchpoints that shape discipline."
        />
        <div className="grid gap-4">
          {[
            "Set up your profile, trading style, watchlist, and biggest challenges.",
            "Generate a premarket brief that summarizes priorities and process reminders.",
            "Use checklist runs before entries so execution stays deliberate.",
            "Close the loop with debriefs and weekly reviews that surface behavior patterns.",
          ].map((item, index) => (
            <Card key={item}>
              <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Step {index + 1}</p>
              <p className="mt-2 text-base text-slate-200">{item}</p>
            </Card>
          ))}
        </div>
      </MarketingSection>

      <MarketingSection>
        <SectionHeading
          eyebrow="Features"
          title="Everything in the MVP is built around repeatable workflow."
          body="The first release stays narrow on purpose: preparation, checklists, debriefs, weekly review, and history."
        />
        <div className="mt-10 grid gap-4 lg:grid-cols-2">
          {features.map((feature) => (
            <Card key={feature}>
              <p className="text-base text-slate-200">{feature}</p>
            </Card>
          ))}
        </div>
      </MarketingSection>
    </main>
  );
}
