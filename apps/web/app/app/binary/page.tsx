import { getBinaryDefaults, getBinaryRun, getBinaryRuns } from "@/lib/api";
import { AppShell } from "@/components/app-shell";
import { BinaryWorkspace } from "@/components/binary-workspace";

export default async function BinaryDeskPage({ searchParams }: { searchParams: Promise<{ run?: string }> }) {
  const [{ run: requestedRunId }, defaults, runs] = await Promise.all([searchParams, getBinaryDefaults(), getBinaryRuns()]);
  const activeRunId = requestedRunId ?? runs[0]?.id;
  const activeRun = activeRunId ? await getBinaryRun(activeRunId) : null;

  return (
    <AppShell
      title="Binary Desk"
      description="A paper two-sided grid on 15-minute crypto Up/Down markets: bids on both sides so a filled pair costs under $1, shaded against inventory, resolved on real (or synthetic) prices. The market itself is modeled, and every run is checked against an efficient crowd."
    >
      <BinaryWorkspace defaults={defaults} runs={runs} initialRun={activeRun} />
    </AppShell>
  );
}
