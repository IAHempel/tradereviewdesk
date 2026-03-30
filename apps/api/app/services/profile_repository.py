from sqlalchemy import select

from app.core.auth import CurrentUser
from app.db.session import SessionLocal
from app.models.user import Profile, User
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services import state_store
from app.services.db_demo_context import get_or_create_current_user, with_db_fallback


def _build_profile_response(user: User, profile: Profile) -> ProfileResponse:
    return ProfileResponse(
        email=user.email,
        display_name=profile.display_name,
        trading_style=profile.trading_style,
        pain_points=list(profile.pain_points or []),
        broker_platform=profile.broker_platform,
        onboarding_completed=profile.onboarding_completed,
    )


def _get_or_create_scoped_profile(session, current_user: CurrentUser) -> tuple[User, Profile]:
    fallback = state_store.get_profile(current_user)
    user = get_or_create_current_user(session, current_user)

    profile = session.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        profile = Profile(
            user_id=user.id,
            display_name=fallback.display_name,
            trading_style=fallback.trading_style,
            pain_points=fallback.pain_points,
            broker_platform=fallback.broker_platform,
            onboarding_completed=fallback.onboarding_completed,
        )
        session.add(profile)
        session.flush()

    return user, profile


def get_profile(current_user: CurrentUser) -> ProfileResponse | None:
    def action() -> ProfileResponse:
        with SessionLocal() as session:
            user, profile = _get_or_create_scoped_profile(session, current_user)
            session.commit()
            session.refresh(user)
            session.refresh(profile)
            return _build_profile_response(user, profile)

    return with_db_fallback(action)


def update_profile(payload: ProfileUpdate, current_user: CurrentUser) -> ProfileResponse | None:
    def action() -> ProfileResponse:
        with SessionLocal() as session:
            user, profile = _get_or_create_scoped_profile(session, current_user)
            update_data = payload.model_dump(exclude_unset=True)

            if "display_name" in update_data:
                profile.display_name = update_data["display_name"]
            if "trading_style" in update_data and update_data["trading_style"] is not None:
                profile.trading_style = update_data["trading_style"]
            if "pain_points" in update_data and update_data["pain_points"] is not None:
                profile.pain_points = update_data["pain_points"]
            if "broker_platform" in update_data:
                profile.broker_platform = update_data["broker_platform"]
            if "onboarding_completed" in update_data and update_data["onboarding_completed"] is not None:
                profile.onboarding_completed = update_data["onboarding_completed"]

            session.add(profile)
            session.commit()
            session.refresh(user)
            session.refresh(profile)
            return _build_profile_response(user, profile)

    return with_db_fallback(action)
