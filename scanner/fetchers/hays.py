"""hays.de fetcher.

Playwright-based (`ctx.browser`), logs in before searching -- switched from
an earlier httpx-only version that worked anonymously (see git history) to
a uniform logged-in-everywhere approach per the candidate's explicit direction,
since anonymous access was only ever verified to return *a* result set,
never confirmed to be the *complete* one a logged-in account sees.

hays.de's job search (`/jobsuche/stellenangebote-jobs`) is a Liferay
portlet -- genuinely server-rendered HTML, no embedded JSON hydration blob
like freelancermap/randstad. Each result is a `.search__result` block;
`_to_posting` (CSS-selector-style BeautifulSoup lookups) is unchanged from
the earlier httpx version and still covered by tests/test_hays.py's
fixture, since parsing server-rendered HTML doesn't care whether the page
came from `page.content()` or a raw HTTP response body.

**Unverified, more so than the other converted fetchers**: unlike
freelancermap/randstad, no working self-service login URL for hays.de job
seekers could be confirmed during implementation (search results pointed
at consultant-mediated registration flows, not a simple email+password
form -- Hays' staffing-agency model may route candidates through a
recruiter rather than a self-service portal at all). `/login` below is a
guess matching the other portals' URL convention, not a confirmed path.
If it turns out hays.de has no self-service applicant login, this fetcher
may need to fall back to anonymous access (see git history for that
version) -- don't assume the login path works without checking on the
first live run.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from scanner.fetchers.base import FetchContext, FetchError
from scanner.models import JobPosting

BASE_URL = "https://www.hays.de"


def fetch(ctx: FetchContext, config: dict) -> list[JobPosting]:
    if ctx.browser is None:
        raise FetchError("hays fetcher requires a Playwright browser (driver: playwright)")

    credentials = ctx.credentials.get("hays")
    if not credentials:
        raise FetchError("hays fetcher requires HAYS_USER/HAYS_PASS credentials")

    search_url = config["search_url"]

    try:
        page = ctx.browser.new_page()
        try:
            _login(page, *credentials)
            page.goto(search_url, timeout=30_000, wait_until="networkidle")
            html = page.content()
        finally:
            page.close()
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"hays fetch failed: {exc}") from exc

    soup = BeautifulSoup(html, "html.parser")
    return [_to_posting(block) for block in soup.select(".search__result")]


def _login(page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/login", timeout=30_000, wait_until="networkidle")
    page.get_by_label("E-Mail").fill(username)
    page.get_by_label("Passwort").fill(password)
    page.get_by_role("button", name="Anmelden").click()
    page.wait_for_load_state("networkidle")


def _to_posting(block) -> JobPosting:
    link = block.select_one("a.search__result__link")
    url = link["href"] if link and link.has_attr("href") else ""
    title = _text(block.select_one(".search__result__header__title"))
    location = _text(block.select_one(".search__result__job__attribute__location .info-text"))
    contract_type = _text(block.select_one(".search__result__job__attribute__type .info-text"))
    reference = _text(block.select_one(".search__result__prospectnumber"))
    job_id = reference.replace("Referenznummer:", "").strip() or url.rsplit("-", 1)[-1].rstrip("/")

    return JobPosting(
        id=f"hays-{job_id}",
        portal="hays",
        title=title,
        url=url,
        posting_text=title,  # hays doesn't render a description snippet in the list view
        contract_type=contract_type or "unknown",
        remote_percent=None,
        company=None,  # hays anonymizes the end client in the list view (staffing agency model)
        contact_name=None,
        contact_email=None,
        location=location or None,
        published_at=None,
    )


def _text(tag) -> str:
    return tag.get_text(strip=True) if tag else ""
