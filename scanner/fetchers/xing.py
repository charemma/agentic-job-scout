"""xing.com fetcher.

xing.com job search is Playwright-based (`ctx.browser`) for the same reason
as linkedin.py -- a login-gated, JS-heavy search that a raw `httpx` GET
can't meaningfully render. Xing is generally more permissive of automated
access than LinkedIn, but the same mitigations apply: real Chromium, run
from `home-node` (home IP), capped frequency (see linkedin.py's docstring for
the full rationale, shared by both fetchers).

**Unverified**: login form and result-card selectors below are a
best-effort guess based on Xing's general markup conventions
(`data-testid` hooks), not confirmed against a live authenticated session
during implementation. Needs a live run + selector check, same caveat as
solcom.py/linkedin.py.
"""

from __future__ import annotations

from scanner.fetchers.base import FetchContext, FetchError
from scanner.models import JobPosting

BASE_URL = "https://www.xing.com"


def fetch(ctx: FetchContext, config: dict) -> list[JobPosting]:
    if ctx.browser is None:
        raise FetchError("xing fetcher requires a Playwright browser (driver: playwright)")

    credentials = ctx.credentials.get("xing")
    if not credentials:
        raise FetchError("xing fetcher requires XING_USER/XING_PASS credentials")

    search_url = config["search_url"]

    try:
        page = ctx.browser.new_page()
        try:
            _login(page, *credentials)
            page.goto(search_url, timeout=30_000, wait_until="networkidle")
            cards = page.query_selector_all('[data-testid="job-search-result"], article')
            return [_to_posting(card) for card in cards]
        finally:
            page.close()
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"xing fetch failed: {exc}") from exc


def _login(page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/login", timeout=30_000, wait_until="networkidle")
    page.fill('input[type="email"], input[name="username"]', username)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def _to_posting(card) -> JobPosting:
    title_el = card.query_selector('[data-testid="job-search-result-title"], h2, h3')
    company_el = card.query_selector('[data-testid="job-search-result-company"], .company')
    location_el = card.query_selector('[data-testid="job-search-result-location"], .location')
    link_el = card.query_selector("a")

    title = title_el.inner_text().strip() if title_el else ""
    href = link_el.get_attribute("href") if link_el else ""
    url = href if (href or "").startswith("http") else f"{BASE_URL}{href}" if href else ""
    job_id = url.rstrip("/").rsplit("/", 1)[-1] or title

    return JobPosting(
        id=f"xing-{job_id}",
        portal="xing",
        title=title,
        url=url,
        posting_text=card.inner_text().strip(),
        contract_type="permanent",  # Xing's default job search skews permanent roles
        remote_percent=None,
        company=company_el.inner_text().strip() if company_el else None,
        contact_name=None,
        contact_email=None,
        location=location_el.inner_text().strip() if location_el else None,
        published_at=None,
    )
