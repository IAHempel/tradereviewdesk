import { SignIn } from "@clerk/nextjs";
import Link from "next/link";
import { redirect } from "next/navigation";

import { Card } from "@tradenoc/ui";

import { MarketingSection } from "@/components/marketing-section";
import { getServerUserContext, isClerkAuthEnabled } from "@/lib/auth";

export default async function LoginPage() {
  const userContext = await getServerUserContext();
  const appEnv = process.env.APP_ENV ?? process.env.NODE_ENV ?? "development";
  const authMisconfigured = appEnv === "production" && !isClerkAuthEnabled();

  if (isClerkAuthEnabled() && userContext) {
    redirect("/app/dashboard");
  }

  return (
    <main>
      <MarketingSection className="flex justify-center">
        <Card className="w-full max-w-md">
          <h1 className="text-3xl font-semibold text-white">Login</h1>
          <p className="mt-3 text-slate-300">
            {authMisconfigured
              ? "Authentication is not configured correctly for this production environment yet."
              : isClerkAuthEnabled()
              ? "Access your TradeReviewDesk workspace with your authenticated account."
              : "Set AUTH_MODE=clerk and add your Clerk keys to enable production auth in this environment."}
          </p>
          {isClerkAuthEnabled() ? (
            <div className="mt-8 overflow-hidden rounded-3xl border border-white/10 bg-slate-900/70 p-2">
              <SignIn
                path="/login"
                routing="path"
                signUpUrl="/signup"
                forceRedirectUrl="/app/dashboard"
                fallbackRedirectUrl="/app/dashboard"
              />
            </div>
          ) : (
            <div className="mt-8 rounded-2xl border border-amber-500/20 bg-amber-500/10 px-4 py-4 text-sm text-amber-100">
              Production auth is fail-closed. Enable Clerk before exposing this route publicly.
            </div>
          )}
          <p className="mt-6 text-sm text-slate-400">
            Need an account? <Link href="/signup" className="text-cyan-300">Start free</Link>
          </p>
        </Card>
      </MarketingSection>
    </main>
  );
}
