"""One-time interactive Xing login to bootstrap a persisted Playwright
session for scanner/fetchers/xing.py.

Run this locally, with a real display (not headless, not in the cluster).
See xing.py's docstring for why: its guessed `/login` URL was a 404 (Xing's
real login lives on a separate `login.xing.com` subdomain, a JS SPA with no
server-rendered form to inspect safely without logging a real account out),
so this fetcher adopts the same persisted-session pattern as
linkedin_login_bootstrap.py rather than guessing selectors blind.

Usage:
    just xing-session-bootstrap

Then follow the printed kubectl command to load the saved session into the
cluster as a Secret, and delete the local file -- it's a live session
credential, same sensitivity as a password.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # running this script directly doesn't put the repo root on sys.path

from playwright.sync_api import sync_playwright  # noqa: E402 -- must follow the sys.path insert above

from scanner.fetchers.xing import LOGIN_URL  # noqa: E402 -- must follow the sys.path insert above

OUTPUT_PATH = REPO_ROOT / "xing_storage_state.json"


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(LOGIN_URL, wait_until="load", timeout=60_000)

        print("Browser window opened. Log in manually and clear any 2FA/CAPTCHA")
        print("challenge by hand. Wait until you land on your Xing feed or job search.")
        input("Press Enter here once you're fully logged in... ")

        page.wait_for_load_state("load")
        still_on_login = page.url.startswith(LOGIN_URL)
        if still_on_login:
            print("Still looks logged out (still on the login page) -- aborting.", file=sys.stderr)
            browser.close()
            sys.exit(1)

        context.storage_state(path=str(OUTPUT_PATH))
        browser.close()

    print(f"\nSession saved to {OUTPUT_PATH}")
    print("Next steps:")
    print("  kubectl create secret generic jobscout-xing-session \\")
    print("    --namespace jobscout \\")
    print(f"    --from-file=xing.json={OUTPUT_PATH} \\")
    print("    --dry-run=client -o yaml | kubectl apply -f -")
    print("\nThen delete the local file -- it's a live session credential:")
    print(f"  rm {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
