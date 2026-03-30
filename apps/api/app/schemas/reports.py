from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


ReportType = Literal["premarket", "debrief", "weekly_review"]
ReportJobStatus = Literal["queued", "processing", "succeeded", "failed"]


class PremarketGenerateRequest(BaseModel):
    report_date: str
    user_profile: dict[str, Any]
    watchlist_symbols: list[str]
    prior_notes: list[str] = []
    manual_events: list[str] = []
    user_priorities: list[str] = []


class DebriefGenerateRequest(BaseModel):
    report_date: str
    user_profile: dict[str, Any]
    trade_entries: list[dict[str, Any]]
    checklist_runs: list[dict[str, Any]]
    user_notes: list[str] = []


class WeeklyReviewGenerateRequest(BaseModel):
    week_start: str
    week_end: str
    user_profile: dict[str, Any]
    debrief_summaries: list[str]
    trade_entries: list[dict[str, Any]]
    checklist_run_summaries: list[str]


class PremarketOutput(BaseModel):
    summary: str
    watchlist_priorities: list[dict[str, str]]
    changes_to_watch: list[str]
    focus_reminders: list[str]
    session_checklist: list[str]
    disclaimer: str


class DebriefOutput(BaseModel):
    session_summary: str
    what_went_well: list[str]
    deviations_from_plan: list[str]
    risk_behavior_notes: list[str]
    next_day_improvements: list[str]
    disclaimer: str


class WeeklyReviewOutput(BaseModel):
    top_strengths: list[str]
    repeated_mistakes: list[str]
    setup_observations: list[str]
    discipline_observations: list[str]
    next_week_action_items: list[str]
    disclaimer: str


class ReportResponse(BaseModel):
    id: str
    report_type: ReportType
    title: str
    report_date: str
    status: str
    input_summary: dict[str, Any]
    parsed_output: dict[str, Any]
    disclaimer: str
    report_job_id: str | None = None


class ReportUsageMetrics(BaseModel):
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class ReportJobResponse(BaseModel):
    id: str
    report_type: ReportType
    status: ReportJobStatus
    attempts: int
    input_payload: dict[str, Any]
    error_message: str | None = None
    raw_model_output: str | None = None
    parsed_output: dict[str, Any] | None = None
    usage_metrics: ReportUsageMetrics | None = None
    report_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReportGenerationResponse(BaseModel):
    job: ReportJobResponse
    report: ReportResponse | None = None
