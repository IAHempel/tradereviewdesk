import { AppShell } from "@/components/app-shell";
import { LoadingShell } from "@/components/state-panels";

export default function AppLoading() {
  return (
    <AppShell
      title="Loading"
      description="TradeReviewDesk is pulling together your latest workflow state."
    >
      <LoadingShell />
    </AppShell>
  );
}
