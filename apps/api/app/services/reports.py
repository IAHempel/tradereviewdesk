from collections.abc import Sequence
import json

from fastapi import HTTPException
from pydantic import ValidationError

from app.core.auth import CurrentUser
from app.core.persistence import require_database_result, use_file_persistence
from app.schemas.reports import (
    DebriefGenerateRequest,
    DebriefOutput,
    PremarketGenerateRequest,
    PremarketOutput,
    ReportGenerationResponse,
    ReportJobResponse,
    ReportResponse,
    ReportType,
    WeeklyReviewGenerateRequest,
    WeeklyReviewOutput,
)
from app.services import report_repository, state_store
from app.services.report_generation_provider import LLMProviderError, report_generation_provider


class ReportService:
    def _build_report_response(
        self,
        *,
        report_type: ReportType,
        report_date: str,
        input_summary: dict,
        parsed_output: dict,
        disclaimer: str,
        report_job_id: str | None,
        report_id: str,
    ) -> ReportResponse:
        title = {
            "premarket": "Daily Premarket Brief",
            "debrief": "Post-Close Debrief",
            "weekly_review": "Weekly Review",
        }[report_type]
        return ReportResponse(
            id=report_id,
            report_type=report_type,
            title=title,
            report_date=report_date,
            status="succeeded",
            input_summary=input_summary,
            parsed_output=parsed_output,
            disclaimer=disclaimer,
            report_job_id=report_job_id,
        )

    def _build_input_summary(self, report_type: ReportType, payload: dict) -> dict:
        if report_type == "premarket":
            return {
                "watchlist_count": len(payload.get("watchlist_symbols", [])),
                "manual_events": payload.get("manual_events", []),
            }
        if report_type == "debrief":
            return {
                "trade_count": len(payload.get("trade_entries", [])),
                "checklist_runs": len(payload.get("checklist_runs", [])),
            }
        return {
            "week_start": payload.get("week_start"),
            "week_end": payload.get("week_end"),
        }

    def _validate_output(self, report_type: ReportType, raw_model_output: str) -> dict:
        parsed_json = json.loads(raw_model_output)
        if report_type == "premarket":
            return PremarketOutput.model_validate(parsed_json).model_dump()
        if report_type == "debrief":
            return DebriefOutput.model_validate(parsed_json).model_dump()
        return WeeklyReviewOutput.model_validate(parsed_json).model_dump()

    def _synthetic_job(
        self,
        *,
        report_type: ReportType,
        input_payload: dict,
        status: str,
        attempts: int,
        error_message: str | None = None,
        raw_model_output: str | None = None,
        parsed_output: dict | None = None,
        usage_metrics: dict | None = None,
        report_id: str | None = None,
    ) -> ReportJobResponse:
        return ReportJobResponse(
            id=f"job-{report_type}-{attempts}",
            report_type=report_type,
            status=status,
            attempts=attempts,
            input_payload=input_payload,
            error_message=error_message,
            raw_model_output=raw_model_output,
            parsed_output=parsed_output,
            usage_metrics=usage_metrics,
            report_id=report_id,
        )

    def _persist_file_report(self, report: ReportResponse, current_user: CurrentUser) -> ReportResponse:
        reports = state_store.list_reports(current_user)
        reports.append(report)
        state_store.save_reports(reports, current_user)
        return report

    def _run_job(
        self,
        *,
        report_type: ReportType,
        input_payload: dict,
        report_date: str,
        current_user: CurrentUser,
    ) -> ReportGenerationResponse:
        input_summary = self._build_input_summary(report_type, input_payload)
        file_reports = state_store.list_reports(current_user) if use_file_persistence() else []
        report_job = (
            self._synthetic_job(report_type=report_type, input_payload=input_payload, status="queued", attempts=0)
            if use_file_persistence()
            else require_database_result(
                report_repository.create_report_job(current_user, report_type, input_payload),
                "Report job",
            )
        )

        latest_validation_error: str | None = None
        for attempt in (1, 2):
            if use_file_persistence():
                report_job = self._synthetic_job(
                    report_type=report_type,
                    input_payload=input_payload,
                    status="processing",
                    attempts=attempt,
                )
            else:
                report_job = require_database_result(
                    report_repository.update_report_job(
                        report_job.id,
                        current_user,
                        status="processing",
                        attempts=attempt,
                        error_message=None,
                    ),
                    "Report job",
                )

            try:
                generation_result = report_generation_provider.generate(
                    report_type,
                    input_payload,
                    attempt=attempt,
                    validation_error=latest_validation_error,
                )
            except LLMProviderError as exc:
                failed_job = (
                    self._synthetic_job(
                        report_type=report_type,
                        input_payload=input_payload,
                        status="failed",
                        attempts=attempt,
                        error_message=str(exc),
                        usage_metrics=None,
                    )
                    if use_file_persistence()
                    else require_database_result(
                        report_repository.update_report_job(
                            report_job.id,
                            current_user,
                            status="failed",
                            attempts=attempt,
                            error_message=str(exc),
                            raw_model_output=None,
                            parsed_output=None,
                        ),
                        "Report job",
                    )
                )
                return ReportGenerationResponse(job=failed_job, report=None)

            raw_model_output = generation_result.raw_output
            usage_metrics = generation_result.usage_metrics

            try:
                parsed_output = self._validate_output(report_type, raw_model_output)
            except (json.JSONDecodeError, ValidationError) as exc:
                latest_validation_error = str(exc)
                if attempt == 2:
                    failed_job = (
                        self._synthetic_job(
                            report_type=report_type,
                            input_payload=input_payload,
                            status="failed",
                            attempts=attempt,
                            error_message=latest_validation_error,
                            raw_model_output=raw_model_output,
                            usage_metrics=usage_metrics,
                        )
                        if use_file_persistence()
                        else require_database_result(
                            report_repository.update_report_job(
                            report_job.id,
                            current_user,
                            status="failed",
                            attempts=attempt,
                            error_message=latest_validation_error,
                            raw_model_output=raw_model_output,
                            parsed_output=None,
                            usage_metrics=usage_metrics,
                        ),
                        "Report job",
                    )
                    )
                    return ReportGenerationResponse(job=failed_job, report=None)
                continue

            disclaimer = str(parsed_output.get("disclaimer") or "Workflow support only.")
            report_response = self._build_report_response(
                report_type=report_type,
                report_date=report_date,
                input_summary=input_summary,
                parsed_output=parsed_output,
                disclaimer=disclaimer,
                report_job_id=None if use_file_persistence() else report_job.id,
                report_id=(f"report-{len(file_reports) + 1}" if use_file_persistence() else "pending"),
            )

            if use_file_persistence():
                saved_report = self._persist_file_report(report_response, current_user)
                succeeded_job = self._synthetic_job(
                    report_type=report_type,
                    input_payload=input_payload,
                    status="succeeded",
                    attempts=attempt,
                    raw_model_output=raw_model_output,
                    parsed_output=parsed_output,
                    usage_metrics=usage_metrics,
                    report_id=saved_report.id,
                )
            else:
                saved_report = require_database_result(
                    report_repository.save_report(
                        report_response,
                        current_user,
                        report_job_id=report_job.id,
                        raw_model_output=raw_model_output,
                    ),
                    "Report",
                )
                succeeded_job = require_database_result(
                    report_repository.update_report_job(
                        report_job.id,
                        current_user,
                        status="succeeded",
                        attempts=attempt,
                        error_message=None,
                        raw_model_output=raw_model_output,
                        parsed_output=parsed_output,
                        usage_metrics=usage_metrics,
                    ),
                    "Report job",
                )

            return ReportGenerationResponse(job=succeeded_job, report=saved_report)

        raise HTTPException(status_code=500, detail="Report job exited unexpectedly.")

    def generate_premarket(self, payload: PremarketGenerateRequest, current_user: CurrentUser) -> ReportGenerationResponse:
        return self._run_job(
            report_type="premarket",
            input_payload=payload.model_dump(),
            report_date=payload.report_date,
            current_user=current_user,
        )

    def generate_debrief(self, payload: DebriefGenerateRequest, current_user: CurrentUser) -> ReportGenerationResponse:
        return self._run_job(
            report_type="debrief",
            input_payload=payload.model_dump(),
            report_date=payload.report_date,
            current_user=current_user,
        )

    def generate_weekly_review(self, payload: WeeklyReviewGenerateRequest, current_user: CurrentUser) -> ReportGenerationResponse:
        return self._run_job(
            report_type="weekly_review",
            input_payload=payload.model_dump(),
            report_date=payload.week_end,
            current_user=current_user,
        )

    def list_reports(self, current_user: CurrentUser) -> Sequence[ReportResponse]:
        if use_file_persistence():
            return state_store.list_reports(current_user)

        return require_database_result(report_repository.list_reports(current_user), "Reports")

    def get_report(self, report_id: str, current_user: CurrentUser) -> ReportResponse:
        if use_file_persistence():
            reports = state_store.list_reports(current_user)
            for item in reports:
                if item.id == report_id:
                    return item
            raise HTTPException(status_code=404, detail="Report not found")

        report = report_repository.get_report(report_id, current_user)
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")
        return report

    def list_report_jobs(self, current_user: CurrentUser) -> Sequence[ReportJobResponse]:
        if use_file_persistence():
            return []

        return require_database_result(report_repository.list_report_jobs(current_user), "Report jobs")

    def get_report_job(self, job_id: str, current_user: CurrentUser) -> ReportJobResponse:
        if use_file_persistence():
            raise HTTPException(status_code=404, detail="Report job not found")

        job = report_repository.get_report_job(job_id, current_user)
        if job is None:
            raise HTTPException(status_code=404, detail="Report job not found")
        return job


report_service = ReportService()
