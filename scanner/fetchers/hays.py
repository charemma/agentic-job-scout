"""hays.de fetcher.

hays.de's job search (`/jobsuche/stellenangebote-jobs`) is a Liferay portlet
-- genuinely server-rendered HTML, no embedded JSON hydration blob like
freelancermap/randstad. Each result is a `.search__result` block; parsed via
CSS-selector-style BeautifulSoup lookups. No login required for search.

Verified 2026-08-12 against the live **unfiltered** search URL
(`/jobsuche/stellenangebote-jobs`, plain GET, HTTP 200). A hand-constructed
Liferay "updateResults" portlet-action URL (with query params guessed from
the search form's HTML) was tried first and got HTTP 403 -- that action
needs a live `p_auth` CSRF-style token tied to an actual form-submit
session, not something safe to fabricate. `search_url` in config.yaml is
therefore deliberately the plain listing URL; keyword filtering happens
downstream via `matcher.py`, same as it would for any portal without its
own working keyword-query param.

Briefly switched to a Playwright login flow (2026-08-14, "log in
everywhere, uniformly") on the assumption every portal had a simple
email+password applicant login. **Reverted 2026-08-18**: `hays.de/login`
(and the header's own "Login" link) both redirect straight into a SAML SSO
error page ("Unable to process SAML request") -- confirmed live in a
browser, not a guess. Hays has no self-service job-seeker login at all;
that SAML flow is for something else entirely (internal/consultant
access). The parsing logic below was never the problem and is unchanged
from the original anonymous version.

A browser-style `User-Agent` is sent defensively (not confirmed strictly
required -- the plain listing URL returned 200 with `httpx`'s default UA
too during verification, but portals like this are prone to UA-based
bot-checks changing over time).
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from scanner.fetchers.base import FetchContext, FetchError
from scanner.models import JobPosting

BASE_URL = "https://www.hays.de"
_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def fetch(ctx: FetchContext, config: dict) -> list[JobPosting]:
    search_url = config["search_url"]
    try:
        response = ctx.http.get(search_url, headers={"User-Agent": _BROWSER_USER_AGENT}, timeout=30.0)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        raise FetchError(f"hays fetch failed: {exc}") from exc

    return [_to_posting(block) for block in soup.select(".search__result")]


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
