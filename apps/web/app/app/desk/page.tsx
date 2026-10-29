import { getDeskDefaults, getDeskRun, getDeskRuns, getDeskSources } from "@/lib/api";
import { AppShell } from "@/components/app-shell";
import { DeskWorkspace } from "@/components/desk-workspace";

export default async function DeskPage({ searchParams }: { searchParams: Promise<{ run?: string }> }) {
  const [{ run: requestedRunId }, defaults, runs, sources] = await Promise.all([
    searchParams,
    getDeskDefaults(),
    getDeskRuns(),
    getDeskSources(),
  ]);
  const activeRunId = requestedRunId ?? runs[0]?.id;
  const activeRun = activeRunId ? await getDeskRun(activeRunId) : null;

  return (
    <AppShell
      title="Agent Desk"
      description="Six agents run your rules bar by bar with paper fills, on a synthetic tape or real historical bars: scout, filter, score, size, execute, and log a reason for every decision."
    >
      <DeskWorkspace defaults={defaults} runs={runs} sources={sources} initialRun={activeRun} />
    </AppShell>
  );
}
