"""solcom.de fetcher.

solcom.de's Projektbörse sits behind Cloudflare bot-protection -- a plain
`httpx` GET returns HTTP 403 with a Cloudflare interstitial ("Kundeninformation"
title page), verified 2026-08-12. A real browser (Playwright) is required
here not because of a login wall on the search itself, but to get past that
challenge -- Cloudflare's JS challenge generally passes for a real Chromium
session, especially from a residential IP (this fetcher only makes sense
running from `home-node`, same rationale as xing/linkedin).

Result-card and login selectors verified live 2026-08-18 (a real browser
sails straight through the Cloudflare challenge, no interstitial hit):
`search_url` redirects to `/fuer-freelancer/projektliste`, where each
result is an `article.project-offer-card` -- confirmed by cross-checking
the count (335) against the page's own "335 Treffer" label. Title/link is
`a.project-offer-card__title-link` inside the card's `h2`. The four
`.project-offer-card__meta-item` `<li>`s are always
[duration, start_date, location, contract_type] in that fixed order
(checked across multiple cards); description text is
`.project-offer-card__description`.

Login (`ctx.credentials["solcom"]`) is wired but its effect (does it change
what the anonymous search shows?) is still unverified -- same open question
as freelancermap's original login slot. The login form itself is a Drupal
user-login block (`#edit-name`/`#edit-pass`/`#edit-submit`), confirmed live
2026-08-18, replacing a guessed `input[type="email"]` selector that never
matched (the username field is `type="text"`, not `"email"`).
"""

from __future__ import annotations

from scanner.fetchers import base
from scanner.models import JobPosting

BASE_URL = "https://www.solcom.de"
RESULT_SELECTOR = "article.project-offer-card"
TITLE_LINK_SELECTOR = "a.project-offer-card__title-link"
META_ITEM_SELECTOR = ".project-offer-card__meta-item"
DESCRIPTION_SELECTOR = ".project-offer-card__description"


def fetch(ctx: base.FetchContext, config: dict) -> list[JobPosting]:
    if ctx.browser is None:
        raise base.FetchError("solcom fetcher requires a Playwright browser (driver: playwright)")

    search_url = config["search_url"]
    credentials = ctx.credentials.get("solcom")

    try:
        page = ctx.browser.new_page()
        try:
            if credentials:
                _login(page, *credentials)
            base.goto(page, search_url)
            cards = page.query_selector_all(RESULT_SELECTOR)
            return [_to_posting(card) for card in cards]
        finally:
            page.close()
    except base.FetchError:
        raise
    except Exception as exc:
        raise base.FetchError(f"solcom fetch failed: {exc}") from exc


def _login(page, username: str, password: str) -> None:
    base.goto(page, f"{BASE_URL}/de/projektportal/login")
    base.dismiss_cookie_banner(page)
    # Drupal login form (id="edit-name"/"edit-pass") -- confirmed live
    # 2026-08-18, replacing a guessed input[type="email"] selector that
    # never matched (the username field is type="text", not "email").
    page.fill("#edit-name", username)
    page.fill("#edit-pass", password)
    page.click("#edit-submit")
    page.wait_for_load_state("networkidle")


def _to_posting(card) -> JobPosting:
    link_el = card.query_selector(TITLE_LINK_SELECTOR)
    description_el = card.query_selector(DESCRIPTION_SELECTOR)
    meta_items = [item.inner_text().strip() for item in card.query_selector_all(META_ITEM_SELECTOR)]
    # fixed order: [duration, start_date, location, contract_type]
    location = meta_items[2] if len(meta_items) > 2 else None

    title = link_el.inner_text().strip() if link_el else ""
    href = link_el.get_attribute("href") if link_el else ""
    url = href if href.startswith("http") else f"{BASE_URL}{href}" if href else ""
    job_id = url.rstrip("/").rsplit("/", 1)[-1] or title

    return JobPosting(
        id=f"solcom-{job_id}",
        portal="solcom",
        title=title,
        url=url,
        posting_text=description_el.inner_text().strip() if description_el else card.inner_text().strip(),
        contract_type="contracting",  # solcom is freelance/contracting-only
        remote_percent=None,
        company=None,
        contact_name=None,
        contact_email=None,
        location=location,
        published_at=None,
    )
