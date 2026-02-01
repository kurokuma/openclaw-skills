---
name: urlscan-search
description: URL scanning and searching via urlscan.io using urlscan-python. Input is a single URL or query/uuid depending on mode.
---

# urlscan Lookup Skill

This skill uses urlscan.io via the urlscan-python client.

## Usage

Scan a URL:
- `python3 urlscan_search.py scan https://example.com --visibility unlisted`

Search:
- `python3 urlscan_search.py search "page.domain:example.com" --limit 10`

Get result by UUID:
- `python3 urlscan_search.py get <uuid>`

## Install
- `pip install urlscan-python`

## Scripts
- `urlscan_search.py`: Runs scan/search/get and prints a readable summary (optional JSON with --json).
