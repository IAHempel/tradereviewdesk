import type { ReactNode } from "react";
import Link from "next/link";

import { appNav } from "@tradenoc/config";

export function AppShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-950">
      <div className="mx-auto grid min-h-screen max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[240px_1fr]">
        <aside className="rounded-3xl border border-white/10 bg-slate-950/80 p-5">
          <Link href="/" className="block text-lg font-semibold tracking-[0.18em] text-white">
            TradeReviewDesk
          </Link>
          <p className="mt-3 text-sm text-slate-400">Your personal trading ops center.</p>
          <nav className="mt-8 space-y-2">
            {appNav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block rounded-2xl px-4 py-3 text-sm text-slate-300 transition hover:bg-white/5 hover:text-white"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>
        <main className="rounded-3xl border border-white/10 bg-slate-950/60 p-6 backdrop-blur">
          <div className="mb-8 space-y-2">
            <p className="text-sm uppercase tracking-[0.22em] text-cyan-300">Command center</p>
            <h1 className="text-3xl font-semibold text-white">{title}</h1>
            <p className="max-w-3xl text-slate-300">{description}</p>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
