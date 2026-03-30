import { AppShell } from "@/components/app-shell";
import { DiagnosticsWorkspace } from "@/components/diagnostics-workspace";
import { getReportJobs, getSubscription } from "@/lib/api";

export default async function DiagnosticsPage() {
  const [reportJobs, subscription] = await Promise.all([getReportJobs(), getSubscription()]);

  return (
    <AppShell
      title="Diagnostics"
      description="Inspect report-job status, token usage, and estimated model cost while the MVP is still under active supervision."
    >
      <DiagnosticsWorkspace reportJobs={reportJobs} subscription={subscription} />
    </AppShell>
  );
}
