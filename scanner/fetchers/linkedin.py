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

4. **Persisted session, found necessary 2026-08-15**: a fresh username/
   password login on every single cron run was itself the bot signal --
   LinkedIn started throwing a PIN verification checkpoint on essentially
   every automated login attempt. Fix: `scripts/linkedin_login_bootstrap.py`
   does one manual interactive login (non-headless, the candidate clears any
   PIN/2FA by hand) and saves Playwright's `storage_state` (cookies) to a
   file, which becomes a k8s Secret mounted at
   `JOBSCOUT_SESSION_DIR/linkedin.json` (see `Secrets.session_state_path_for`
   in `scanner/config.py`). When that file exists, this fetcher loads it
   into a new browser context instead of calling `_login()` at all -- no
   fresh login, no bot signal, no PIN prompt. If the session has expired
   (redirected back to /login or /checkpoint), this fetcher fails loudly
   rather than falling back to a fresh login, since that fallback is
   exactly the behavior that caused the problem -- expiry needs the candidate to
   re-run the bootstrap script, not a silent retry.

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

from urllib.parse import urlsplit

from scanner.fetchers import base
from scanner.models import JobPosting

BASE_URL = "https://www.linkedin.com"

# A plain desktop Chrome UA -- headless Chromium's default fingerprint
# differs from headed Chrome (older Chromium literally put "HeadlessChrome"
# in the UA; even current versions can still be distinguished via other
# signals). More importantly: scripts/linkedin_login_bootstrap.py
# bootstraps the persisted session in a *headed* browser, but this fetcher
# replays it in a *headless* one (scanner/browser.py always launches
# headless=True) -- without pinning the same UA on both sides, the saved
# session gets replayed under a different fingerprint than the one
# LinkedIn saw when it was created, itself a plausible bot signal. Pin an
# identical, ordinary UA in both places instead of leaving it to
# Playwright's per-mode default.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def fetch(ctx: base.FetchContext, config: dict) -> list[JobPosting]:
    if ctx.browser is None:
        raise base.FetchError("linkedin fetcher requires a Playwright browser (driver: playwright)")

    search_url = config["search_url"]
    session_state_path = ctx.session_state_paths.get("linkedin")

    try:
        if session_state_path is not None:
            context = ctx.browser.new_context(storage_state=str(session_state_path), user_agent=USER_AGENT)
            page = context.new_page()
            try:
                base.goto(page, search_url)
                _check_not_logged_out(page)
                cards = page.query_selector_all("div.base-card, li.jobs-search-results__list-item")
                return [_to_posting(card) for card in cards]
            finally:
                page.close()
                context.close()

        credentials = ctx.credentials.get("linkedin")
        if not credentials:
            raise base.FetchError("linkedin fetcher requires LINKEDIN_USER/LINKEDIN_PASS credentials")

        context = ctx.browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        try:
            _login(page, *credentials)
            base.goto(page, search_url)
            cards = page.query_selector_all("div.base-card, li.jobs-search-results__list-item")
            return [_to_posting(card) for card in cards]
        finally:
            page.close()
            context.close()
    except base.FetchError:
        raise
    except Exception as exc:
        raise base.FetchError(f"linkedin fetch failed: {exc}") from exc


def _looks_logged_out(url: str) -> bool:
    """Path-based, not substring -- LinkedIn's own internal post-login
    redirect hop is /checkpoint/lg/login-submit, a normal part of a
    *successful* login that a naive "login" or "checkpoint" substring
    check misidentifies as a failure (found 2026-08-15: aborted a
    genuinely successful login because "login" matched inside
    "login-submit"). Only a literal /login path, or a /checkpoint path
    other than that known-benign hop, counts as logged out/blocked."""
    path = urlsplit(url).path
    if path.startswith("/login"):
        return True
    return path.startswith("/checkpoint") and path != "/checkpoint/lg/login-submit"


def _check_not_logged_out(page) -> None:
    """A bootstrapped session can expire (LinkedIn invalidates cookies,
    force-logout, etc.) -- landing back on /login or a real /checkpoint
    means the persisted storage_state no longer works. Fail loudly here
    rather than falling back to `_login()`: a fresh login is exactly the
    bot signal that made session persistence necessary in the first place
    (see this module's docstring, point 4). Needs the candidate to re-run
    scripts/linkedin_login_bootstrap.py, not a silent automated retry."""
    if _looks_logged_out(page.url):
        raise base.FetchError(
            "linkedin session expired (redirected to login/checkpoint) -- "
            "re-run scripts/linkedin_login_bootstrap.py and refresh the "
            "jobscout-linkedin-session secret"
        )


def _login(page, username: str, password: str) -> None:
    base.goto(page, f"{BASE_URL}/login")
    base.dismiss_cookie_banner(page)
    page.fill("#username", username)
    page.fill("#password", password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("load")
    if _looks_logged_out(page.url):
        raise base.FetchError("linkedin login hit a verification checkpoint -- needs manual clearance")


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
