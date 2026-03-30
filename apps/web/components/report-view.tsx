import { Card } from "@tradenoc/ui";
import type { ReportJobRecord, ReportRecord } from "@tradenoc/types";

import { asStringList } from "@/lib/reports";
import { StatePanel } from "@/components/state-panels";

function ReportFallback({
  title,
  emptyMessage,
  latestJob,
}: {
  title: string;
  emptyMessage: string;
  latestJob: ReportJobRecord | null;
}) {
  const statusText = latestJob
    ? latestJob.status === "failed"
      ? latestJob.error_message ?? "The latest report job failed validation."
      : `Latest job is ${latestJob.status}.`
    : emptyMessage;

  return (
    <Card>
      <h2 className="text-lg font-medium text-white">{title}</h2>
      <div className="mt-3">
        <StatePanel
          title={latestJob?.status === "failed" ? "Generation failed" : "Nothing generated yet"}
          message={statusText}
          tone={latestJob?.status === "failed" ? "danger" : latestJob?.status === "processing" ? "warning" : "default"}
        />
      </div>
    </Card>
  );
}

export function PremarketReportView({
  report,
  latestJob,
}: {
  report: ReportRecord | null;
  latestJob: ReportJobRecord | null;
}) {
  if (!report) {
    return (
      <ReportFallback
        title="Latest brief"
        emptyMessage="No premarket brief has been generated yet."
        latestJob={latestJob}
      />
    );
  }

  const priorities = Array.isArray(report.parsed_output.watchlist_priorities)
    ? report.parsed_output.watchlist_priorities
    : [];

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-medium text-white">{report.title}</h2>
          <p className="mt-2 text-sm text-slate-400">Generated for {report.report_date}</p>
        </div>
        <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-emerald-200">
          {report.status}
        </span>
      </div>
      <p className="mt-4 text-sm text-slate-200">{String(report.parsed_output.summary ?? "No summary available.")}</p>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="text-sm uppercase tracking-[0.18em] text-cyan-300">Watchlist priorities</h3>
          {priorities.length === 0 ? (
            <div className="mt-3">
              <StatePanel
                title="No watchlist priorities returned"
                message="Generate another brief after refining your watchlist or adding a bit more manual context."
              />
            </div>
          ) : (
            <ul className="mt-3 space-y-3 text-sm text-slate-300">
              {priorities.map((item, index) => {
                const priority = typeof item === "object" && item !== null ? (item as Record<string, unknown>) : {};
                return (
                  <li key={`${String(priority.symbol ?? "symbol")}-${index}`} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                    <p className="font-medium text-white">
                      {String(priority.symbol ?? "Unknown")} | {String(priority.priority ?? "n/a")}
                    </p>
                    <p className="mt-1 text-slate-400">{String(priority.reason ?? "No reason available.")}</p>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        <div>
          <h3 className="text-sm uppercase tracking-[0.18em] text-cyan-300">Focus reminders</h3>
          {asStringList(report.parsed_output.focus_reminders).length === 0 ? (
            <div className="mt-3">
              <StatePanel
                title="No reminders returned"
                message="This brief did not include focus reminders. Re-run after adding a few priorities or manual events."
              />
            </div>
          ) : (
            <ul className="mt-3 space-y-3 text-sm text-slate-300">
              {asStringList(report.parsed_output.focus_reminders).map((item) => (
                <li key={item} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <p className="mt-6 text-sm text-slate-400">{report.disclaimer}</p>
    </Card>
  );
}

export function DebriefReportView({
  report,
  latestJob,
}: {
  report: ReportRecord | null;
  latestJob: ReportJobRecord | null;
}) {
  if (!report) {
    return (
      <ReportFallback
        title="Latest debrief"
        emptyMessage="No post-close debrief has been generated yet."
        latestJob={latestJob}
      />
    );
  }

  const strengths = asStringList(report.parsed_output.what_went_well);
  const improvements = asStringList(report.parsed_output.next_day_improvements);

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-medium text-white">{report.title}</h2>
          <p className="mt-2 text-sm text-slate-400">Generated for {report.report_date}</p>
        </div>
        <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-emerald-200">
          {report.status}
        </span>
      </div>
      <p className="mt-4 text-sm text-slate-200">
        {String(report.parsed_output.session_summary ?? "No session summary available.")}
      </p>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="text-sm uppercase tracking-[0.18em] text-cyan-300">What went well</h3>
          {strengths.length === 0 ? (
            <div className="mt-3">
              <StatePanel title="No strengths captured" message="The report did not return strengths this time. Add more session detail and try again." />
            </div>
          ) : (
            <ul className="mt-3 space-y-3 text-sm text-slate-300">
              {strengths.map((item) => (
                <li key={item} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3 className="text-sm uppercase tracking-[0.18em] text-cyan-300">Next-day improvements</h3>
          {improvements.length === 0 ? (
            <div className="mt-3">
              <StatePanel title="No improvements captured" message="The report did not return improvement items this time. Add more session detail and try again." />
            </div>
          ) : (
            <ul className="mt-3 space-y-3 text-sm text-slate-300">
              {improvements.map((item) => (
                <li key={item} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <p className="mt-6 text-sm text-slate-400">{report.disclaimer}</p>
    </Card>
  );
}

export function WeeklyReviewReportView({
  report,
  latestJob,
}: {
  report: ReportRecord | null;
  latestJob: ReportJobRecord | null;
}) {
  if (!report) {
    return (
      <ReportFallback
        title="Latest weekly review"
        emptyMessage="No weekly review has been generated yet."
        latestJob={latestJob}
      />
    );
  }

  const strengths = asStringList(report.parsed_output.top_strengths);
  const mistakes = asStringList(report.parsed_output.repeated_mistakes);
  const discipline = asStringList(report.parsed_output.discipline_observations);
  const actions = asStringList(report.parsed_output.next_week_action_items);

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-medium text-white">{report.title}</h2>
          <p className="mt-2 text-sm text-slate-400">Generated for week ending {report.report_date}</p>
        </div>
        <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-emerald-200">
          {report.status}
        </span>
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="text-sm uppercase tracking-[0.18em] text-cyan-300">Top strengths</h3>
          {strengths.length === 0 ? (
            <div className="mt-3">
              <StatePanel title="No strengths captured" message="The weekly review did not return strengths this time. Build a few more inputs and try again." />
            </div>
          ) : (
            <ul className="mt-3 space-y-3 text-sm text-slate-300">
              {strengths.map((item) => (
                <li key={item} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3 className="text-sm uppercase tracking-[0.18em] text-cyan-300">Repeated mistakes</h3>
          {mistakes.length === 0 ? (
            <div className="mt-3">
              <StatePanel title="No repeated mistakes captured" message="This weekly review did not find repeat mistakes. Add more debrief detail if that feels incomplete." />
            </div>
          ) : (
            <ul className="mt-3 space-y-3 text-sm text-slate-300">
              {mistakes.map((item) => (
                <li key={item} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3 className="text-sm uppercase tracking-[0.18em] text-cyan-300">Discipline observations</h3>
          {discipline.length === 0 ? (
            <div className="mt-3">
              <StatePanel title="No discipline observations captured" message="The model did not return discipline observations this time. Try another weekly generation after more journal input." />
            </div>
          ) : (
            <ul className="mt-3 space-y-3 text-sm text-slate-300">
              {discipline.map((item) => (
                <li key={item} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3 className="text-sm uppercase tracking-[0.18em] text-cyan-300">Next week action items</h3>
          {actions.length === 0 ? (
            <div className="mt-3">
              <StatePanel title="No action items captured" message="This review did not return action items. Re-run once the week has more trades, runs, or debriefs." />
            </div>
          ) : (
            <ul className="mt-3 space-y-3 text-sm text-slate-300">
              {actions.map((item) => (
                <li key={item} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <p className="mt-6 text-sm text-slate-400">{report.disclaimer}</p>
    </Card>
  );
}
