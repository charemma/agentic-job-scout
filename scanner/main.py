"""Scanner CronJob entrypoint: fetch -> match -> assess -> notify -> compose.

Runs to completion and exits (k8s CronJob), once per invocation. A failure
in one portal's fetcher, in assessing fit for one posting, in publishing
the ntfy notification, or in triggering application-writer's /compose, is
logged and does not abort the rest of the run.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import httpx

from scanner import store
from scanner.application_writer_client import AssessError, ComposeError, assess_fit, trigger_compose
from scanner.browser import maybe_playwright
from scanner.config import Secrets, load_config
from scanner.fetchers import FetchError, enabled_fetchers
from scanner.fetchers.base import FetchContext
from scanner.matcher import match
from scanner.notifier import notify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("jobscout.scanner")

# fit_level values (from application-writer's /assess and /compose), ordered
# weakest to strongest. min_fit_level in config.yaml sets the noise-reduction
# bar for triggering a notification + full /compose draft.
_FIT_LEVEL_RANK = {"schwach": 0, "solide": 1, "stark": 2}


def run() -> None:
    config = load_config()
    secrets = Secrets.from_env()

    repo_path = store.sync_applications_repo(
        config["applications_repo"]["clone_url"],
        secrets.applications_repo_token,
        Path(config["applications_repo"]["local_path"]),
    )

    criteria = config["criteria"]
    min_fit_rank = _FIT_LEVEL_RANK.get(criteria.get("min_fit_level", "solide"), 1)
    compose_enabled = criteria.get("compose_enabled", True)

    fetched_count = 0
    matched_count = 0
    assessed_count = 0
    triggered_count = 0
    # In-run safety net against duplicate postings -- store.already_seen()
    # only checks jobscout-applications' committed state, which never
    # updates while compose_enabled=false, and a single fetcher can itself
    # return duplicate entries (e.g. a login-gated portal silently
    # re-serving page 1 for later pages). Cheap, always correct, no reason
    # not to have it regardless of the root cause on any given portal.
    seen_ids: set[str] = set()

    with httpx.Client(follow_redirects=True) as http_client, maybe_playwright(config) as browser:
        ctx_credentials = {
            portal_name: secrets.credentials_for(portal_name) for portal_name in config.get("portals", {})
        }
        ctx_session_states = {
            portal_name: secrets.session_state_path_for(portal_name) for portal_name in config.get("portals", {})
        }
        ctx = FetchContext(
            http=http_client, browser=browser, credentials=ctx_credentials, session_state_paths=ctx_session_states
        )

        for portal_name, fetch in enabled_fetchers(config):
            try:
                postings = fetch(ctx, config["portals"][portal_name])
            except FetchError as exc:
                log.error("fetcher %s failed: %s", portal_name, exc)
                continue

            fetched_count += len(postings)
            log.info("fetched %d postings from %s", len(postings), portal_name)

            for posting in postings:
                if posting.id in seen_ids:
                    continue
                seen_ids.add(posting.id)

                if store.already_seen(repo_path, posting.id):
                    continue

                result = match(posting, criteria["keywords"], criteria["min_matches"])
                if result is None:
                    continue

                matched_count += 1
                request_id = str(uuid.uuid4())
                log.info(
                    "keyword match [%s] %s -- %s (keywords: %s)",
                    request_id,
                    posting.id,
                    posting.title,
                    ", ".join(result.matched_keywords),
                )

                try:
                    assessment = assess_fit(
                        config["application_writer"]["base_url"],
                        secrets.application_writer_token,
                        posting,
                        result.matched_keywords,
                        request_id,
                    )
                except AssessError as exc:
                    log.error("[%s] assess failed, skipping: %s", request_id, exc)
                    continue

                assessed_count += 1
                fit_level = assessment.get("fit_level", "schwach")
                if _FIT_LEVEL_RANK.get(fit_level, 0) < min_fit_rank:
                    log.info("[%s] fit_level=%s below threshold, skipping", request_id, fit_level)
                    continue

                log.info(
                    "[%s] fit_level=%s -- notifying%s",
                    request_id,
                    fit_level,
                    " + drafting" if compose_enabled else " (drafting disabled, compose_enabled=false)",
                )
                try:
                    _notify_match_found(
                        config, secrets, posting, result.matched_keywords, assessment, compose_enabled
                    )
                except httpx.HTTPError as exc:
                    log.error("[%s] ntfy notify failed, will retry next run: %s", request_id, exc)
                    continue

                try:
                    store.mark_seen(
                        repo_path,
                        config["applications_repo"]["clone_url"],
                        secrets.applications_repo_token,
                        posting,
                        fit_level,
                        assessment.get("summary", ""),
                    )
                except Exception as exc:
                    log.error("[%s] mark_seen failed (will re-notify next run): %s", request_id, exc)

                if not compose_enabled:
                    continue

                try:
                    trigger_compose(
                        config["application_writer"]["base_url"],
                        secrets.application_writer_token,
                        posting,
                        result.matched_keywords,
                        request_id,
                    )
                    triggered_count += 1
                except ComposeError as exc:
                    log.error("[%s] %s", request_id, exc)

    log.info(
        "run complete: fetched=%d matched=%d assessed=%d composed_triggered=%d",
        fetched_count,
        matched_count,
        assessed_count,
        triggered_count,
    )


def _notify_match_found(
    config: dict, secrets: Secrets, posting, matched_keywords: list[str], assessment: dict, compose_enabled: bool
) -> None:
    ntfy = config["notifications"]["ntfy"]
    footer = "Draft wird erstellt..." if compose_enabled else "Kein Draft (compose_enabled=false)."
    notify(
        base_url=ntfy["base_url"],
        topic=ntfy["topic"],
        token=secrets.ntfy_token,
        title=f"[{assessment.get('fit_level', '?')}] {posting.title}",
        message=(
            f"{posting.company or 'Unbekannt'} -- {posting.portal}\n"
            f"Keywords: {', '.join(matched_keywords)}\n\n"
            f"{assessment.get('summary', '')}\n\n"
            f"{footer}"
        ),
        click_url=posting.url,
    )


if __name__ == "__main__":
    run()
