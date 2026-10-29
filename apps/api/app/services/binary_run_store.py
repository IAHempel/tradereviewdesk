"""Saved binary desk runs in either persistence mode."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.auth import CurrentUser
from app.core.persistence import require_database_result, use_file_persistence
from app.db.session import SessionLocal
from app.models.desk import BinaryRun
from app.schemas.binary import BinaryRunResponse, BinaryRunSummaryResponse
from app.services import state_store
from app.services.db_demo_context import get_or_create_current_user, with_db_fallback

RUN_HISTORY_LIMIT = 20
FILE_RUN_HISTORY_LIMIT = 5
_IDENTITY_FIELDS = {"id", "created_at"}


def _to_response(run: BinaryRun) -> BinaryRunResponse:
    return BinaryRunResponse.model_validate({**run.result, "id": run.id, "created_at": run.created_at.isoformat()})


def save_run(result: BinaryRunResponse, current_user: CurrentUser) -> BinaryRunResponse:
    if use_file_persistence():
        run = result.model_copy(update={"id": str(uuid4()), "created_at": datetime.now(UTC).isoformat()})
        history = state_store.list_binary_runs(current_user)
        state_store.save_binary_runs([run, *history][:FILE_RUN_HISTORY_LIMIT], current_user)
        return run

    def action() -> BinaryRunResponse:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            run = BinaryRun(
                user_id=user.id,
                data_source=result.data_source,
                config=result.config.model_dump(mode="json"),
                summary=result.summary.model_dump(mode="json"),
                result=result.model_dump(mode="json", exclude=_IDENTITY_FIELDS),
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return _to_response(run)

    return require_database_result(with_db_fallback(action), "Binary run")


def list_runs(current_user: CurrentUser) -> list[BinaryRunSummaryResponse]:
    if use_file_persistence():
        return [
            BinaryRunSummaryResponse.model_validate(run.model_dump(include=set(BinaryRunSummaryResponse.model_fields)))
            for run in state_store.list_binary_runs(current_user)
        ]

    def action() -> list[BinaryRunSummaryResponse]:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            rows = session.execute(
                select(
                    BinaryRun.id,
                    BinaryRun.created_at,
                    BinaryRun.data_source,
                    BinaryRun.config,
                    BinaryRun.summary,
                    BinaryRun.result["baseline"],
                )
                .where(BinaryRun.user_id == user.id)
                .order_by(BinaryRun.created_at.desc())
                .limit(RUN_HISTORY_LIMIT)
            )
            return [
                BinaryRunSummaryResponse(
                    id=run_id,
                    created_at=created_at.isoformat(),
                    data_source=data_source,
                    config=config,
                    summary=summary,
                    baseline=baseline,
                )
                for run_id, created_at, data_source, config, summary, baseline in rows
            ]

    return require_database_result(with_db_fallback(action), "Binary runs")


def get_run(run_id: str, current_user: CurrentUser) -> BinaryRunResponse | None:
    if use_file_persistence():
        return next((item for item in state_store.list_binary_runs(current_user) if item.id == run_id), None)
    try:
        UUID(run_id)
    except ValueError:
        return None

    def action() -> BinaryRunResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            run = session.scalar(select(BinaryRun).where(BinaryRun.id == run_id, BinaryRun.user_id == user.id))
            return _to_response(run) if run is not None else None

    return with_db_fallback(action)
