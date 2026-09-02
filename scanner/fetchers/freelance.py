"""freelance.de fetcher.

Playwright-based (`ctx.browser`), login via `FREELANCE_USER`/`FREELANCE_PASS`
-- confirmed login URL `/login.php` (found via search, 2026-08-14). New
portal, not previously implemented.

**Unverified**: the search results page (`/projekte.html`) returned only a
sparse navigation shell (~16KB, no listing markup, no embedded JSON) to a
plain `curl`/WebFetch request -- likely requires an authenticated session
or JS-driven client-side rendering to show real results, neither of which
a raw HTTP request exercises. `RESULT_SELECTOR` etc. below are a
best-effort guess (same style as solcom.py's), not confirmed against a
real logged-in page. Needs a live selector-verification pass (open the
search URL in a real authenticated browser session, `page.content()` it,
adjust selectors) before trusting its output.

**Login field fixed, 2026-09-02**: `_login()` was guessing a standalone
"E-Mail" label, which timed out on every run -- the real login form has a
single combined field labeled "Nutzername/E-Mail", not two separate ones.
Matched via a case-insensitive regex on "e-mail" rather than the exact
combined string, so a future label rewording is less likely to break it
again the same way.
"""

from __future__ import annotations

import re

from scanner.fetchers import base
from scanner.models import JobPosting

BASE_URL = "https://www.freelance.de"
RESULT_SELECTOR = "article.project, div.project-item, li.project-list-item"
TITLE_SELECTOR = "h2, h3, .project-title"
LOCATION_SELECTOR = ".project-location, .location"
LINK_SELECTOR = "a"


def fetch(ctx: base.FetchContext, config: dict) -> list[JobPosting]:
    if ctx.browser is None:
        raise base.FetchError("freelance fetcher requires a Playwright browser (driver: playwright)")

    credentials = ctx.credentials.get("freelance")
    if not credentials:
        raise base.FetchError("freelance fetcher requires FREELANCE_USER/FREELANCE_PASS credentials")

    search_url = config["search_url"]

    try:
        page = ctx.browser.new_page()
        try:
            _login(page, *credentials)
            base.goto(page, search_url)
            cards = page.query_selector_all(RESULT_SELECTOR)
            return [_to_posting(card) for card in cards]
        finally:
            page.close()
    except base.FetchError:
        raise
    except Exception as exc:
        raise base.FetchError(f"freelance fetch failed: {exc}") from exc


def _login(page, username: str, password: str) -> None:
    base.goto(page, f"{BASE_URL}/login.php")
    base.dismiss_cookie_banner(page)
    page.get_by_label(re.compile("e-mail", re.IGNORECASE)).fill(username)
    page.get_by_label("Passwort").fill(password)
    page.get_by_role("button", name="Anmelden").click()
    page.wait_for_load_state("networkidle")


def _to_posting(card) -> JobPosting:
    title_el = card.query_selector(TITLE_SELECTOR)
    link_el = card.query_selector(LINK_SELECTOR)
    location_el = card.query_selector(LOCATION_SELECTOR)

    title = title_el.inner_text().strip() if title_el else ""
    href = link_el.get_attribute("href") if link_el else ""
    url = href if (href or "").startswith("http") else f"{BASE_URL}{href}" if href else ""
    job_id = url.rstrip("/").rsplit("/", 1)[-1] or title

    return JobPosting(
        id=f"freelance-{job_id}",
        portal="freelance",
        title=title,
        url=url,
        posting_text=card.inner_text().strip(),
        contract_type="contracting",  # freelance.de is freelance/contracting-only
        remote_percent=None,
        company=None,
        contact_name=None,
        contact_email=None,
        location=location_el.inner_text().strip() if location_el else None,
        published_at=None,
    )
