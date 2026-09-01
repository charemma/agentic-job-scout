"""HTTP client for the application-writer service.

Bounded retry/backoff (no tenacity dependency -- this is the only call site
that needs it, a manual loop is simpler than pulling in a library for one
use). A failure here must never crash the whole scanner run: callers catch
`ComposeError`/`AssessError` and move on to the next posting, leaving this
one to be retried on the next scan tick (dedup in store.py only marks a
posting "seen" once compose succeeds).
"""

from __future__ import annotations

import time
from dataclasses import asdict

import httpx

from scanner.models import JobPosting

RETRY_DELAYS_SECONDS = [1, 4, 16]
# application-writer's claude_cli.py shells out to `claude -p`
# (subscription-billed CLI, not the direct API) with its own 180s subprocess
# timeout per completion call -- noticeably slower and more variable than a
# raw API call was. Set comfortably above that so the scanner doesn't give
# up on a /assess call that's still legitimately running server-side
# (/assess is now up to two completions: analyse + blind match scoring).
# /compose chains up to 7 completions (analyse, write, review, blind match
# eval, plus one bounded write+review+eval improvement round) sequentially,
# so it gets its own, much larger timeout.
REQUEST_TIMEOUT_SECONDS = 400.0
COMPOSE_TIMEOUT_SECONDS = 1500.0


class ComposeError(RuntimeError):
    pass


class AssessError(RuntimeError):
    pass


def _posting_payload(posting: JobPosting, matched_keywords: list[str]) -> dict:
    payload = {**asdict(posting), "matched_keywords": matched_keywords}
    if payload.get("published_at"):
        payload["published_at"] = posting.published_at.isoformat()
    return payload


def _post_with_retry(
    url: str,
    payload: dict,
    headers: dict,
    error_cls: type[Exception],
    what: str,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
) -> dict:
    last_error: Exception | None = None
    for attempt, delay in enumerate([0, *RETRY_DELAYS_SECONDS]):
        if delay:
            time.sleep(delay)
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            last_error = exc

    raise error_cls(f"{what} failed after {len(RETRY_DELAYS_SECONDS) + 1} attempts: {last_error}")


def assess_fit(
    base_url: str,
    token: str,
    posting: JobPosting,
    matched_keywords: list[str],
    request_id: str,
) -> dict:
    """Cheap LLM fit-check (no drafting/PDF build) -- returns {fit_level, summary}."""
    payload = _posting_payload(posting, matched_keywords)
    headers = {"Authorization": f"Bearer {token}", "X-Request-ID": request_id}
    return _post_with_retry(
        f"{base_url.rstrip('/')}/assess", payload, headers, AssessError, f"assess for {posting.id}"
    )


def trigger_compose(
    base_url: str,
    token: str,
    posting: JobPosting,
    matched_keywords: list[str],
    request_id: str,
) -> None:
    payload = _posting_payload(posting, matched_keywords)
    headers = {"Authorization": f"Bearer {token}", "X-Request-ID": request_id}
    _post_with_retry(
        f"{base_url.rstrip('/')}/compose",
        payload,
        headers,
        ComposeError,
        f"application-writer /compose for {posting.id}",
        timeout=COMPOSE_TIMEOUT_SECONDS,
    )
