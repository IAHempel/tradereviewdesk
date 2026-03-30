import type { ReactNode } from "react";

import { ClerkProvider } from "@clerk/nextjs";

import { isClerkAuthEnabled } from "@/lib/auth";

export function AuthProvider({ children }: { children: ReactNode }) {
  if (!isClerkAuthEnabled()) {
    return children;
  }

  return <ClerkProvider>{children}</ClerkProvider>;
}
