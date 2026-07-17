"""freelancermap.de fetcher.

freelancermap's search page is server-rendered React (react-on-rails): the
full result set for the current page is embedded as a JSON blob in a
`<script type="application/json" data-component-name="ProjectSearch">` tag,
not scraped from rendered HTML. That JSON is what this module parses -- it's
the same data the page hydrates from, so it's far less brittle than CSS
selectors against markup that can change with any frontend redesign.

Verified 2026-07-17 against the live search URL the candidate provided: the search
itself requires no login (plain GET, HTTP 200, full result JSON present).
`hideAppliedProjects` is accepted as a query param but its effect without an
authenticated session is unverified -- if login turns out to matter later
(e.g. for `hideAppliedProjects` or contact details), add a `_login()` helper
here using `config["credentials"]`; the config shape already has a slot for
it (see `k8s/secrets.md`), but no login flow has been implemented or tested
yet -- do not assume one exists.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape

import httpx
from bs4 import BeautifulSoup

from scanner.models import JobPosting

BASE_URL = "https://www.freelancermap.de"


def fetch(client: httpx.Client, config: dict) -> list[JobPosting]:
    search_url = config["search_url"]
    max_pages = config.get("max_pages", 3)

    postings: list[JobPosting] = []
    for page in range(1, max_pages + 1):
        page_url = _with_page(search_url, page)
        response = client.get(page_url, timeout=30.0)
        response.raise_for_status()

        raw_items = _extract_results(response.text)
        if not raw_items:
            break

        postings.extend(_to_posting(item) for item in raw_items)

    return postings


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
        title=item["title"],
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
