from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException, status

from app.core.auth import CurrentUser
from app.core.config import settings
from app.schemas.billing import BillingPortalResponse, CheckoutSessionResponse, SubscriptionResponse
from app.services import subscription_repository

PLAN_ORDER = {"free": 0, "pro": 1, "elite": 2}
FEATURE_REQUIREMENTS = {
    "checklists": "pro",
    "debrief_reports": "pro",
    "weekly_review_reports": "pro",
}
STRIPE_API_BASE = "https://api.stripe.com/v1"


def _normalize_plan(plan: str) -> str:
    normalized = plan.strip().lower()
    if normalized not in PLAN_ORDER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported subscription plan.")
    return normalized


def _is_placeholder(value: str) -> bool:
    return "placeholder" in value or value == "replace-me"


def stripe_is_configured() -> bool:
    return not (
        not settings.stripe_secret_key
        or _is_placeholder(settings.stripe_secret_key)
        or _is_placeholder(settings.stripe_price_id_pro)
        or _is_placeholder(settings.stripe_price_id_elite)
    )


def require_stripe_configuration() -> None:
    if settings.is_production and not stripe_is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe billing is not configured for production.",
        )


def _is_webhook_signature_configured() -> bool:
    return bool(settings.stripe_webhook_secret) and not _is_placeholder(settings.stripe_webhook_secret)


def _resolve_price_id(plan: str) -> str | None:
    if plan == "pro":
        return settings.stripe_price_id_pro
    if plan == "elite":
        return settings.stripe_price_id_elite
    return None


def _resolve_plan_from_price_id(price_id: str | None, fallback_plan: str | None = None) -> str:
    if price_id == settings.stripe_price_id_pro:
        return "pro"
    if price_id == settings.stripe_price_id_elite:
        return "elite"
    return _normalize_plan(fallback_plan or "free")


def _build_app_url(path_or_url: str | None, fallback_path: str) -> str:
    if path_or_url:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        return urljoin(f"{settings.app_url.rstrip('/')}/", path_or_url.lstrip("/"))
    return urljoin(f"{settings.app_url.rstrip('/')}/", fallback_path.lstrip("/"))


def get_subscription(current_user: CurrentUser) -> SubscriptionResponse:
    return subscription_repository.get_subscription(current_user, is_stub=not stripe_is_configured()) or SubscriptionResponse(
        plan="free",
        status="active",
        current_period_end=None,
        is_stub=not stripe_is_configured(),
    )


def _request_stripe(path: str, *, form_data: dict[str, str]) -> dict:
    response = httpx.post(
        f"{STRIPE_API_BASE}{path}",
        data=form_data,
        headers={"Authorization": f"Bearer {settings.stripe_secret_key}"},
        timeout=20.0,
    )
    response.raise_for_status()
    return response.json()


def create_checkout_session(
    current_user: CurrentUser,
    *,
    plan: str,
    success_url: str | None,
    cancel_url: str | None,
) -> CheckoutSessionResponse:
    require_stripe_configuration()

    normalized_plan = _normalize_plan(plan)
    if normalized_plan == "free":
        subscription_repository.sync_subscription_for_user(
            current_user,
            plan="free",
            status="active",
            current_period_end=None,
            is_stub=not stripe_is_configured(),
        )
        return CheckoutSessionResponse(
            url=_build_app_url("/app/settings?billing=free", "/app/settings?billing=free"),
            mode="internal",
        )

    if not stripe_is_configured():
        subscription_repository.sync_subscription_for_user(
            current_user,
            plan=normalized_plan,
            status="checkout_pending",
            current_period_end=None,
            is_stub=True,
        )
        return CheckoutSessionResponse(
            url=_build_app_url(
                f"/app/settings?billing=stub-checkout&plan={normalized_plan}",
                f"/app/settings?billing=stub-checkout&plan={normalized_plan}",
            ),
            mode="stub",
        )

    existing_ids = subscription_repository.get_stripe_ids_for_user(current_user)
    stripe_customer_id = existing_ids[0] if existing_ids else None
    form_data = {
        "mode": "subscription",
        "success_url": _build_app_url(success_url, settings.stripe_checkout_success_path),
        "cancel_url": _build_app_url(cancel_url, settings.stripe_checkout_cancel_path),
        "client_reference_id": current_user.auth_provider_id,
        "metadata[auth_provider_id]": current_user.auth_provider_id,
        "metadata[email]": current_user.email,
        "metadata[plan]": normalized_plan,
        "subscription_data[metadata][auth_provider_id]": current_user.auth_provider_id,
        "subscription_data[metadata][email]": current_user.email,
        "subscription_data[metadata][plan]": normalized_plan,
        "line_items[0][price]": _resolve_price_id(normalized_plan) or "",
        "line_items[0][quantity]": "1",
    }
    if stripe_customer_id:
        form_data["customer"] = stripe_customer_id
    else:
        form_data["customer_email"] = current_user.email

    try:
        payload = _request_stripe("/checkout/sessions", form_data=form_data)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to create Stripe checkout session right now.",
        ) from exc

    subscription_repository.sync_subscription_for_user(
        current_user,
        plan=normalized_plan,
        status="checkout_pending",
        current_period_end=None,
        stripe_customer_id=payload.get("customer"),
        is_stub=False,
    )
    return CheckoutSessionResponse(url=payload["url"], mode="stripe")


