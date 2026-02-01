#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Headless Selenium fetcher.

- Input: one URL
- Output:
  - default: rendered HTML (page_source)
  - --text: visible text (best-effort)
  - --selector CSS: scope to a CSS selector (HTML or text)
  - --screenshot path: save PNG screenshot
- Safety:
  - disables downloads
  - no extra navigation beyond the given URL (except redirects)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def build_driver(headless: bool = True) -> webdriver.Chrome:
    chrome_binary = os.getenv("CHROME_BINARY", "").strip() or None
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "").strip() or None

    opts = ChromeOptions()
    if chrome_binary:
        opts.binary_location = chrome_binary

    # Headless
    if headless:
        # new headless (Chrome 109+)
        opts.add_argument("--headless=new")

    # Hardening / stability flags
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1365,768")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--disable-default-apps")
    opts.add_argument("--disable-sync")
    opts.add_argument("--metrics-recording-only")
    opts.add_argument("--no-first-run")
    opts.add_argument("--password-store=basic")
    opts.add_argument("--use-mock-keychain")

    # Reduce automation fingerprints a bit (not perfect)
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # Disable downloads
    prefs = {
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    opts.add_experimental_option("prefs", prefs)

    service = ChromeService(executable_path=chromedriver_path) if chromedriver_path else ChromeService()
    driver = webdriver.Chrome(service=service, options=opts)

    # a little anti-detection (best-effort)
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
"""
            },
        )
    except Exception:
        pass

    return driver


def validate_url(url: str) -> str:
    u = url.strip()
    if not u:
        raise ValueError("empty_url")
    if not (u.startswith("http://") or u.startswith("https://")):
        raise ValueError("url_must_start_with_http_or_https")
    return u


def fetch(
    url: str,
    timeout: int,
    wait_seconds: float,
    selector: Optional[str],
    as_text: bool,
    screenshot_path: Optional[str],
) -> str:
    driver = None
    try:
        driver = build_driver(headless=True)
        driver.set_page_load_timeout(timeout)

        driver.get(url)

        # Wait for DOM ready
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
            )
        except TimeoutException:
            # continue; sometimes SPAs never reach complete
            pass

        # Optional fixed wait (useful for SPAs)
        if wait_seconds > 0:
            time.sleep(wait_seconds)

        # Optional selector wait (ensure element exists)
        if selector:
            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            except TimeoutException:
                # element not found; still output whatever we have
                pass

        # Screenshot
        if screenshot_path:
            driver.save_screenshot(screenshot_path)

        # Extract content
        if selector:
            elems = driver.find_elements(By.CSS_SELECTOR, selector)
            if elems:
                if as_text:
                    # join visible texts
                    return "\n\n".join([e.text for e in elems if e.text])
                else:
                    # outerHTML for each matched node
                    return "\n\n".join(
                        [driver.execute_script("return arguments[0].outerHTML;", e) for e in elems]
                    )

        # default full page
        if as_text:
            # best-effort visible text from body
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                return body.text
            except Exception:
                return driver.page_source
        else:
            return driver.page_source

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch rendered page content using headless Selenium.")
    ap.add_argument("url", help="Target URL (http/https)")
    ap.add_argument("--timeout", type=int, default=int(os.getenv("SELENIUM_TIMEOUT", "20")),
                    help="Page load / wait timeout seconds (default: SELENIUM_TIMEOUT or 20)")
    ap.add_argument("--wait", type=float, default=0.0,
                    help="Fixed sleep seconds after DOM ready (useful for SPAs)")
    ap.add_argument("--selector", type=str, default=None,
                    help="CSS selector to scope output (e.g., 'main', '#content', '.article')")
    ap.add_argument("--text", action="store_true",
                    help="Output visible text instead of HTML")
    ap.add_argument("--screenshot", type=str, default=None,
                    help="Save screenshot PNG to this path")
    args = ap.parse_args()

    try:
        url = validate_url(args.url)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    try:
        content = fetch(
            url=url,
            timeout=args.timeout,
            wait_seconds=args.wait,
            selector=args.selector,
            as_text=args.text,
            screenshot_path=args.screenshot,
        )
    except WebDriverException as e:
        print(f"error: selenium_webdriver_failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"error: fetch_failed: {e}", file=sys.stderr)
        return 1

    # Human-readable output (no JSON dump)
    print(f"[selenium-fetch] url={url}")
    if args.selector:
        print(f"[selenium-fetch] selector={args.selector} mode={'text' if args.text else 'html'}")
    else:
        print(f"[selenium-fetch] mode={'text' if args.text else 'html'}")
    if args.screenshot:
        print(f"[selenium-fetch] screenshot={args.screenshot}")
    print("-" * 80)
    print(content)

    return 0


if __name__ == "__main__":
    main()
