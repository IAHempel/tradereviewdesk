import { getDeskDefaults, getDeskRun, getDeskRuns } from "@/lib/api";
import { AppShell } from "@/components/app-shell";
import { DeskWorkspace } from "@/components/desk-workspace";

export default async function DeskPage({ searchParams }: { searchParams: Promise<{ run?: string }> }) {
  const [{ run: requestedRunId }, defaults, runs] = await Promise.all([searchParams, getDeskDefaults(), getDeskRuns()]);
  const activeRunId = requestedRunId ?? runs[0]?.id;
  const activeRun = activeRunId ? await getDeskRun(activeRunId) : null;

  return (
    <AppShell
      title="Agent Desk"
      description="Six agents run your rules bar by bar on a synthetic tape with paper fills: scout, filter, score, size, execute, and log a reason for every decision."
    >
      <DeskWorkspace defaults={defaults} runs={runs} initialRun={activeRun} />
    </AppShell>
  );
}
