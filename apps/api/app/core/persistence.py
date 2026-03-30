from fastapi import HTTPException, status

from app.core.config import settings

from typing import TypeVar

T = TypeVar("T")


def use_file_persistence() -> bool:
    return settings.persistence_mode == "file"


def require_database_result(result: T | None, resource_name: str) -> T:
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{resource_name} is unavailable because database persistence is active but the database could not be reached.",
        )

    return result
