import Link from "next/link";

const sections = [
  {
    title: "Service scope",
    body:
      "TradeReviewDesk is a workflow and journaling product for self-directed traders. It is designed to help you organize preparation, checklist use, trade review, and weekly reflection. It is not a brokerage, order-routing venue, or advisory service.",
  },
  {
    title: "No advisory relationship",
    body:
      "Use of TradeReviewDesk does not create an investment adviser, broker-dealer, fiduciary, or other professional relationship. Content generated in the product is informational workflow support only and should not be treated as a recommendation to buy, sell, hold, or size a position in any security or instrument.",
  },
  {
    title: "User responsibility",
    body:
      "You are solely responsible for your market research, trading decisions, risk management, tax treatment, regulatory compliance, and any losses that result from your activity. You should independently verify any information before acting on it.",
  },
  {
    title: "Beta product status",
    body:
      "This MVP is an early-stage product. Features, prompts, outputs, pricing, availability, data handling, and account controls may change as the product evolves. These terms are a structured launch draft and should be reviewed by counsel before broad public release.",
  },
  {
    title: "Acceptable use",
    body:
      "You may not use TradeReviewDesk to violate law, evade market rules, impersonate another person, abuse the service, or attempt to extract credentials, source prompts, or restricted system behavior. We may suspend access if use creates legal, security, or operational risk.",
  },
  {
    title: "Availability and liability",
    body:
      "TradeReviewDesk is provided on an as-is and as-available basis during this MVP phase. We do not guarantee uptime, accuracy, completeness, or fitness for a particular purpose. To the maximum extent permitted by law, TradeReviewDesk disclaims liability for indirect, incidental, consequential, or trading-related losses.",
  },
];

export default function TermsPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-20 text-slate-300">
      <div className="space-y-4">
        <p className="text-sm uppercase tracking-[0.24em] text-cyan-300">Terms</p>
        <h1 className="text-5xl font-semibold text-white">TradeReviewDesk Terms of Use</h1>
        <p className="text-lg text-slate-300">
          This page is an MVP launch draft that defines the product boundary clearly and is intended for later legal review.
        </p>
      </div>
      <div className="mt-10 space-y-6">
        {sections.map((section) => (
          <section key={section.title} className="rounded-3xl border border-white/10 bg-white/[0.03] p-6">
            <h2 className="text-xl font-medium text-white">{section.title}</h2>
            <p className="mt-3 leading-7 text-slate-300">{section.body}</p>
          </section>
        ))}
      </div>
      <p className="mt-10 text-sm text-slate-400">
        Related documents: <Link href="/legal/privacy" className="text-cyan-300">Privacy</Link> and{" "}
        <Link href="/legal/disclaimer" className="text-cyan-300">Disclaimer</Link>.
      </p>
    </main>
  );
}
