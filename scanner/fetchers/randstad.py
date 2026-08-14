"""randstad.de fetcher.

Playwright-based (`ctx.browser`), logs in via the "Mein Randstad"
Bewerberaccount before searching -- confirmed login URL
`/mein-randstad/login/` (found via search, 2026-08-14; the guessed
`/login/` 404s, don't use that). Converted from an earlier httpx-only
version that worked anonymously (see git history) -- switched to a
uniform logged-in-everywhere approach per the candidate's explicit direction,
since anonymous access was only ever verified to return *a* result set,
never confirmed to be the *complete* one a logged-in account sees.

randstad's job search page hydrates from `window.__ROUTE_DATA__ = {...}`
(Elasticsearch-shaped JSON) embedded in the page -- same "parse the
hydration data" approach as freelancermap.py, and unaffected by whether
the page was fetched via httpx or rendered via a real browser (the JSON is
server-rendered either way). `_extract_route_data`/`_to_posting` are
unchanged and still covered by tests/test_randstad.py's fixtures.

**Unverified**: login form field selectors below are a best-effort guess
(generic `get_by_label`/`get_by_placeholder` patterns for
email/password/submit) -- randstad's login page content wasn't
inspectable in detail during implementation (WebFetch returned a
truncated summary, not raw HTML). Needs a live pass once Playwright can
actually run somewhere (real Docker image or cluster, not this project's
bare NixOS dev host -- see the multi-portal-expansion plan notes).
"""

from __future__ import annotations

import json
from datetime import datetime

from scanner.fetchers.base import FetchContext, FetchError
from scanner.models import JobPosting

BASE_URL = "https://www.randstad.de"
_ROUTE_DATA_MARKER = "window.__ROUTE_DATA__"


def fetch(ctx: FetchContext, config: dict) -> list[JobPosting]:
    if ctx.browser is None:
        raise FetchError("randstad fetcher requires a Playwright browser (driver: playwright)")

    credentials = ctx.credentials.get("randstad")
    if not credentials:
        raise FetchError("randstad fetcher requires RANDSTAD_USER/RANDSTAD_PASS credentials")

    search_url = config["search_url"]

    try:
        page = ctx.browser.new_page()
        try:
            _login(page, *credentials)
            page.goto(search_url, timeout=30_000, wait_until="networkidle")
            data = _extract_route_data(page.content())
        finally:
            page.close()
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"randstad fetch failed: {exc}") from exc

    hits = data.get("searchResults", {}).get("hits", {}).get("hits", [])
    return [_to_posting(hit["_source"]) for hit in hits]


def _login(page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/mein-randstad/login/", timeout=30_000, wait_until="networkidle")
    page.get_by_label("E-Mail").fill(username)
    page.get_by_label("Passwort").fill(password)
    page.get_by_role("button", name="Anmelden").click()
    page.wait_for_load_state("networkidle")


def _extract_route_data(html: str) -> dict:
    idx = html.find(_ROUTE_DATA_MARKER)
    if idx == -1:
        return {}
    start = html.find("{", idx)
    depth = 0
    for i, ch in enumerate(html[start:]):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[start : start + i + 1])
    return {}


def _to_posting(source: dict) -> JobPosting:
    info = source.get("JobInformation", {})
    location = source.get("JobLocation", {})
    sanitized = source.get("BlueXSanitized", {})
    client = source.get("ClientInformation", {})
    identity = source.get("JobIdentity", {})
    job_id = source["JobId"]
    dates = source.get("JobDates", {})

    return JobPosting(
        id=f"randstad-{job_id.lower()}",
        portal="randstad",
        title=info.get("Title", ""),
        url=f"{BASE_URL}/jobs/{sanitized.get('Title')}_{sanitized.get('City')}_{job_id.lower()}/",
        posting_text=info.get("Description", ""),
        contract_type=info.get("JobType", "unknown"),
        remote_percent=None,
        company=client.get("ClientName") or identity.get("CompanyName"),
        contact_name=None,
        contact_email=None,
        location=", ".join(filter(None, [location.get("City"), location.get("Region")])) or None,
        published_at=_parse_date(dates.get("DateCreated")),
    )


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
