"""Push notifications for live desk sessions: ntfy, Discord, or Slack webhooks.

The server posts to a URL the user supplies, so only known webhook hosts are
accepted (no private addresses, no arbitrary hosts). An operator can allow a
self-hosted ntfy server with DESK_NOTIFY_EXTRA_HOSTS.
"""

from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

import httpx

from app.core.config import settings

NotifyChannel = Literal["ntfy", "discord", "slack"]
_CHANNEL_HOSTS: dict[str, NotifyChannel] = {
    "ntfy.sh": "ntfy",
    "discord.com": "discord",
    "discordapp.com": "discord",
    "hooks.slack.com": "slack",
}
NOTIFY_TIMEOUT_SECONDS = 5.0


class NotifyURLError(ValueError):
    pass


def channel_for(url: str) -> NotifyChannel:
    """Validates a webhook URL and returns its channel, or raises NotifyURLError with a user-facing reason."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if parts.scheme != "https":
        raise NotifyURLError("Notification URLs must start with https://.")
    if parts.username or parts.password or parts.port not in (None, 443):
        raise NotifyURLError("Notification URLs can't carry credentials or a custom port.")

    extra = {item.strip().lower() for item in settings.desk_notify_extra_hosts.split(",") if item.strip()}
    if host in extra:
        channel: NotifyChannel = "ntfy"
    elif host in _CHANNEL_HOSTS:
        channel = _CHANNEL_HOSTS[host]
    else:
        raise NotifyURLError("Use an ntfy.sh topic, a Discord webhook, or a Slack incoming webhook URL.")

    path = parts.path.strip("/")
    if channel == "ntfy" and (not path or "/" in path):
        raise NotifyURLError("An ntfy URL needs exactly one topic, like https://ntfy.sh/my-desk-alerts.")
    if channel == "discord" and not path.startswith("api/webhooks/"):
        raise NotifyURLError("A Discord URL must be a webhook (https://discord.com/api/webhooks/...).")
    if channel == "slack" and not path.startswith("services/"):
        raise NotifyURLError("A Slack URL must be an incoming webhook (https://hooks.slack.com/services/...).")
    return channel


@dataclass(frozen=True)
class DeskNotification:
    title: str
    body: str
    urgent: bool = False


def send(url: str, notification: DeskNotification, *, client: httpx.Client) -> str | None:
    """Posts the notification. Returns an error message instead of raising, so a dead webhook never stops the desk."""
    try:
        channel = channel_for(url)
    except NotifyURLError as exc:
        return str(exc)

    link = f"{settings.app_url.rstrip('/')}/app/desk"
    try:
        if channel == "ntfy":
            response = client.post(
                url,
                content=notification.body.encode("utf-8"),
                headers={
                    "Title": notification.title,
                    "Tags": "warning" if notification.urgent else "chart_with_upwards_trend",
                    "Priority": "high" if notification.urgent else "default",
                    "Click": link,
                },
                timeout=NOTIFY_TIMEOUT_SECONDS,
            )
        elif channel == "discord":
            response = client.post(
                url,
                json={"content": f"**{notification.title}**\n{notification.body}\n{link}"},
                timeout=NOTIFY_TIMEOUT_SECONDS,
            )
        else:
            response = client.post(
                url,
                json={"text": f"*{notification.title}*\n{notification.body}\n<{link}|Open the desk>"},
                timeout=NOTIFY_TIMEOUT_SECONDS,
            )
    except httpx.HTTPError as exc:
        return f"Notification failed: {exc.__class__.__name__}."
    if response.status_code >= 400:
        return f"Notification failed: HTTP {response.status_code}."
    return None
