import type { ReportJobRecord, ReportRecord, ReportType } from "@tradenoc/types";

export function getLatestReportByType(reports: ReportRecord[], reportType: ReportType): ReportRecord | null {
  return reports
    .filter((report) => report.report_type === reportType)
    .sort((left, right) => right.report_date.localeCompare(left.report_date))[0] ?? null;
}

export function getLatestReportJobByType(reportJobs: ReportJobRecord[], reportType: ReportType): ReportJobRecord | null {
  return reportJobs.find((job) => job.report_type === reportType) ?? null;
}

export function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string");
}

export function getCurrentWeekRange() {
  const now = new Date();
  const day = now.getDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const weekStart = new Date(now);
  weekStart.setDate(now.getDate() + diffToMonday);
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekStart.getDate() + 4);

  return {
    weekStart: weekStart.toISOString().slice(0, 10),
    weekEnd: weekEnd.toISOString().slice(0, 10),
  };
}
