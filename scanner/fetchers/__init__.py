"""Portal fetcher registry.

Each portal is a plain module exposing a single `fetch(ctx, config)`
function -- no shared base class needed, just a common call signature. To
add a new portal: write `<portal>.py` with a `fetch` function matching
`FetcherFn`, then register it below. Nothing else in the scanner needs to
change (Open/Closed).

All portals log in via `ctx.browser` (a lazily-launched Playwright
`Browser`, see `scanner/browser.py` -- only paid for if at least one
enabled portal declares `driver: playwright`, which as of 2026-08-14 is
every portal, per the candidate's explicit "log in everywhere, uniformly" decision
-- see individual fetcher docstrings for why anonymous access was dropped
even where it technically returned *a* result set). `ctx.http` (a plain
`httpx.Client`) is kept on `FetchContext` for any future portal that
genuinely has no login-gated content, but nothing currently uses it.
"""

from __future__ import annotations

from collections.abc import Callable

from scanner.fetchers import freelance, freelancermap, hays, linkedin, randstad, solcom, xing
from scanner.fetchers.base import FetchContext, FetchError
from scanner.models import JobPosting

__all__ = ["FetchContext", "FetchError", "FetcherFn", "REGISTRY", "enabled_fetchers", "needs_playwright"]

FetcherFn = Callable[[FetchContext, dict], list[JobPosting]]

REGISTRY: dict[str, FetcherFn] = {
    "freelancermap": freelancermap.fetch,
    "xing": xing.fetch,
    "linkedin": linkedin.fetch,
    "solcom": solcom.fetch,
    "randstad": randstad.fetch,
    "hays": hays.fetch,
    "freelance": freelance.fetch,
}


def enabled_fetchers(config: dict) -> list[tuple[str, FetcherFn]]:
    """Return (portal_name, fetch_fn) pairs for portals marked enabled in config."""
    portals = config.get("portals", {})
    return [
        (name, REGISTRY[name])
        for name, portal_config in portals.items()
        if portal_config.get("enabled") and name in REGISTRY
    ]


def needs_playwright(config: dict) -> bool:
    """True if any enabled portal declares `driver: playwright`."""
    portals = config.get("portals", {})
    return any(
        portal_config.get("enabled") and portal_config.get("driver") == "playwright"
        for portal_config in portals.values()
    )
