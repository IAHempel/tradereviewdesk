import type { ReactNode } from "react";

export function MarketingSection({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`mx-auto max-w-7xl px-6 py-16 sm:py-24 ${className}`}>{children}</section>;
}
