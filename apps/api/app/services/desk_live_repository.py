from uuid import UUID

from sqlalchemy import select

from app.core.auth import CurrentUser
from app.db.session import SessionLocal
from app.models.desk import DeskLiveSession
from app.models.user import User
from app.schemas.desk import DESK_LIVE_ACTIVE_STATUSES, DeskLiveSessionRecord
from app.services.db_demo_context import get_or_create_current_user, with_db_fallback

_IDENTITY_FIELDS = {"id", "created_at"}


def _to_record(row: DeskLiveSession) -> DeskLiveSessionRecord:
    return DeskLiveSessionRecord.model_validate({**row.record, "id": row.id, "created_at": row.created_at.isoformat()})


def _payload(record: DeskLiveSessionRecord) -> dict:
    return record.model_dump(mode="json", exclude=_IDENTITY_FIELDS)


def create(record: DeskLiveSessionRecord, current_user: CurrentUser) -> DeskLiveSessionRecord | None:
    def action() -> DeskLiveSessionRecord:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            row = DeskLiveSession(
                user_id=user.id, status=record.status, session_date=record.session_date, record=_payload(record)
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return _to_record(row)

    return with_db_fallback(action)


def latest(current_user: CurrentUser) -> DeskLiveSessionRecord | None:
    def action() -> DeskLiveSessionRecord | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            row = session.scalar(
                select(DeskLiveSession)
                .where(DeskLiveSession.user_id == user.id)
                .order_by(DeskLiveSession.created_at.desc())
                .limit(1)
            )
            session.commit()
            return _to_record(row) if row is not None else None

    return with_db_fallback(action)


def get(session_id: str, current_user: CurrentUser) -> DeskLiveSessionRecord | None:
    try:
        UUID(session_id)
    except ValueError:
        return None

    def action() -> DeskLiveSessionRecord | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            row = session.scalar(
                select(DeskLiveSession).where(DeskLiveSession.id == session_id, DeskLiveSession.user_id == user.id)
            )
            return _to_record(row) if row is not None else None

    return with_db_fallback(action)


def save(record: DeskLiveSessionRecord, current_user: CurrentUser) -> DeskLiveSessionRecord | None:
    def action() -> DeskLiveSessionRecord | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            row = session.scalar(
                select(DeskLiveSession).where(DeskLiveSession.id == record.id, DeskLiveSession.user_id == user.id)
            )
            if row is None:
                return None
            row.status = record.status
            row.record = _payload(record)
            session.commit()
            session.refresh(row)
            return _to_record(row)

    return with_db_fallback(action)


def active_owners() -> list[tuple[str, str]] | None:
    """(auth provider id, email) for every user with an active live session."""

    def action() -> list[tuple[str, str]]:
        with SessionLocal() as session:
            rows = session.execute(
                select(User.auth_provider_id, User.email)
                .join(DeskLiveSession, DeskLiveSession.user_id == User.id)
                .where(DeskLiveSession.status.in_(DESK_LIVE_ACTIVE_STATUSES))
                .distinct()
            )
            return [(auth_provider_id, email) for auth_provider_id, email in rows]

    return with_db_fallback(action)
