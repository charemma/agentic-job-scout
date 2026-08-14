"""solcom.de fetcher.

solcom.de's Projektbörse sits behind Cloudflare bot-protection -- a plain
`httpx` GET returns HTTP 403 with a Cloudflare interstitial ("Kundeninformation"
title page), verified 2026-08-12. A real browser (Playwright) is required
here not because of a login wall on the search itself, but to get past that
challenge -- Cloudflare's JS challenge generally passes for a real Chromium
session, especially from a residential IP (this fetcher only makes sense
running from `home-node`, same rationale as xing/linkedin).

**Unverified**: the exact result-card selectors below are a best-effort
guess (solcom's markup could not be inspected directly -- Cloudflare blocked
every fetch attempt during implementation, including from a script). Treat
this fetcher as needing a live selector-verification pass (open the search
URL in a real browser, `page.content()` it, adjust `RESULT_SELECTOR` etc.)
before trusting its output -- do not assume it works untested, unlike
freelancermap/randstad/hays which were verified against live responses.

Login (`ctx.credentials["solcom"]`) is wired but its effect (does it change
what the anonymous search shows?) is also unverified -- same open question
as freelancermap's original login slot.
"""

from __future__ import annotations

from scanner.fetchers.base import FetchContext, FetchError, dismiss_cookie_banner
from scanner.models import JobPosting

BASE_URL = "https://www.solcom.de"
RESULT_SELECTOR = "article.project-teaser, div.project-list-item"
TITLE_SELECTOR = "h2, h3, .project-teaser__title"
LOCATION_SELECTOR = ".project-teaser__location, .location"
LINK_SELECTOR = "a"


def fetch(ctx: FetchContext, config: dict) -> list[JobPosting]:
    if ctx.browser is None:
        raise FetchError("solcom fetcher requires a Playwright browser (driver: playwright)")

    search_url = config["search_url"]
    credentials = ctx.credentials.get("solcom")

    try:
        page = ctx.browser.new_page()
        try:
            if credentials:
                _login(page, *credentials)
            page.goto(search_url, timeout=30_000, wait_until="networkidle")
            cards = page.query_selector_all(RESULT_SELECTOR)
            return [_to_posting(card) for card in cards]
        finally:
            page.close()
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"solcom fetch failed: {exc}") from exc


def _login(page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/de/projektportal/login", timeout=30_000, wait_until="networkidle")
    dismiss_cookie_banner(page)
    page.fill('input[type="email"], input[name*="user" i]', username)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def _to_posting(card) -> JobPosting:
    title_el = card.query_selector(TITLE_SELECTOR)
    link_el = card.query_selector(LINK_SELECTOR)
    location_el = card.query_selector(LOCATION_SELECTOR)

    title = title_el.inner_text().strip() if title_el else ""
    href = link_el.get_attribute("href") if link_el else ""
    url = href if href.startswith("http") else f"{BASE_URL}{href}" if href else ""
    job_id = url.rstrip("/").rsplit("/", 1)[-1] or title

    return JobPosting(
        id=f"solcom-{job_id}",
        portal="solcom",
        title=title,
        url=url,
        posting_text=card.inner_text().strip(),
        contract_type="contracting",  # solcom is freelance/contracting-only
        remote_percent=None,
        company=None,
        contact_name=None,
        contact_email=None,
        location=location_el.inner_text().strip() if location_el else None,
        published_at=None,
    )