def create_portal_session(current_user: CurrentUser, *, return_url: str | None) -> BillingPortalResponse:
    require_stripe_configuration()

    subscription = get_subscription(current_user)
    stripe_ids = subscription_repository.get_stripe_ids_for_user(current_user)
    stripe_customer_id = stripe_ids[0] if stripe_ids else None

    if not stripe_is_configured() or not stripe_customer_id:
        return BillingPortalResponse(
            url=_build_app_url("/app/settings?billing=stub-portal", "/app/settings?billing=stub-portal"),
            mode="stub",
        )

    try:
        payload = _request_stripe(
            "/billing_portal/sessions",
            form_data={
                "customer": stripe_customer_id,
                "return_url": _build_app_url(return_url, settings.stripe_billing_portal_return_path),
            },
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to create Stripe billing portal session right now.",
        ) from exc

    return BillingPortalResponse(url=payload["url"], mode="stripe" if not subscription.is_stub else "stub")


def require_feature_access(current_user: CurrentUser, feature: str) -> SubscriptionResponse:
    subscription = get_subscription(current_user)
    required_plan = FEATURE_REQUIREMENTS[feature]
    if PLAN_ORDER.get(subscription.plan, 0) < PLAN_ORDER[required_plan]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"{required_plan.title()} plan required to use this workflow.",
        )
    return subscription


def _parse_signature_header(signature_header: str) -> tuple[int, list[str]]:
    timestamp = 0
    signatures: list[str] = []
    for part in signature_header.split(","):
        key, _, value = part.partition("=")
        if key == "t" and value.isdigit():
            timestamp = int(value)
        elif key == "v1" and value:
            signatures.append(value)
    return timestamp, signatures


def _verify_webhook_signature(payload: bytes, signature_header: str | None) -> None:
    if not _is_webhook_signature_configured():
        return
    if not signature_header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe signature header.")

    timestamp, signatures = _parse_signature_header(signature_header)
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(
        settings.stripe_webhook_secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not signatures or not any(hmac.compare_digest(expected, signature) for signature in signatures):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe signature.")


def _unix_to_datetime(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=UTC)


def _extract_subscription_plan(subscription_payload: dict) -> str:
    items = (((subscription_payload.get("items") or {}).get("data")) or [])
    price_id = None
    if items:
        price_id = ((items[0].get("price") or {}).get("id")) if isinstance(items[0], dict) else None
    metadata = subscription_payload.get("metadata") or {}
    return _resolve_plan_from_price_id(price_id, metadata.get("plan"))


def handle_webhook(payload: bytes, signature_header: str | None) -> dict[str, str]:
    require_stripe_configuration()

    _verify_webhook_signature(payload, signature_header)

    try:
        event = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe webhook payload.") from exc

    event_type = event.get("type")
    event_object = ((event.get("data") or {}).get("object")) or {}

    if event_type == "checkout.session.completed":
        metadata = event_object.get("metadata") or {}
        auth_provider_id = metadata.get("auth_provider_id")
        if not auth_provider_id:
            return {"received": "true"}
        subscription_repository.sync_subscription_by_auth_provider_id(
            auth_provider_id,
            email=metadata.get("email"),
            stripe_customer_id=event_object.get("customer"),
            stripe_subscription_id=event_object.get("subscription"),
            plan=_normalize_plan(metadata.get("plan", "free")),
            status="active",
            current_period_end=None,
            is_stub=not stripe_is_configured(),
        )
    elif event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
        subscription_repository.sync_subscription_by_stripe_customer(
            str(event_object.get("customer") or ""),
            stripe_subscription_id=event_object.get("id"),
            plan=_extract_subscription_plan(event_object),
            status=str(event_object.get("status") or "active"),
            current_period_end=_unix_to_datetime(event_object.get("current_period_end")),
            is_stub=not stripe_is_configured(),
        )

    return {"received": "true"}
