"""One-time interactive LinkedIn login to bootstrap a persisted Playwright
session for scanner/fetchers/linkedin.py.

Run this locally, with a real display (not headless, not in the cluster) --
LinkedIn's bot-detection started throwing a PIN/2FA verification checkpoint
on every fresh automated login, so the fetcher now reuses a saved session
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

from playwright.sync_api import sync_playwright

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "linkedin_storage_state.json"


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.linkedin.com/login", wait_until="networkidle")

        print("Browser window opened. Log in manually and clear any PIN/2FA/CAPTCHA")
        print("challenge by hand. Wait until you land on your feed or any logged-in page.")
        input("Press Enter here once you're fully logged in... ")

        if "/login" in page.url or "checkpoint" in page.url or "challenge" in page.url:
            print("Still looks logged out (URL is still /login or /checkpoint) -- aborting.", file=sys.stderr)
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
