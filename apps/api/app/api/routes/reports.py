from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, require_current_user
from app.schemas.reports import (
    DebriefGenerateRequest,
    PremarketGenerateRequest,
    ReportGenerationResponse,
    ReportJobResponse,
    ReportResponse,
    WeeklyReviewGenerateRequest,
)
from app.services import billing_service
from app.services.reports import report_service

router = APIRouter()


@router.get("/jobs", response_model=list[ReportJobResponse])
def list_report_jobs(current_user: CurrentUser = Depends(require_current_user)) -> list[ReportJobResponse]:
    return list(report_service.list_report_jobs(current_user))


@router.get("/jobs/{job_id}", response_model=ReportJobResponse)
def get_report_job(job_id: str, current_user: CurrentUser = Depends(require_current_user)) -> ReportJobResponse:
    return report_service.get_report_job(job_id, current_user)


@router.post("/premarket/generate", response_model=ReportGenerationResponse)
def generate_premarket_report(
    payload: PremarketGenerateRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> ReportGenerationResponse:
    return report_service.generate_premarket(payload, current_user)


@router.post("/debrief/generate", response_model=ReportGenerationResponse)
def generate_debrief_report(
    payload: DebriefGenerateRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> ReportGenerationResponse:
    billing_service.require_feature_access(current_user, "debrief_reports")
    return report_service.generate_debrief(payload, current_user)


@router.post("/weekly-review/generate", response_model=ReportGenerationResponse)
def generate_weekly_review(
    payload: WeeklyReviewGenerateRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> ReportGenerationResponse:
    billing_service.require_feature_access(current_user, "weekly_review_reports")
    return report_service.generate_weekly_review(payload, current_user)


@router.get("", response_model=list[ReportResponse])
def list_reports(current_user: CurrentUser = Depends(require_current_user)) -> list[ReportResponse]:
    return list(report_service.list_reports(current_user))


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: str, current_user: CurrentUser = Depends(require_current_user)) -> ReportResponse:
    return report_service.get_report(report_id, current_user)
