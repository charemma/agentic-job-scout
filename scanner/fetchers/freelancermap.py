"""freelancermap.de fetcher.

freelancermap's search page is server-rendered React (react-on-rails): the
full result set for the current page is embedded as a JSON blob in a
`<script type="application/json" data-component-name="ProjectSearch">` tag,
not scraped from rendered HTML. That JSON is what this module parses -- it's
the same data the page hydrates from, so it's far less brittle than CSS
selectors against markup that can change with any frontend redesign. This
part is unchanged and still well-tested (see tests/test_freelancermap.py)
regardless of how the page HTML was obtained.

**Login required, confirmed 2026-08-14**: anonymous requests only ever see
page 1 (~22 results) -- `pagenr=2`/`3` silently return page 1 again, gated
by what the site's own frontend strings call a `pagination_forbidden_modal`
("Registrieren Sie sich, um mehr Suchergebnisse zu sehen"). This module now
logs in via Playwright (`ctx.browser`, `FREELANCERMAP_USER`/`_PASS`) before
paginating, so `max_pages` in config.yaml can be raised beyond 1 again.

**Unverified**: the login form selectors below (`get_by_label` on the
visible field text "E-Mail-Adresse oder Benutzername" / "Passwort" /
button "Anmelden") are taken from the page's rendered labels, confirmed via
WebFetch -- but not exercised against a real Chromium session (Playwright
can't launch on this project's bare NixOS dev host, see the
multi-portal-expansion plan notes; the real Docker image installs Chromium's
full apt dependency set and is where this needs a first live run). Whether
a logged-in session actually unlocks real pagination beyond page 1 is
*also* unverified -- worth checking on that first live run before assuming
`max_pages > 1` does anything useful.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape

from bs4 import BeautifulSoup

from scanner.fetchers import base
from scanner.models import JobPosting

BASE_URL = "https://www.freelancermap.de"


def fetch(ctx: base.FetchContext, config: dict) -> list[JobPosting]:
    if ctx.browser is None:
        raise base.FetchError("freelancermap fetcher requires a Playwright browser (driver: playwright)")

    credentials = ctx.credentials.get("freelancermap")
    if not credentials:
        raise base.FetchError("freelancermap fetcher requires FREELANCERMAP_USER/FREELANCERMAP_PASS credentials")

    search_url = config["search_url"]
    max_pages = config.get("max_pages", 3)

    postings: list[JobPosting] = []
    try:
        page = ctx.browser.new_page()
        try:
            _login(page, *credentials)
            for page_num in range(1, max_pages + 1):
                page_url = _with_page(search_url, page_num)
                base.goto(page, page_url)

                raw_items = _extract_results(page.content())
                if not raw_items:
                    break

                postings.extend(_to_posting(item) for item in raw_items)
        finally:
            page.close()
    except base.FetchError:
        raise
    except Exception as exc:
        raise base.FetchError(f"freelancermap fetch failed: {exc}") from exc

    return postings


def _login(page, username: str, password: str) -> None:
    base.goto(page, f"{BASE_URL}/login")
    base.dismiss_cookie_banner(page)
    page.get_by_label("E-Mail-Adresse oder Benutzername").fill(username)
    page.get_by_label("Passwort").fill(password)
    page.get_by_role("button", name="Anmelden").click()
    page.wait_for_load_state("networkidle")


def _with_page(url: str, page: int) -> str:
    if page <= 1:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}pagenr={page}"


def _extract_results(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find(
        "script",
        attrs={"type": "application/json", "data-component-name": "ProjectSearch"},
    )
    if tag is None or not tag.string:
        return []
    data = json.loads(tag.string)
    return data.get("initialResults", [])


def _to_posting(item: dict) -> JobPosting:
    poster = item.get("poster") or {}
    contract = item.get("projectContractType") or {}
    contact_name = " ".join(
        filter(None, [poster.get("firstName"), poster.get("lastName")])
    ) or None

    return JobPosting(
        id=f"freelancermap-{item['id']}",
        portal="freelancermap",
        title=item["title"].strip(),
        url=BASE_URL + item["links"]["project"],
        posting_text=_strip_html(item.get("description", "")),
        contract_type=contract.get("type", "unknown"),
        remote_percent=contract.get("remoteInPercent"),
        company=item.get("company"),
        contact_name=contact_name,
        contact_email=None,  # not exposed without an authenticated/applied session
        location=item.get("city"),
        published_at=_parse_datetime(item.get("created")),
    )


def _strip_html(html: str) -> str:
    text = BeautifulSoup(unescape(html), "html.parser").get_text("\n")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
