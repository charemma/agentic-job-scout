"""xing.com fetcher.

xing.com job search is Playwright-based (`ctx.browser`) for the same reason
as linkedin.py -- a login-gated, JS-heavy search that a raw `httpx` GET
can't meaningfully render. Xing is generally more permissive of automated
access than LinkedIn, but the same mitigations apply: real Chromium, run
from `home-node` (home IP), capped frequency (see linkedin.py's docstring for
the full rationale, shared by both fetchers).

**Persisted session, same as linkedin.py, adopted 2026-08-18**: the
original `_login()` guessed `https://www.xing.com/login`, which is a plain
404 -- Xing's actual login lives on a separate subdomain,
`https://login.xing.com/`, a JS SPA with no server-rendered form (so its
field selectors can't be inspected via a raw HTTP GET the way solcom's
Drupal form could). Rather than guess selectors on a page that couldn't be
directly verified without logging a real account out, this fetcher adopts
LinkedIn's persisted-session pattern outright:
`scripts/xing_login_bootstrap.py` does one manual interactive login and
saves Playwright's `storage_state`, which becomes a k8s Secret mounted at
`JOBSCOUT_SESSION_DIR/xing.json` (see `Secrets.session_state_path_for` in
`scanner/config.py`). When that file exists, this fetcher loads it into a
new browser context instead of calling `_login()` at all. `_login()` below
is an unverified best-effort fallback only, same caveat as linkedin.py's --
rarely exercised once a session is bootstrapped.

**Result-card selectors verified against a live authenticated session,
2026-08-18** (checked the search query itself first: `999+ jobs found`
for the existing `"platform engineering" OR "ai security"` query, so the
query syntax was never the problem here, only the login step blocking
every run before it ever got this far). Real per-card container is
`[data-testid="job-search-result"]` (an `<article>`); title is
`[data-testid="job-teaser-list-title"]`; company is the card's first `<p>`
(checked consistent across 6 live cards); location is
`[class*="multi-location-display"]` (a semantic class-name fragment, not
one of Xing's hashed styled-components classes, so more likely to survive
a frontend rebuild than an exact class match would).
"""

from __future__ import annotations

from scanner.fetchers import base
from scanner.models import JobPosting

BASE_URL = "https://www.xing.com"
LOGIN_URL = "https://login.xing.com/"

_RESULT_SELECTOR = '[data-testid="job-search-result"]'
_TITLE_SELECTOR = '[data-testid="job-teaser-list-title"]'
_LOCATION_SELECTOR = '[class*="multi-location-display"]'


def fetch(ctx: base.FetchContext, config: dict) -> list[JobPosting]:
    if ctx.browser is None:
        raise base.FetchError("xing fetcher requires a Playwright browser (driver: playwright)")

    search_url = config["search_url"]
    session_state_path = ctx.session_state_paths.get("xing")

    try:
        if session_state_path is not None:
            context = ctx.browser.new_context(storage_state=str(session_state_path))
            page = context.new_page()
            try:
                base.goto(page, search_url)
                _check_not_logged_out(page)
                cards = page.query_selector_all(_RESULT_SELECTOR)
                return [_to_posting(card) for card in cards]
            finally:
                page.close()
                context.close()

        credentials = ctx.credentials.get("xing")
        if not credentials:
            raise base.FetchError("xing fetcher requires XING_USER/XING_PASS credentials")

        context = ctx.browser.new_context()
        page = context.new_page()
        try:
            _login(page, *credentials)
            base.goto(page, search_url)
            cards = page.query_selector_all(_RESULT_SELECTOR)
            return [_to_posting(card) for card in cards]
        finally:
            page.close()
            context.close()
    except base.FetchError:
        raise
    except Exception as exc:
        raise base.FetchError(f"xing fetch failed: {exc}") from exc


def _looks_logged_out(url: str) -> bool:
    return url.startswith(LOGIN_URL)


def _check_not_logged_out(page) -> None:
    """A bootstrapped session can expire -- landing back on login.xing.com
    means the persisted storage_state no longer works. Fail loudly rather
    than falling back to `_login()`, same rationale as linkedin.py: a fresh
    login is the exact behavior session persistence exists to avoid."""
    if _looks_logged_out(page.url):
        raise base.FetchError(
            "xing session expired (redirected to login) -- re-run "
            "scripts/xing_login_bootstrap.py and refresh the "
            "jobscout-xing-session secret"
        )


def _login(page, username: str, password: str) -> None:
    """Unverified fallback -- see module docstring. Xing's login is a JS
    SPA on a separate subdomain with no server-rendered form to inspect
    without logging a real account out first, so these selectors are a
    best-effort guess, not a confirmed live check like the rest of this
    module. Exercised only if no persisted session has been bootstrapped."""
    base.goto(page, LOGIN_URL)
    base.dismiss_cookie_banner(page)
    page.fill('input[type="email"], input[name="username"]', username)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("load")
    if _looks_logged_out(page.url):
        raise base.FetchError("xing login failed or hit a verification challenge -- needs manual clearance")


def _to_posting(card) -> JobPosting:
    title_el = card.query_selector(_TITLE_SELECTOR)
    location_el = card.query_selector(_LOCATION_SELECTOR)
    company_el = card.query_selector("p")
    link_el = card.query_selector("a[href]")

    title = title_el.inner_text().strip() if title_el else ""
    href = link_el.get_attribute("href") if link_el else ""
    href_path = (href or "").split("?")[0]
    url = href_path if href_path.startswith("http") else f"{BASE_URL}{href_path}" if href_path else ""
    job_id = url.rstrip("/").rsplit("-", 1)[-1] or title

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
