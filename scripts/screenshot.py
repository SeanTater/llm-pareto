#!/usr/bin/env python3
"""
Screenshot helper for rendering pricing pages
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import base64


def screenshot_url(url: str, output_path: str = None, width: int = 1920, height: int = 4000) -> str:
    """
    Take a screenshot of a URL and return base64-encoded image

    Args:
        url: URL to screenshot
        output_path: Optional path to save screenshot (for debugging)
        width: Viewport width
        height: Viewport height (tall for scrolling pages)

    Returns:
        Base64-encoded PNG image
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        # Navigate and wait for network idle
        page.goto(url, wait_until="networkidle", timeout=30000)

        # Take full page screenshot
        screenshot_bytes = page.screenshot(full_page=True)

        # Save if output path provided
        if output_path:
            Path(output_path).write_bytes(screenshot_bytes)
            print(f"Screenshot saved to {output_path}")

        browser.close()

        # Return base64 for API
        return base64.b64encode(screenshot_bytes).decode('utf-8')


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 screenshot.py <url> [output.png]")
        sys.exit(1)

    url = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Screenshotting {url}...")
    screenshot_url(url, output)
    print("Done!")
