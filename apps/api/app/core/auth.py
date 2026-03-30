import hashlib
import hmac
import time
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from app.core.config import settings

LOCAL_DEMO_AUTH_PROVIDER_ID = "local-demo-user"


@dataclass(frozen=True)
class CurrentUser:
    auth_provider: str
    auth_provider_user_id: str
    auth_provider_id: str
    email: str
    display_name: str | None = None


def is_auth_enabled() -> bool:
    return settings.auth_mode == "clerk"


def require_auth_configuration() -> None:
    if settings.is_production and settings.auth_mode != "clerk":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured for production.",
        )

    if settings.is_production and settings.auth_mode == "clerk" and settings.is_placeholder_auth_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication secret is not configured for production.",
        )


def get_demo_user() -> CurrentUser:
    from app.services import state_store

    profile = state_store.get_profile()
    return CurrentUser(
        auth_provider="local",
        auth_provider_user_id=LOCAL_DEMO_AUTH_PROVIDER_ID,
        auth_provider_id=f"local:{LOCAL_DEMO_AUTH_PROVIDER_ID}",
        email=profile.email,
        display_name=profile.display_name,
    )


def _build_signature(
    auth_provider: str,
    auth_user_id: str,
    auth_email: str,
    auth_display_name: str,
    auth_timestamp: str,
) -> str:
    payload = "\n".join([auth_provider, auth_user_id, auth_email, auth_display_name, auth_timestamp])
    return hmac.new(
        settings.auth_internal_shared_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def require_current_user(
    x_tradenoc_auth_provider: str | None = Header(default=None),
    x_tradenoc_auth_user_id: str | None = Header(default=None),
    x_tradenoc_auth_email: str | None = Header(default=None),
    x_tradenoc_auth_display_name: str | None = Header(default=None),
    x_tradenoc_auth_timestamp: str | None = Header(default=None),
    x_tradenoc_auth_signature: str | None = Header(default=None),
) -> CurrentUser:
    require_auth_configuration()

    if not is_auth_enabled():
        return get_demo_user()

    missing_headers = [
        name
        for name, value in (
            ("X-TradeNOC-Auth-Provider", x_tradenoc_auth_provider),
            ("X-TradeNOC-Auth-User-Id", x_tradenoc_auth_user_id),
            ("X-TradeNOC-Auth-Email", x_tradenoc_auth_email),
            ("X-TradeNOC-Auth-Timestamp", x_tradenoc_auth_timestamp),
            ("X-TradeNOC-Auth-Signature", x_tradenoc_auth_signature),
        )
        if not value
    ]
    if missing_headers:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing auth headers: {', '.join(missing_headers)}",
        )

    try:
        request_timestamp = int(x_tradenoc_auth_timestamp)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth timestamp.") from exc

    if abs(int(time.time()) - request_timestamp) > settings.auth_request_ttl_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth request expired.")

    expected_signature = _build_signature(
        auth_provider=x_tradenoc_auth_provider,
        auth_user_id=x_tradenoc_auth_user_id,
        auth_email=x_tradenoc_auth_email,
        auth_display_name=x_tradenoc_auth_display_name or "",
        auth_timestamp=x_tradenoc_auth_timestamp,
    )
    if not hmac.compare_digest(expected_signature, x_tradenoc_auth_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth signature.")

    if x_tradenoc_auth_provider != "clerk":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported auth provider.")

    return CurrentUser(
        auth_provider=x_tradenoc_auth_provider,
        auth_provider_user_id=x_tradenoc_auth_user_id,
        auth_provider_id=f"{x_tradenoc_auth_provider}:{x_tradenoc_auth_user_id}",
        email=x_tradenoc_auth_email,
        display_name=x_tradenoc_auth_display_name or None,
    )
