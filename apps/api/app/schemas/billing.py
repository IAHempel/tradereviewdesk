from pydantic import BaseModel


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    current_period_end: str | None = None
    is_stub: bool = False


class CheckoutSessionCreate(BaseModel):
    plan: str
    success_url: str | None = None
    cancel_url: str | None = None


class CheckoutSessionResponse(BaseModel):
    url: str
    mode: str


class BillingPortalCreate(BaseModel):
    return_url: str | None = None


class BillingPortalResponse(BaseModel):
    url: str
    mode: str
