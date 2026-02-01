---
name: censys-search
description: Lookup a host by IP using Censys Search API (Hosts view).
---

# Censys IP Lookup Skill

This skill queries Censys Search API (Hosts view) for a single IP address and returns a concise summary.

## Usage

Provide exactly one argument: an IPv4/IPv6 address.

Examples:
- `python3 censys_search.py 8.8.8.8`
- `python3 censys_search.py 2001:4860:4860::8888`

## Scripts

- `censys_search.py`: Executes Censys host view lookup for the given IP and prints a summary (JSON optional with `--json`).
