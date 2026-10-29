from uuid import UUID

from sqlalchemy import select

from app.core.auth import CurrentUser
from app.db.session import SessionLocal
from app.models.desk import DeskRun
from app.schemas.desk import DeskRunResponse, DeskRunSummaryResponse
from app.services.db_demo_context import get_or_create_current_user, with_db_fallback

_IDENTITY_FIELDS = {"id", "created_at"}


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def _to_summary(run: DeskRun) -> DeskRunSummaryResponse:
    return DeskRunSummaryResponse(
        id=run.id,
        created_at=run.created_at.isoformat(),
        mode=run.mode,
        data_source=run.data_source,
        config=run.config,
        summary=run.summary,
    )


def _to_response(run: DeskRun) -> DeskRunResponse:
    return DeskRunResponse.model_validate({**run.result, "id": run.id, "created_at": run.created_at.isoformat()})


def create_desk_run(result: DeskRunResponse, current_user: CurrentUser) -> DeskRunResponse | None:
    def action() -> DeskRunResponse:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            run = DeskRun(
                user_id=user.id,
                mode=result.mode,
                data_source=result.data_source,
                config=result.config.model_dump(mode="json"),
                summary=result.summary.model_dump(mode="json"),
                result=result.model_dump(mode="json", exclude=_IDENTITY_FIELDS),
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return _to_response(run)

    return with_db_fallback(action)


def list_desk_runs(current_user: CurrentUser, *, limit: int) -> list[DeskRunSummaryResponse] | None:
    def action() -> list[DeskRunSummaryResponse]:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            runs = session.scalars(
                select(DeskRun).where(DeskRun.user_id == user.id).order_by(DeskRun.created_at.desc()).limit(limit)
            )
            return [_to_summary(run) for run in runs]

    return with_db_fallback(action)


def get_desk_run(run_id: str, current_user: CurrentUser) -> DeskRunResponse | None:
    if not _is_uuid(run_id):
        return None

    def action() -> DeskRunResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            run = session.scalar(select(DeskRun).where(DeskRun.id == run_id, DeskRun.user_id == user.id))
            return _to_response(run) if run is not None else None

    return with_db_fallback(action)
