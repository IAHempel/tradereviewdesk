const sections = [
  {
    title: "No investment advice",
    body:
      "TradeReviewDesk does not provide investment advice, research ratings, security recommendations, suitability determinations, market predictions, price targets, or personalized trading instructions.",
  },
  {
    title: "No execution or brokerage",
    body:
      "TradeReviewDesk does not place orders, route trades, custody funds, clear transactions, or act as a broker, exchange, or trading venue. Your brokerage account and trading platform remain separate from this product.",
  },
  {
    title: "Generated content limits",
    body:
      "Reports, summaries, reminders, and workflow prompts are generated from the data you provide and may be incomplete, incorrect, or poorly phrased. They should be treated as journaling and process-support artifacts only.",
  },
  {
    title: "Educational and operational framing",
    body:
      "TradeReviewDesk is intended to support planning discipline, review quality, and behavioral consistency for self-directed traders. Any reference to symbols, setups, or session context is operational framing, not a recommendation to transact.",
  },
];

export default function DisclaimerPage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-20 text-slate-300">
      <div className="space-y-4">
        <p className="text-sm uppercase tracking-[0.24em] text-cyan-300">Disclaimer</p>
        <h1 className="text-5xl font-semibold text-white">TradeReviewDesk Product Disclaimer</h1>
        <p className="text-lg text-slate-300">
          The core rule for this MVP is simple: TradeReviewDesk supports workflow and review, not investment advice or trade execution.
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
    </main>
  );
}
