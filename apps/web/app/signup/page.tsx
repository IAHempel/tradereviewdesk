import { SignUp } from "@clerk/nextjs";
import Link from "next/link";
import { redirect } from "next/navigation";

import { Card } from "@tradenoc/ui";

import { MarketingSection } from "@/components/marketing-section";
import { getServerUserContext, isClerkAuthEnabled } from "@/lib/auth";

export default async function SignupPage() {
  const userContext = await getServerUserContext();
  const appEnv = process.env.APP_ENV ?? process.env.NODE_ENV ?? "development";
  const authMisconfigured = appEnv === "production" && !isClerkAuthEnabled();

  if (isClerkAuthEnabled() && userContext) {
    redirect("/app/dashboard");
  }

  return (
    <main>
      <MarketingSection className="flex justify-center">
        <Card className="w-full max-w-xl">
          <h1 className="text-3xl font-semibold text-white">Start free</h1>
          <p className="mt-3 text-slate-300">
            {authMisconfigured
              ? "Authentication is not configured correctly for this production environment yet."
              : isClerkAuthEnabled()
              ? "Create your TradeReviewDesk account, then move directly into onboarding, watchlists, and report workflows."
              : "Set AUTH_MODE=clerk and add your Clerk keys to enable production signup in this environment."}
          </p>
          {isClerkAuthEnabled() ? (
            <div className="mt-8 overflow-hidden rounded-3xl border border-white/10 bg-slate-900/70 p-2">
              <SignUp
                path="/signup"
                routing="path"
                signInUrl="/login"
                forceRedirectUrl="/app/dashboard"
                fallbackRedirectUrl="/app/dashboard"
              />
            </div>
          ) : (
            <div className="mt-8 rounded-2xl border border-amber-500/20 bg-amber-500/10 px-4 py-4 text-sm text-amber-100">
              Production signup is fail-closed. Enable Clerk before exposing this route publicly.
            </div>
          )}
          <p className="mt-6 text-sm text-slate-400">
            Already have an account? <Link href="/login" className="text-cyan-300">Login</Link>
          </p>
        </Card>
      </MarketingSection>
    </main>
  );
}
