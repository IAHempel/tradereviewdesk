import { getChecklistRuns, getChecklistTemplates, getSubscription } from "@/lib/api";
import { AppShell } from "@/components/app-shell";
import { ChecklistsWorkspace } from "@/components/checklists-workspace";

export default async function ChecklistsPage() {
  const [templates, runs, subscription] = await Promise.all([getChecklistTemplates(), getChecklistRuns(), getSubscription()]);

  return (
    <AppShell
      title="Checklists"
      description="Template-driven trade preparation built to reduce impulsive entries and improve consistency."
    >
      <ChecklistsWorkspace templates={templates} runs={runs} currentPlan={subscription?.plan ?? "free"} />
    </AppShell>
  );
}
