"""Lazy Playwright launch. Every portal logs in via a browser session now
(driver: playwright, uniformly, decided 2026-08-14 -- see fetchers/__init__.py),
so in practice this always launches when any portal is enabled. Kept
lazy/guarded by `needs_playwright()` anyway rather than launching
unconditionally: a future portal genuinely not needing a browser (or all
portals disabled for a debugging run) shouldn't pay Chromium startup cost,
and the `playwright` import itself is deferred into the function body so
`scanner.main` stays importable on a host where Playwright's native deps
aren't installed (e.g. local dev without the Docker image's apt-installed
Chromium libs), as long as nothing enabled actually needs it. Launched
headless; the scanner CronJob itself runs pinned to a home-network node
(see k8s/scanner-cronjob.yaml) -- this module is only responsible for the
browser process, not the network path.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from scanner.fetchers import needs_playwright

if TYPE_CHECKING:
    from playwright.sync_api import Browser


@contextmanager
def maybe_playwright(config: dict) -> Iterator["Browser | None"]:
    if not needs_playwright(config):
        yield None
        return

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            browser.close()
