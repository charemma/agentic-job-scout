"""Shared types for portal fetchers. Split out from `__init__.py` so portal
modules can import `FetchContext`/`FetchError` without a circular import
(`__init__.py` itself imports every portal module to build the registry)."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

try:
    from playwright.sync_api import Browser
except ImportError:  # pragma: no cover - playwright is an optional/lazy dep at import time in tests
    Browser = object  # type: ignore[assignment,misc]


@dataclass
class FetchContext:
    """Everything a fetcher might need. Fetchers use only what they need --
    an httpx-only portal never touches `browser`/`credentials`."""

    http: httpx.Client
    browser: "Browser | None"
    credentials: dict[str, tuple[str, str] | None]


class FetchError(Exception):
    """Raised by a fetcher on any failure (HTTP, browser automation, login,
    unexpected page shape). `main.py` catches this uniformly per portal, so
    one broken/blocked portal never aborts the rest of a scan run."""


# Cookie-consent banners (OneTrust, Cookiebot, generic) sit on top of the
# page and intercept clicks -- confirmed live 2026-08-14 against
# freelancermap (OneTrust), where it silently retried the login button click
# for 60+ attempts until timing out. Every portal's `_login()` should call
# this right after the initial `page.goto()`, before interacting with the
# login form. Best-effort: tries the most common consent-tool button
# selectors with a short timeout each, swallows failures (no banner, already
# dismissed via a cookie, or an unrecognized consent tool -- none of those
# should block login).
_COOKIE_CONSENT_SELECTORS = [
    "#onetrust-accept-btn-handler",  # OneTrust, by far the most common on German sites
    "#CybotCookiebotDialogBodyButtonAccept",  # Cookiebot
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",  # Cookiebot, layered consent variant
    "button:has-text('Alle akzeptieren')",
    "button:has-text('Alle Cookies akzeptieren')",
    "button:has-text('Accept all')",
]


def dismiss_cookie_banner(page, timeout_ms: int = 3000) -> None:
    for selector in _COOKIE_CONSENT_SELECTORS:
        try:
            page.click(selector, timeout=timeout_ms)
            return
        except Exception:
            continue
