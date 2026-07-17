"""Scanner CronJob entrypoint: fetch -> match -> dedup -> notify -> trigger compose.

Runs to completion and exits (k8s CronJob), once per invocation. A failure
in one portal's fetcher, or in triggering application-writer for one
posting, is logged and does not abort the rest of the run.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import httpx

from scanner import store
from scanner.application_writer_client import ComposeError, trigger_compose
from scanner.config import Secrets, load_config
from scanner.fetchers import enabled_fetchers
from scanner.matcher import match
from scanner.notifier import notify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("jobscout.scanner")


def run() -> None:
    config = load_config()
    secrets = Secrets.from_env()

    repo_path = store.sync_applications_repo(
        config["applications_repo"]["clone_url"],
        secrets.applications_repo_token,
        Path(config["applications_repo"]["local_path"]),
    )

    criteria = config["criteria"]
    fetched_count = 0
    matched_count = 0
    triggered_count = 0

    with httpx.Client(follow_redirects=True) as client:
        for portal_name, fetch in enabled_fetchers(config):
            try:
                postings = fetch(client, config["portals"][portal_name])
            except httpx.HTTPError as exc:
                log.error("fetcher %s failed: %s", portal_name, exc)
                continue

            fetched_count += len(postings)
            log.info("fetched %d postings from %s", len(postings), portal_name)

            for posting in postings:
                if store.already_seen(repo_path, posting.id):
                    continue

                result = match(posting, criteria["keywords"], criteria["min_matches"])
                if result is None:
                    continue

                matched_count += 1
                request_id = str(uuid.uuid4())
                log.info(
                    "match [%s] %s -- %s (keywords: %s)",
                    request_id,
                    posting.id,
                    posting.title,
                    ", ".join(result.matched_keywords),
                )

                _notify_match_found(config, secrets, posting, result.matched_keywords)

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
        "run complete: fetched=%d matched=%d composed_triggered=%d",
        fetched_count,
        matched_count,
        triggered_count,
    )


def _notify_match_found(config: dict, secrets: Secrets, posting, matched_keywords: list[str]) -> None:
    ntfy = config["notifications"]["ntfy"]
    notify(
        base_url=ntfy["base_url"],
        topic=ntfy["topic"],
        token=secrets.ntfy_token,
        title=f"Neuer Match: {posting.title}",
        message=(
            f"{posting.company or 'Unbekannt'} -- {posting.portal}\n"
            f"Keywords: {', '.join(matched_keywords)}\n"
            f"Draft wird erstellt..."
        ),
        click_url=posting.url,
    )


if __name__ == "__main__":
    run()
