"""linkedin.com fetcher.

**ToS / bot-detection risk, read before touching this file**: LinkedIn
actively detects and can suspend accounts for automated access. Mitigations
in place, agreed with the candidate:

1. Real Chromium via Playwright (`ctx.browser`), not raw HTTP -- looks like
   an actual browser session, not a scraper.
2. This fetcher only makes sense running from `home-node` (home/residential
   IP via Tailscale-joined k3s worker), never the VPS -- a login from a
   previously-unseen datacenter IP is one of the strongest bot signals,
   independent of request frequency. See `k8s/scanner-cronjob.yaml`'s
   `nodeSelector: {home-network: "true"}`.
3. Capped at ~4x/day (`k8s/scanner-cronjob.yaml` schedule), per the candidate's
   explicit cadence.

None of this eliminates the risk -- LinkedIn can still challenge/verify an
unfamiliar automated login (2FA prompt, CAPTCHA). A failed run here should
be treated as "needs the candidate to manually clear a verification prompt," not a
bug to silently retry aggressively.

**Unverified**: login form and job-search-result selectors below follow
LinkedIn's long-standing public markup conventions (`base-card`,
`base-search-card__title`, etc., used in most LinkedIn scraping writeups),
but could not be confirmed against a live authenticated session during
implementation (no interactive login/2FA available in this environment).
Needs a live run + selector check before being trusted, same as solcom.py.

`f_WT=2` is LinkedIn's own documented query param for "Remote" work type --
used here to push remote-filtering to the portal itself where possible,
on top of the downstream LLM remote-only enforcement.
"""

from __future__ import annotations

from scanner.fetchers.base import FetchContext, FetchError
from scanner.models import JobPosting

BASE_URL = "https://www.linkedin.com"


def fetch(ctx: FetchContext, config: dict) -> list[JobPosting]:
    if ctx.browser is None:
        raise FetchError("linkedin fetcher requires a Playwright browser (driver: playwright)")

    credentials = ctx.credentials.get("linkedin")
    if not credentials:
        raise FetchError("linkedin fetcher requires LINKEDIN_USER/LINKEDIN_PASS credentials")

    search_url = config["search_url"]

    try:
        page = ctx.browser.new_page()
        try:
            _login(page, *credentials)
            page.goto(search_url, timeout=30_000, wait_until="networkidle")
            cards = page.query_selector_all("div.base-card, li.jobs-search-results__list-item")
            return [_to_posting(card) for card in cards]
        finally:
            page.close()
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"linkedin fetch failed: {exc}") from exc


def _login(page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/login", timeout=30_000, wait_until="networkidle")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    if "checkpoint" in page.url or "challenge" in page.url:
        raise FetchError("linkedin login hit a verification checkpoint -- needs manual clearance")


def _to_posting(card) -> JobPosting:
    title_el = card.query_selector(".base-search-card__title, h3")
    company_el = card.query_selector(".base-search-card__subtitle, h4")
    location_el = card.query_selector(".job-search-card__location")
    link_el = card.query_selector("a.base-card__full-link, a")

    title = title_el.inner_text().strip() if title_el else ""
    url = (link_el.get_attribute("href") or "").split("?")[0] if link_el else ""
    job_id = url.rstrip("/").rsplit("-", 1)[-1] or title

    return JobPosting(
        id=f"linkedin-{job_id}",
        portal="linkedin",
        title=title,
        url=url,
        posting_text=card.inner_text().strip(),
        contract_type="permanent",  # LinkedIn's default job search skews permanent roles
        remote_percent=None,
        company=company_el.inner_text().strip() if company_el else None,
        contact_name=None,
        contact_email=None,
        location=location_el.inner_text().strip() if location_el else None,
        published_at=None,
    )
