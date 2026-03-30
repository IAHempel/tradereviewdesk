import type { ReactNode } from "react";

import { redirect } from "next/navigation";

import { getServerUserContext, isClerkAuthEnabled } from "@/lib/auth";

export default async function AppLayout({ children }: { children: ReactNode }) {
  if (isClerkAuthEnabled()) {
    const userContext = await getServerUserContext();

    if (!userContext) {
      redirect("/login");
    }
  }

  return children;
}
