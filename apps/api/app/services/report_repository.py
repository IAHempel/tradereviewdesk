from sqlalchemy import select

from app.core.auth import CurrentUser
from app.db.session import SessionLocal
from app.models.report import Report, ReportJob
from app.schemas.reports import ReportJobResponse, ReportResponse, ReportUsageMetrics
from app.services.db_demo_context import get_or_create_current_user, with_db_fallback


def _to_response(report: Report) -> ReportResponse:
    return ReportResponse(
        id=report.id,
        report_type=report.report_type,
        title=report.title,
        report_date=str(report.report_date),
        status="succeeded",
        input_summary=dict(report.input_summary or {}),
        parsed_output=dict(report.parsed_output or {}),
        disclaimer=str((report.parsed_output or {}).get("disclaimer") or "Workflow support only."),
        report_job_id=report.report_job_id,
    )


def _job_to_response(job: ReportJob, report_id: str | None = None) -> ReportJobResponse:
    return ReportJobResponse(
        id=job.id,
        report_type=job.report_type,
        status=job.status,
        attempts=job.attempts,
        input_payload=dict(job.input_payload or {}),
        error_message=job.error_message,
        raw_model_output=job.raw_model_output,
        parsed_output=dict(job.parsed_output) if job.parsed_output is not None else None,
        usage_metrics=ReportUsageMetrics.model_validate(dict(job.usage_metrics)) if job.usage_metrics is not None else None,
        report_id=report_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def list_reports(current_user: CurrentUser) -> list[ReportResponse] | None:
    def action() -> list[ReportResponse]:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            reports = list(
                session.scalars(
                    select(Report)
                    .where(Report.user_id == user.id)
                    .order_by(Report.report_date.desc(), Report.created_at.desc())
                )
            )
            return [_to_response(report) for report in reports]

    return with_db_fallback(action)


def save_report(
    payload: ReportResponse,
    current_user: CurrentUser,
    *,
    report_job_id: str | None,
    raw_model_output: str | None,
) -> ReportResponse | None:
    def action() -> ReportResponse:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            report = Report(
                user_id=user.id,
                report_job_id=report_job_id,
                report_type=payload.report_type,
                title=payload.title,
                report_date=payload.report_date,
                input_summary=payload.input_summary,
                raw_model_output=raw_model_output,
                parsed_output={**payload.parsed_output, "disclaimer": payload.disclaimer},
            )
            session.add(report)
            session.commit()
            session.refresh(report)
            return _to_response(report)

    return with_db_fallback(action)


def get_report(report_id: str, current_user: CurrentUser) -> ReportResponse | None:
    def action() -> ReportResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            report = session.scalar(select(Report).where(Report.id == report_id, Report.user_id == user.id))
            if report is None:
                return None
            return _to_response(report)

    return with_db_fallback(action)


def create_report_job(current_user: CurrentUser, report_type: str, input_payload: dict) -> ReportJobResponse | None:
    def action() -> ReportJobResponse:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            job = ReportJob(
                user_id=user.id,
                report_type=report_type,
                status="queued",
                attempts=0,
                input_payload=input_payload,
                error_message=None,
                raw_model_output=None,
                parsed_output=None,
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return _job_to_response(job)

    return with_db_fallback(action)


def update_report_job(
    job_id: str,
    current_user: CurrentUser,
    *,
    status: str,
    attempts: int | None = None,
    error_message: str | None = None,
    raw_model_output: str | None = None,
    parsed_output: dict | None = None,
    usage_metrics: dict | None = None,
) -> ReportJobResponse | None:
    def action() -> ReportJobResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            job = session.scalar(select(ReportJob).where(ReportJob.id == job_id, ReportJob.user_id == user.id))
            if job is None:
                return None

            job.status = status
            if attempts is not None:
                job.attempts = attempts
            job.error_message = error_message
            job.raw_model_output = raw_model_output
            job.parsed_output = parsed_output
            job.usage_metrics = usage_metrics

            session.add(job)
            session.commit()
            session.refresh(job)

            report_id = session.scalar(select(Report.id).where(Report.report_job_id == job.id))
            return _job_to_response(job, report_id=report_id)

    return with_db_fallback(action)


def get_report_job(job_id: str, current_user: CurrentUser) -> ReportJobResponse | None:
    def action() -> ReportJobResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            job = session.scalar(select(ReportJob).where(ReportJob.id == job_id, ReportJob.user_id == user.id))
            if job is None:
                return None
            report_id = session.scalar(select(Report.id).where(Report.report_job_id == job.id))
            return _job_to_response(job, report_id=report_id)

    return with_db_fallback(action)


def list_report_jobs(current_user: CurrentUser) -> list[ReportJobResponse] | None:
    def action() -> list[ReportJobResponse]:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            jobs = list(
                session.scalars(
                    select(ReportJob)
                    .where(ReportJob.user_id == user.id)
                    .order_by(ReportJob.created_at.desc())
                )
            )
            report_ids = {
                report_job_id: report_id
                for report_job_id, report_id in session.execute(select(Report.report_job_id, Report.id)).all()
                if report_job_id is not None
            }
            return [_job_to_response(job, report_id=report_ids.get(job.id)) for job in jobs]

    return with_db_fallback(action)
