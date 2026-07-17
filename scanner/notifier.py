"""ntfy publishing.

Talks to the self-hosted ntfy instance at ntfy.charemma.de. Requires a
publish-scoped token (auth-default-access on that instance is deny-all) --
see k8s/secrets.md for how the token is created.
"""

from __future__ import annotations

import httpx


def notify(
    base_url: str,
    topic: str,
    token: str,
    title: str,
    message: str,
    click_url: str | None = None,
    priority: int = 3,
) -> None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Title": title.encode("utf-8"),
        "Priority": str(priority),
    }
    if click_url:
        headers["Click"] = click_url
    response = httpx.post(
        f"{base_url.rstrip('/')}/{topic}",
        content=message.encode("utf-8"),
        headers=headers,
        timeout=10.0,
    )
    response.raise_for_status()
