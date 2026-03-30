import Link from "next/link";

import { complianceCopy } from "@tradenoc/config";

export function SiteFooter() {
  return (
    <footer className="border-t border-white/10 bg-slate-950/70">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-8 text-sm text-slate-400 md:flex-row md:items-center md:justify-between">
        <p className="max-w-2xl">{complianceCopy.short}</p>
        <div className="flex gap-4">
          <Link href="/legal/disclaimer">Disclaimer</Link>
          <Link href="/legal/privacy">Privacy</Link>
          <Link href="/legal/terms">Terms</Link>
        </div>
      </div>
    </footer>
  );
}
