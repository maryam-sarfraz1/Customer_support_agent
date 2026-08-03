"""Capture README screenshots of the chat page and admin dashboard.

Usage: python scripts/take_screenshots.py [--base-url http://localhost:8000]
Requires: pip install playwright && playwright install chromium
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "images"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--admin-email", default="admin@gmail.com")
    parser.add_argument("--admin-password", default="admin-change-me")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # --- Customer chat with a real answer ---
        page.goto(f"{args.base_url}/chat")
        page.fill("#box", "What is your refund policy?")
        page.click("button.send")
        page.wait_for_selector(".cite", timeout=90_000)
        page.fill("#box", "How do I reset my password?")
        page.click("button.send")
        page.wait_for_selector(".rate >> nth=1", timeout=90_000)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT_DIR / "chat.png"))
        print("saved chat.png")

        # --- Admin dashboard with live metrics ---
        page.goto(f"{args.base_url}/admin")
        page.fill("#email", args.admin_email)
        page.fill("#password", args.admin_password)
        page.click("button[type=submit]")
        page.wait_for_selector(".tile", timeout=30_000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT_DIR / "dashboard.png"))
        print("saved dashboard.png")

        browser.close()


if __name__ == "__main__":
    main()
