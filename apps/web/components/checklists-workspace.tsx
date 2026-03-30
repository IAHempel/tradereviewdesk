"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Card } from "@tradenoc/ui";
import type { ChecklistRun, ChecklistTemplate, SubscriptionPlan } from "@tradenoc/types";

function joinTemplateItems(template: ChecklistTemplate | null) {
  return template ? template.items.map((item) => item.label).join("\n") : "";
}

function joinRunItems(run: ChecklistRun | null) {
  return run ? run.items.map((item) => item.label_snapshot).join("\n") : "";
}

export function ChecklistsWorkspace({
  templates,
  runs,
  currentPlan,
}: {
  templates: ChecklistTemplate[];
  runs: ChecklistRun[];
  currentPlan: SubscriptionPlan;
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [templateMessage, setTemplateMessage] = useState<string | null>(null);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null);
  const [editingRunId, setEditingRunId] = useState<string | null>(null);
  const isLocked = currentPlan === "free";

  const defaultTemplate = templates.find((template) => template.is_default) ?? templates[0] ?? null;
  const editingTemplate = templates.find((template) => template.id === editingTemplateId) ?? null;
  const editingRun = runs.find((run) => run.id === editingRunId) ?? null;

  async function handleTemplateSubmit(formData: FormData) {
    setTemplateMessage(null);

    const name = String(formData.get("name") ?? "").trim();
    const description = String(formData.get("description") ?? "").trim() || null;
    const rawItems = String(formData.get("items") ?? "");
    const items = rawItems
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean)
      .map((label, index) => ({
        id: editingTemplate?.items[index]?.id ?? `item-${Date.now()}-${index}`,
        label,
        description: null,
        is_required: true,
        display_order: index + 1,
      }));

    if (!name || items.length === 0) {
      setTemplateMessage("Add a template name and at least one checklist item.");
      return;
    }
    if (isLocked) {
      setTemplateMessage("Pro plan required to create checklist templates.");
      return;
    }

    startTransition(async () => {
      const response = await fetch(
        editingTemplate ? `/api/checklist-templates/${editingTemplate.id}` : "/api/checklist-templates",
        {
          method: editingTemplate ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            description,
            is_default: editingTemplate?.is_default ?? templates.length === 0,
            items,
          }),
        },
      );

      const data = (await response.json()) as { detail?: string; message?: string };
      if (!response.ok) {
        setTemplateMessage(data.detail ?? data.message ?? "Unable to save checklist template.");
        return;
      }

      setTemplateMessage(editingTemplate ? `Template "${name}" updated.` : `Template "${name}" created.`);
      setEditingTemplateId(null);
      router.refresh();
    });
  }

  async function handleRunSubmit(formData: FormData) {
    setRunMessage(null);

    const activeTemplate = editingRun ? null : defaultTemplate;
    if (!editingRun && !activeTemplate) {
      setRunMessage("Create a template before starting a checklist run.");
      return;
    }

    const symbol = String(formData.get("symbol") ?? "").trim().toUpperCase() || null;
    const setupTag = String(formData.get("setup_tag") ?? "").trim() || null;
    const reasonForEntry = String(formData.get("reason_for_entry") ?? "").trim();
    const confidenceScore = Number(String(formData.get("confidence_score") ?? ""));
    const rawItems = String(formData.get("items") ?? "");
    const items = rawItems
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean)
      .map((label) => ({
        label_snapshot: label,
        completed: true,
      }));

    if (!reasonForEntry) {
      setRunMessage("Add the reason for entry before saving a run.");
      return;
    }
    if (items.length === 0) {
      setRunMessage("Add at least one checklist item snapshot before saving the run.");
      return;
    }
    if (isLocked) {
      setRunMessage("Pro plan required to create checklist runs.");
      return;
    }

    startTransition(async () => {
      const response = await fetch(editingRun ? `/api/checklist-runs/${editingRun.id}` : "/api/checklist-runs", {
        method: editingRun ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_id: editingRun?.template_id ?? activeTemplate?.id ?? null,
          session_date: String(formData.get("session_date") ?? "").trim() || new Date().toISOString().slice(0, 10),
          symbol,
          setup_tag: setupTag,
          reason_for_entry: reasonForEntry,
          confidence_score: Number.isFinite(confidenceScore) && confidenceScore > 0 ? confidenceScore : null,
          items,
        }),
      });

      const data = (await response.json()) as { detail?: string; message?: string };
      if (!response.ok) {
        setRunMessage(data.detail ?? data.message ?? "Unable to save checklist run.");
        return;
      }

      setRunMessage(editingRun ? "Checklist run updated." : `Checklist run saved${symbol ? ` for ${symbol}` : ""}.`);
      setEditingRunId(null);
      router.refresh();
    });
  }

  async function handleTemplateDelete(templateId: string, templateName: string) {
    if (!window.confirm(`Delete the template "${templateName}"?`)) {
      return;
    }

    setTemplateMessage(null);
    startTransition(async () => {
      const response = await fetch(`/api/checklist-templates/${templateId}`, { method: "DELETE" });
      const data = (await response.json()) as { detail?: string; message?: string };
      if (!response.ok) {
        setTemplateMessage(data.detail ?? data.message ?? "Unable to delete checklist template.");
        return;
      }

      if (editingTemplateId === templateId) {
        setEditingTemplateId(null);
      }
      setTemplateMessage(`Template "${templateName}" deleted.`);
      router.refresh();
    });
  }

  async function handleRunDelete(runId: string, symbol: string | null) {
    if (!window.confirm(`Delete this checklist run${symbol ? ` for ${symbol}` : ""}?`)) {
      return;
    }

    setRunMessage(null);
    startTransition(async () => {
      const response = await fetch(`/api/checklist-runs/${runId}`, { method: "DELETE" });
      const data = (await response.json()) as { detail?: string; message?: string };
      if (!response.ok) {
        setRunMessage(data.detail ?? data.message ?? "Unable to delete checklist run.");
        return;
      }

      if (editingRunId === runId) {
        setEditingRunId(null);
      }
      setRunMessage(`Checklist run deleted${symbol ? ` for ${symbol}` : ""}.`);
      router.refresh();
    });
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-medium text-white">
              {editingTemplate ? "Edit checklist template" : "Create checklist template"}
            </h2>
            <p className="mt-2 text-sm text-slate-300">
              Build a repeatable pre-entry gate so execution follows a plan, not a mood.
            </p>
          </div>
          {editingTemplate ? (
            <button
              type="button"
              onClick={() => setEditingTemplateId(null)}
              className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-cyan-300/60"
            >
              Cancel edit
            </button>
          ) : null}
        </div>
        {isLocked ? (
          <p className="mt-3 text-sm text-cyan-300">
            Pro plan required for checklist workflows.{" "}
            <Link href="/app/settings" className="underline underline-offset-4">
              Upgrade in settings.
            </Link>
          </p>
        ) : null}
        <form key={editingTemplate?.id ?? "new-template"} action={handleTemplateSubmit} className="mt-6 grid gap-4">
          <label className="grid gap-2 text-sm text-slate-300">
            Template name
            <input
              name="name"
              defaultValue={editingTemplate?.name ?? ""}
              placeholder="Opening range momentum"
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            Description
            <input
              name="description"
              defaultValue={editingTemplate?.description ?? ""}
              placeholder="Guardrails before continuation entries"
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            Checklist items
            <textarea
              name="items"
              rows={6}
              defaultValue={joinTemplateItems(editingTemplate)}
              placeholder={"Catalyst is identified\nRisk and stop are defined\nPosition size matches plan"}
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
            />
          </label>
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-slate-400">{templateMessage ?? "Templates save through the backend checklist API."}</p>
            <button
              type="submit"
              disabled={isPending || isLocked}
              className="rounded-full bg-cyan-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-cyan-200 disabled:opacity-60"
            >
              {isPending ? "Saving..." : editingTemplate ? "Update template" : "Create template"}
            </button>
          </div>
        </form>
      </Card>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-medium text-white">{editingRun ? "Edit checklist run" : "Start checklist run"}</h2>
            <p className="mt-2 text-sm text-slate-300">
              Use the current template context to document the setup before taking action.
            </p>
          </div>
          {editingRun ? (
            <button
              type="button"
              onClick={() => setEditingRunId(null)}
              className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-emerald-300/60"
            >
              Cancel edit
            </button>
          ) : null}
        </div>
        {isLocked ? (
          <p className="mt-3 text-sm text-cyan-300">
            Pro plan required for checklist runs.{" "}
            <Link href="/app/settings" className="underline underline-offset-4">
              Upgrade in settings.
            </Link>
          </p>
        ) : null}
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-300">
          <p className="font-medium text-white">
            {editingRun ? "Editing saved run" : defaultTemplate?.name ?? "No template loaded"}
          </p>
          <p className="mt-2">
            {editingRun
              ? `${editingRun.items.length} checklist item${editingRun.items.length === 1 ? "" : "s"} currently saved.`
              : defaultTemplate
                ? `${defaultTemplate.items.length} checklist item${defaultTemplate.items.length === 1 ? "" : "s"} ready.`
                : "Create a template first."}
          </p>
        </div>
        <form key={editingRun?.id ?? "new-run"} action={handleRunSubmit} className="mt-6 grid gap-4">
          <label className="grid gap-2 text-sm text-slate-300">
            Session date
            <input
              name="session_date"
              type="date"
              defaultValue={editingRun?.session_date ?? new Date().toISOString().slice(0, 10)}
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-emerald-300/60"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            Symbol
            <input
              name="symbol"
              defaultValue={editingRun?.symbol ?? ""}
              placeholder="NVDA"
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-emerald-300/60"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            Setup tag
            <input
              name="setup_tag"
              defaultValue={editingRun?.setup_tag ?? ""}
              placeholder="momentum"
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-emerald-300/60"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            Reason for entry
            <textarea
              name="reason_for_entry"
              rows={4}
              defaultValue={editingRun?.reason_for_entry ?? ""}
              placeholder="High relative volume, clear reclaim, defined invalidation."
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-emerald-300/60"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            Checklist item snapshot
            <textarea
              name="items"
              rows={5}
              defaultValue={editingRun ? joinRunItems(editingRun) : joinTemplateItems(defaultTemplate)}
              placeholder={"Catalyst is identified\nRisk and stop are defined\nPosition size matches plan"}
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-emerald-300/60"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            Confidence score (1-5)
            <input
              name="confidence_score"
              type="number"
              min="1"
              max="5"
              defaultValue={editingRun?.confidence_score ?? ""}
              placeholder="4"
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-emerald-300/60"
            />
          </label>
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-slate-400">{runMessage ?? "Runs save through the backend checklist API."}</p>
            <button
              type="submit"
              disabled={isPending || (!editingRun && !defaultTemplate) || isLocked}
              className="rounded-full bg-emerald-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-emerald-200 disabled:opacity-60"
            >
              {isPending ? "Saving..." : editingRun ? "Update run" : "Start run"}
            </button>
          </div>
        </form>
      </Card>

      <Card>
        <h2 className="text-lg font-medium text-white">Saved templates</h2>
        <ul className="mt-4 space-y-3 text-sm text-slate-300">
          {templates.length > 0 ? (
            templates.map((template) => (
              <li key={template.id} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="font-medium text-white">{template.name}</p>
                    <p className="mt-1 text-slate-400">{template.description ?? "No description."}</p>
                    <p className="mt-2 text-slate-400">{template.items.map((item) => item.label).join(" | ")}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setEditingTemplateId(template.id)}
                      className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-cyan-300/60"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => handleTemplateDelete(template.id, template.name)}
                      className="rounded-full border border-rose-400/30 px-4 py-2 text-sm font-medium text-rose-100 transition hover:border-rose-300/60"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            ))
          ) : (
            <li className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4">No templates saved yet.</li>
          )}
        </ul>
      </Card>

      <Card>
        <h2 className="text-lg font-medium text-white">Recent runs</h2>
        <ul className="mt-4 space-y-3 text-sm text-slate-300">
          {runs.length > 0 ? (
            runs.map((run) => (
              <li key={run.id} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="font-medium text-white">
                      {run.symbol ?? "No symbol"} | {run.setup_tag ?? "No setup tag"}
                    </p>
                    <p className="mt-1 text-slate-400">{run.reason_for_entry}</p>
                    <p className="mt-2 text-slate-400">
                      Confidence {run.confidence_score ?? "n/a"} | {run.items.filter((item) => item.completed).length}/{run.items.length} items completed
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setEditingRunId(run.id)}
                      className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-emerald-300/60"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRunDelete(run.id, run.symbol)}
                      className="rounded-full border border-rose-400/30 px-4 py-2 text-sm font-medium text-rose-100 transition hover:border-rose-300/60"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            ))
          ) : (
            <li className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4">No checklist runs saved yet.</li>
          )}
        </ul>
      </Card>
    </div>
  );
}
