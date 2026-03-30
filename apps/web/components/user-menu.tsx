"use client";

import Link from "next/link";
import { useState } from "react";

import { SignOutButton } from "@clerk/nextjs";

export function UserMenu({
  identityLabel,
  authEnabled,
}: {
  identityLabel: string;
  authEnabled: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        onBlur={(event) => {
          if (!event.currentTarget.parentElement?.contains(event.relatedTarget as Node | null)) {
            setIsOpen(false);
          }
        }}
        className="inline-flex min-w-0 items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/10 px-4 py-2 text-sm text-cyan-50 transition hover:border-cyan-300/50"
      >
        <span className="max-w-[12rem] truncate">{identityLabel}</span>
        <span className="text-xs text-cyan-200">{isOpen ? "▲" : "▼"}</span>
      </button>
      {isOpen ? (
        <div className="absolute right-0 z-30 mt-3 w-56 rounded-2xl border border-white/10 bg-slate-950/95 p-2 shadow-[0_24px_80px_rgba(15,23,42,0.45)] backdrop-blur">
          <div className="border-b border-white/10 px-3 py-3">
            <p className="truncate text-sm font-medium text-white">{identityLabel}</p>
            <p className="mt-1 text-xs uppercase tracking-[0.18em] text-cyan-300">Signed in</p>
          </div>
          <div className="py-2">
            <Link
              href="/app/dashboard"
              onClick={() => setIsOpen(false)}
              className="block rounded-xl px-3 py-2 text-sm text-slate-200 transition hover:bg-white/5 hover:text-white"
            >
              Dashboard
            </Link>
            <Link
              href="/app/settings"
              onClick={() => setIsOpen(false)}
              className="mt-1 block rounded-xl px-3 py-2 text-sm text-slate-200 transition hover:bg-white/5 hover:text-white"
            >
              Settings
            </Link>
          </div>
          {authEnabled ? (
            <div className="border-t border-white/10 pt-2">
              <SignOutButton redirectUrl="/">
                <button
                  type="button"
                  className="block w-full rounded-xl px-3 py-2 text-left text-sm text-rose-100 transition hover:bg-rose-400/10 hover:text-rose-50"
                >
                  Sign out
                </button>
              </SignOutButton>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
