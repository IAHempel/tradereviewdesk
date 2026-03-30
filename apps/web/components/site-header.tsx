import Link from "next/link";

import { getServerUserContext, isClerkAuthEnabled } from "@/lib/auth";

const primaryNav = [
  { href: "/how-it-works", label: "How it works" },
  { href: "/pricing", label: "Pricing" },
];

export async function SiteHeader() {
  const userContext = await getServerUserContext();
  const authEnabled = isClerkAuthEnabled();
  const identityLabel = userContext?.displayName?.trim() || userContext?.email || null;

  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/70 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-[0.16em] text-white">
          TradeReviewDesk
        </Link>
        <div className="flex items-center gap-4">
          <nav className="hidden items-center gap-6 md:flex">
            {primaryNav.map((item) => (
              <Link key={item.href} href={item.href} className="text-sm text-slate-300 transition hover:text-white">
                {item.label}
              </Link>
            ))}
          </nav>
          {userContext && identityLabel ? (
            <div className="flex items-center gap-3">
              <Link
                href="/app/dashboard"
                className="hidden rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-cyan-300/60 sm:inline-flex"
              >
                Dashboard
              </Link>
              <Link
                href="/app/settings"
                className="inline-flex min-w-0 items-center rounded-full border border-cyan-300/20 bg-cyan-300/10 px-4 py-2 text-sm text-cyan-50 transition hover:border-cyan-300/50"
              >
                <span className="truncate">{identityLabel}</span>
              </Link>
            </div>
          ) : authEnabled ? (
            <div className="flex items-center gap-3">
              <Link
                href="/login"
                className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/5"
              >
                Login
              </Link>
              <Link
                href="/signup"
                className="rounded-full bg-cyan-300 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-200"
              >
                Start free
              </Link>
            </div>
          ) : (
            <Link
              href="/signup"
              className="rounded-full bg-cyan-300 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-200"
            >
              Start free
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
