"""One-time interactive LinkedIn login to bootstrap a persisted Playwright
session for scanner/fetchers/linkedin.py.

Run this locally, with a real display (not headless, not in the cluster) --
A fresh automated login started triggering a PIN/2FA verification
checkpoint on every attempt, so the fetcher now reuses a saved session
instead of logging in from scratch on every cron run. See
linkedin.py's docstring (point 4) for the full rationale.

Usage:
    just linkedin-session-bootstrap

Then follow the printed kubectl command to load the saved session into the
cluster as a Secret, and delete the local file -- it's a live session
credential, same sensitivity as a password.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # running this script directly doesn't put the repo root on sys.path

from playwright.sync_api import sync_playwright

from scanner.fetchers.linkedin import USER_AGENT  # noqa: E402 -- must follow the sys.path insert above

OUTPUT_PATH = REPO_ROOT / "linkedin_storage_state.json"


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        # Same USER_AGENT as scanner/fetchers/linkedin.py uses to replay
        # this session headless -- if the fingerprint differs between
        # bootstrap and replay, that mismatch is itself a plausible bot
        # signal. See linkedin.py's USER_AGENT docstring for the full
        # rationale.
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        # "networkidle" reliably times out on LinkedIn -- its pages keep
        # firing background analytics/presence beacons indefinitely, so
        # network traffic never actually goes idle even once the page is
        # fully loaded and interactive. "load" is the right signal here.
        page.goto("https://www.linkedin.com/login", wait_until="load", timeout=60_000)

        print("Browser window opened. Log in manually and clear any PIN/2FA/CAPTCHA")
        print("challenge by hand. Wait until you land on your feed or any logged-in page.")
        input("Press Enter here once you're fully logged in... ")

        # URL substring checks are unreliable here: LinkedIn's own
        # internal post-login redirect hop is
        # https://www.linkedin.com/checkpoint/lg/login-submit -- a normal
        # part of a *successful* login, but "login" in "login-submit"
        # false-positives any "/login" or "checkpoint" substring check
        # (found 2026-08-15, aborted a genuinely successful login). The
        # actual login form being gone is a much more reliable signal.
        page.wait_for_load_state("load")
        still_showing_login_form = page.query_selector("#username") is not None
        if still_showing_login_form:
            print("Still looks logged out (login form is still showing) -- aborting.", file=sys.stderr)
            browser.close()
            sys.exit(1)

        context.storage_state(path=str(OUTPUT_PATH))
        browser.close()

    print(f"\nSession saved to {OUTPUT_PATH}")
    print("Next steps:")
    print("  kubectl create secret generic jobscout-linkedin-session \\")
    print("    --namespace jobscout \\")
    print(f"    --from-file=linkedin.json={OUTPUT_PATH} \\")
    print("    --dry-run=client -o yaml | kubectl apply -f -")
    print("\nThen delete the local file -- it's a live session credential:")
    print(f"  rm {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
