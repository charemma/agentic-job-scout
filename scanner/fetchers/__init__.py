"""Portal fetcher registry.

Each portal is a plain module exposing a single `fetch(client, config)`
function -- no shared base class needed, just a common call signature. To
add a new portal: write `<portal>.py` with a `fetch` function matching
`FetcherFn`, then register it below. Nothing else in the scanner needs to
change (Open/Closed).
"""

from __future__ import annotations

from collections.abc import Callable

import httpx

from scanner.models import JobPosting
from scanner.fetchers import freelancermap

FetcherFn = Callable[[httpx.Client, dict], list[JobPosting]]

REGISTRY: dict[str, FetcherFn] = {
    "freelancermap": freelancermap.fetch,
}


def enabled_fetchers(config: dict) -> list[tuple[str, FetcherFn]]:
    """Return (portal_name, fetch_fn) pairs for portals marked enabled in config."""
    portals = config.get("portals", {})
    return [
        (name, REGISTRY[name])
        for name, portal_config in portals.items()
        if portal_config.get("enabled") and name in REGISTRY
    ]
