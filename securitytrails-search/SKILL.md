---
name: securitytrails-search
description: Domain intelligence lookup via SecurityTrails using pysecuritytrails. Input is a single domain.
---

# SecurityTrails Lookup Skill

This skill queries SecurityTrails (via pysecuritytrails) for a single domain.

## Usage

Examples:
- `python3 securitytrails_search.py example.com --mode info`
- `python3 securitytrails_search.py example.com --mode subdomains --limit 50`
- `python3 securitytrails_search.py example.com --mode whois`
- `python3 securitytrails_search.py example.com --mode history_dns`
- `python3 securitytrails_search.py example.com --mode tags`

## Install
- `pip install pysecuritytrails`

## Scripts
-  securitytrails_search.py`: Executes SecurityTrails domain lookup and prints a readable summary (optional JSON with --json).
