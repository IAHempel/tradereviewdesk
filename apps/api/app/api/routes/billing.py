from fastapi import APIRouter, Depends, Header, Request

from app.core.auth import CurrentUser, require_current_user
from app.schemas.billing import (
    BillingPortalCreate,
    BillingPortalResponse,
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    SubscriptionResponse,
)
from app.services import billing_service

router = APIRouter()


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(current_user: CurrentUser = Depends(require_current_user)) -> SubscriptionResponse:
    return billing_service.get_subscription(current_user)


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    payload: CheckoutSessionCreate,
    current_user: CurrentUser = Depends(require_current_user),
) -> CheckoutSessionResponse:
    return billing_service.create_checkout_session(
        current_user,
        plan=payload.plan,
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
    )


@router.post("/create-portal-session", response_model=BillingPortalResponse)
def create_portal_session(
    payload: BillingPortalCreate,
    current_user: CurrentUser = Depends(require_current_user),
) -> BillingPortalResponse:
    return billing_service.create_portal_session(current_user, return_url=payload.return_url)


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    return billing_service.handle_webhook(await request.body(), stripe_signature)
