from datetime import datetime

from sqlalchemy import select

from app.core.auth import CurrentUser
from app.db.session import SessionLocal
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.billing import SubscriptionResponse
from app.services.db_demo_context import get_or_create_current_user, with_db_fallback


def _to_response(subscription: Subscription, *, is_stub: bool) -> SubscriptionResponse:
    return SubscriptionResponse(
        plan=subscription.plan,
        status=subscription.status,
        current_period_end=subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        is_stub=is_stub,
    )


def _get_or_create_subscription_record(session, user: User) -> Subscription:
    subscription = session.scalar(select(Subscription).where(Subscription.user_id == user.id))
    if subscription is None:
        subscription = Subscription(user_id=user.id, plan="free", status="active", current_period_end=None)
        session.add(subscription)
        session.flush()
    return subscription


def get_subscription(current_user: CurrentUser, *, is_stub: bool = False) -> SubscriptionResponse | None:
    def action() -> SubscriptionResponse:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            subscription = _get_or_create_subscription_record(session, user)
            session.commit()
            session.refresh(subscription)
            return _to_response(subscription, is_stub=is_stub)

    return with_db_fallback(action)


def sync_subscription_for_user(
    current_user: CurrentUser,
    *,
    plan: str,
    status: str,
    current_period_end: datetime | None = None,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    is_stub: bool = False,
) -> SubscriptionResponse | None:
    def action() -> SubscriptionResponse:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            subscription = _get_or_create_subscription_record(session, user)
            subscription.plan = plan
            subscription.status = status
            subscription.current_period_end = current_period_end
            if stripe_customer_id is not None:
                subscription.stripe_customer_id = stripe_customer_id
            if stripe_subscription_id is not None:
                subscription.stripe_subscription_id = stripe_subscription_id
            session.add(subscription)
            session.commit()
            session.refresh(subscription)
            return _to_response(subscription, is_stub=is_stub)

    return with_db_fallback(action)


def get_stripe_ids_for_user(current_user: CurrentUser) -> tuple[str | None, str | None] | None:
    def action() -> tuple[str | None, str | None]:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            subscription = _get_or_create_subscription_record(session, user)
            session.commit()
            return subscription.stripe_customer_id, subscription.stripe_subscription_id

    return with_db_fallback(action)


def sync_subscription_by_stripe_customer(
    stripe_customer_id: str,
    *,
    stripe_subscription_id: str | None,
    plan: str,
    status: str,
    current_period_end: datetime | None = None,
    is_stub: bool = False,
) -> SubscriptionResponse | None:
    def action() -> SubscriptionResponse | None:
        with SessionLocal() as session:
            subscription = session.scalar(
                select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
            )
            if subscription is None and stripe_subscription_id is not None:
                subscription = session.scalar(
                    select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
                )
            if subscription is None:
                return None

            subscription.plan = plan
            subscription.status = status
            subscription.current_period_end = current_period_end
            subscription.stripe_customer_id = stripe_customer_id
            if stripe_subscription_id is not None:
                subscription.stripe_subscription_id = stripe_subscription_id
            session.add(subscription)
            session.commit()
            session.refresh(subscription)
            return _to_response(subscription, is_stub=is_stub)

    return with_db_fallback(action)


def sync_subscription_by_auth_provider_id(
    auth_provider_id: str,
    *,
    email: str | None,
    stripe_customer_id: str | None,
    stripe_subscription_id: str | None,
    plan: str,
    status: str,
    current_period_end: datetime | None = None,
    is_stub: bool = False,
) -> SubscriptionResponse | None:
    def action() -> SubscriptionResponse | None:
        with SessionLocal() as session:
            user = session.scalar(select(User).where(User.auth_provider_id == auth_provider_id))
            if user is None:
                if email is None:
                    return None
                user = User(auth_provider_id=auth_provider_id, email=email)
                session.add(user)
                session.flush()
            elif email and user.email != email:
                user.email = email
                session.add(user)
                session.flush()

            subscription = _get_or_create_subscription_record(session, user)
            subscription.plan = plan
            subscription.status = status
            subscription.current_period_end = current_period_end
            if stripe_customer_id is not None:
                subscription.stripe_customer_id = stripe_customer_id
            if stripe_subscription_id is not None:
                subscription.stripe_subscription_id = stripe_subscription_id
            session.add(subscription)
            session.commit()
            session.refresh(subscription)
            return _to_response(subscription, is_stub=is_stub)

    return with_db_fallback(action)
