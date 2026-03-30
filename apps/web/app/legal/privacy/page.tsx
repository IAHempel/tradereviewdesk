import Link from "next/link";

const sections = [
  {
    title: "What TradeReviewDesk collects",
    body:
      "TradeReviewDesk may collect account information, profile/onboarding data, watchlists, checklist entries, trade journal records, generated reports, billing metadata, and operational logs needed to run, secure, and improve the service.",
  },
  {
    title: "How data is used",
    body:
      "We use collected data to authenticate users, persist workflow state, generate reports, support billing, troubleshoot issues, and evaluate product quality. During MVP operation, limited internal review of logs or generated content may occur to diagnose failures and improve reliability.",
  },
  {
    title: "What TradeReviewDesk does not claim",
    body:
      "TradeReviewDesk does not promise confidential treatment beyond the security controls actually in place, and this MVP privacy page should not be treated as final legal advice or a final production privacy policy. It is a launch draft intended for counsel review.",
  },
  {
    title: "Third-party services",
    body:
      "TradeReviewDesk may rely on hosting, authentication, payment, database, logging, and model providers to deliver the product. Those providers may process limited information as part of their infrastructure roles, subject to their own terms and privacy practices.",
  },
  {
    title: "Retention and deletion",
    body:
      "Workflow records may remain stored until they are deleted by the user, removed during testing, or purged under future retention rules. If you need data removed during MVP operation, deletion tools inside the app may not cover every record yet.",
  },
];

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-20 text-slate-300">
      <div className="space-y-4">
        <p className="text-sm uppercase tracking-[0.24em] text-cyan-300">Privacy</p>
        <h1 className="text-5xl font-semibold text-white">TradeReviewDesk Privacy Overview</h1>
        <p className="text-lg text-slate-300">
          This page explains the MVP privacy posture at a high level and is intended to be refined with legal review before broader release.
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
        Related documents: <Link href="/legal/terms" className="text-cyan-300">Terms</Link> and{" "}
        <Link href="/legal/disclaimer" className="text-cyan-300">Disclaimer</Link>.
      </p>
    </main>
  );
}
