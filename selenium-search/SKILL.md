---
name: selenium-search
description: Fetch rendered page content using a headless Selenium browser (Chromium/Chrome). Input is a single URL. Outputs rendered HTML (and optional extracted text/screenshot).
---

# Selenium Headless Fetch Skill

This skill launches a headless browser using Selenium to load a URL and retrieve the rendered page content (post-JS execution).

## Usage

Provide one URL as input.

Examples:
- `python3 fetch.py https://example.com`
- `python3 fetch.py https://example.com --text`
- `python3 fetch.py https://example.com --wait 3 --timeout 30`
- `python3 fetch.py https://example.com --selector "main" --text`
- `python3 fetch.py https://example.com --screenshot out.png`

## Requirements

- Python 3.10+
- Selenium: `pip install selenium`
- Selenium: `sudo apt install chromium-chromedriver`

## Scripts

- `fetch.py`: Loads a URL in headless mode and prints rendered HTML (default) or extracted text.
