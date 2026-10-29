"""Live desk sessions across both persistence modes, shared by the API and the background worker."""

import logging
from datetime import datetime

from app.core.auth import CurrentUser, get_demo_user
from app.core.persistence import require_database_result, use_file_persistence
from app.schemas.desk import DeskLiveSessionRecord
from app.services import desk_live_repository, desk_run_store, state_store
from app.services.desk import live

logger = logging.getLogger(__name__)

FILE_LIVE_HISTORY_LIMIT = 5
FINAL_STATUSES = ("closed", "stopped")


def latest(current_user: CurrentUser) -> DeskLiveSessionRecord | None:
    if use_file_persistence():
        records = state_store.list_desk_live_sessions(current_user)
        return records[0] if records else None
    return desk_live_repository.latest(current_user)


def get(session_id: str, current_user: CurrentUser) -> DeskLiveSessionRecord | None:
    if use_file_persistence():
        return next((item for item in state_store.list_desk_live_sessions(current_user) if item.id == session_id), None)
    return desk_live_repository.get(session_id, current_user)


def create(record: DeskLiveSessionRecord, current_user: CurrentUser) -> DeskLiveSessionRecord:
    record = finalize(record, current_user)
    if use_file_persistence():
        history = state_store.list_desk_live_sessions(current_user)
        state_store.save_desk_live_sessions([record, *history][:FILE_LIVE_HISTORY_LIMIT], current_user)
        return record
    return require_database_result(desk_live_repository.create(record, current_user), "Live session")


def save(record: DeskLiveSessionRecord, current_user: CurrentUser) -> DeskLiveSessionRecord:
    record = finalize(record, current_user)
    if use_file_persistence():
        history = state_store.list_desk_live_sessions(current_user)
        state_store.save_desk_live_sessions([record if item.id == record.id else item for item in history], current_user)
        return record
    return require_database_result(desk_live_repository.save(record, current_user), "Live session")


def finalize(record: DeskLiveSessionRecord, current_user: CurrentUser) -> DeskLiveSessionRecord:
    """Once a session is closed or stopped, its last result goes into the saved run history (once)."""
    if record.status not in FINAL_STATUSES or record.run_id or record.result is None or not record.result.frames:
        return record
    run = desk_run_store.save_run(record.result, current_user)
    return record.model_copy(update={"run_id": run.id})


def tick_and_save(
    record: DeskLiveSessionRecord, current_user: CurrentUser, *, now: datetime | None = None
) -> DeskLiveSessionRecord:
    ticked = live.tick(record, now=now)
    if ticked is record:
        return record
    return save(ticked, current_user)


def _owner(auth_provider_id: str | None, email: str) -> CurrentUser:
    if auth_provider_id is None:
        return get_demo_user()
    provider, _, user_id = auth_provider_id.partition(":")
    return CurrentUser(auth_provider=provider, auth_provider_user_id=user_id, auth_provider_id=auth_provider_id, email=email)


def tick_all(*, now: datetime | None = None) -> int:
    """Ticks every active live session; returns how many were checked. Errors in one never stop the rest."""
    owners = state_store.desk_live_session_owners() if use_file_persistence() else (desk_live_repository.active_owners() or [])
    checked = 0
    for auth_provider_id, email in owners:
        current_user = _owner(auth_provider_id, email)
        try:
            record = latest(current_user)
            if record is not None:
                tick_and_save(record, current_user, now=now)
                checked += 1
        except Exception:  # noqa: BLE001 - one user's failure must not stall everyone else's session
            logger.exception("Live desk tick failed for %s", auth_provider_id)
    return checked
