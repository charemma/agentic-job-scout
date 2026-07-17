"""HTTP client for triggering the application-writer service.

Bounded retry/backoff (no tenacity dependency -- this is the only call site
that needs it, a manual loop is simpler than pulling in a library for one
use). A failure here must never crash the whole scanner run: the caller
catches `ComposeError` and moves on to the next posting, leaving this one
to be retried on the next hourly tick (dedup in store.py only marks a
posting "seen" once compose succeeds).
"""

from __future__ import annotations

import time
from dataclasses import asdict

import httpx

from scanner.models import JobPosting

RETRY_DELAYS_SECONDS = [1, 4, 16]


class ComposeError(RuntimeError):
    pass


def trigger_compose(
    base_url: str,
    token: str,
    posting: JobPosting,
    matched_keywords: list[str],
    request_id: str,
) -> None:
    payload = {**asdict(posting), "matched_keywords": matched_keywords}
    if payload.get("published_at"):
        payload["published_at"] = posting.published_at.isoformat()

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": request_id,
    }

    last_error: Exception | None = None
    for attempt, delay in enumerate([0, *RETRY_DELAYS_SECONDS]):
        if delay:
            time.sleep(delay)
        try:
            response = httpx.post(
                f"{base_url.rstrip('/')}/compose",
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return
        except httpx.HTTPError as exc:
            last_error = exc

    raise ComposeError(
        f"application-writer /compose failed for {posting.id} after "
        f"{len(RETRY_DELAYS_SECONDS) + 1} attempts: {last_error}"
    )
