---
name: waybackpy-search
description: Query the Internet Archive Wayback Machine using waybackpy. Input is a single URL. Supports newest/oldest/near/snapshots/save.
---

# Waybackpy Search Skill

This skill queries the Wayback Machine APIs via waybackpy for a single URL.

Supported operations:
- newest: latest snapshot
- oldest: earliest snapshot
- near: snapshot near a given timestamp/date
- snapshots: list snapshots in a range (limited)
- save: archive the URL now (Save API)

## Usage

Examples:
- `python3 wayback_search.py https://example.com --mode newest`
- `python3 wayback_search.py https://example.com --mode oldest`
- `python3 wayback_search.py https://example.com --mode near --year 2020 --month 1 --day 1`
- `python3 wayback_search.py https://example.com --mode near --wayback-ts 20101010101010`
- `python3 wayback_search.py https://example.com --mode snapshots --start 2018 --end 2019 --limit 20`
- `python3 wayback_search.py https://example.com --mode save`

## Requirements
- Python 3.10+
- `pip install waybackpy`

## Scripts
- `wayback_search.py`: Executes the Wayback Machine query using waybackpy and prints a human-readable summary.