import { getProfile, getSubscription, getWatchlists } from "@/lib/api";
import { getServerUserContext, isClerkAuthEnabled } from "@/lib/auth";
import { AppShell } from "@/components/app-shell";
import { SettingsWorkspace } from "@/components/settings-workspace";

export default async function SettingsPage() {
  const [profile, watchlists, subscription, userContext] = await Promise.all([
    getProfile(),
    getWatchlists(),
    getSubscription(),
    getServerUserContext(),
  ]);

  return (
    <AppShell
      title="Settings"
      description="Configure profile, watchlists, checklist defaults, and billing preferences."
    >
      <SettingsWorkspace
        profile={profile}
        watchlists={watchlists}
        subscription={subscription}
        authEnabled={isClerkAuthEnabled()}
        isAuthenticated={Boolean(userContext)}
      />
    </AppShell>
  );
}
