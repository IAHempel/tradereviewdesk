from typing import Callable, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

from app.core.persistence import use_file_persistence
from app.core.auth import CurrentUser
from app.models.user import User

T = TypeVar("T")


def with_db_fallback(action: Callable[[], T]) -> T | None:
    try:
        return action()
    except (OperationalError, ProgrammingError, SQLAlchemyError):
        if use_file_persistence():
            return None
        raise


def get_or_create_current_user(session, current_user: CurrentUser) -> User:
    user = session.scalar(select(User).where(User.auth_provider_id == current_user.auth_provider_id))

    if user is None:
        user = User(auth_provider_id=current_user.auth_provider_id, email=current_user.email)
        session.add(user)
        session.flush()
    elif user.email != current_user.email:
        user.email = current_user.email
        session.add(user)
        session.flush()

    return user
