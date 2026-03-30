from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, require_current_user
from app.core.persistence import require_database_result, use_file_persistence
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services import profile_repository, state_store

router = APIRouter()


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: CurrentUser = Depends(require_current_user)) -> ProfileResponse:
    if use_file_persistence():
        return state_store.get_profile(current_user)

    return require_database_result(profile_repository.get_profile(current_user), "Profile")


@router.put("", response_model=ProfileResponse)
def update_profile(payload: ProfileUpdate, current_user: CurrentUser = Depends(require_current_user)) -> ProfileResponse:
    if use_file_persistence():
        return state_store.update_profile(payload, current_user)

    return require_database_result(profile_repository.update_profile(payload, current_user), "Profile")
