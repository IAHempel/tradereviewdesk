"""Saved desk runs in either persistence mode."""

from datetime import UTC, datetime
from uuid import uuid4

from app.core.auth import CurrentUser
from app.core.persistence import require_database_result, use_file_persistence
from app.schemas.desk import DeskRunResponse, DeskRunSummaryResponse
from app.services import desk_repository, state_store

RUN_HISTORY_LIMIT = 20
FILE_RUN_HISTORY_LIMIT = 5


def save_run(result: DeskRunResponse, current_user: CurrentUser) -> DeskRunResponse:
    if use_file_persistence():
        run = result.model_copy(update={"id": str(uuid4()), "created_at": datetime.now(UTC).isoformat()})
        history = state_store.list_desk_runs(current_user)
        state_store.save_desk_runs([run, *history][:FILE_RUN_HISTORY_LIMIT], current_user)
        return run
    return require_database_result(desk_repository.create_desk_run(result, current_user), "Desk run")


def list_runs(current_user: CurrentUser) -> list[DeskRunSummaryResponse]:
    if use_file_persistence():
        return [
            DeskRunSummaryResponse.model_validate(run.model_dump(include=set(DeskRunSummaryResponse.model_fields)))
            for run in state_store.list_desk_runs(current_user)
        ]
    return require_database_result(desk_repository.list_desk_runs(current_user, limit=RUN_HISTORY_LIMIT), "Desk runs")


def get_run(run_id: str, current_user: CurrentUser) -> DeskRunResponse | None:
    if use_file_persistence():
        return next((item for item in state_store.list_desk_runs(current_user) if item.id == run_id), None)
    return desk_repository.get_desk_run(run_id, current_user)
