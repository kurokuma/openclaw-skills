---
name: virustotal-search
description: Lookup IOC reputation and analysis summary using VirusTotal Python client. Auto-detects hash/IP/domain/URL
---

# VirusTotal Lookup Skill

This skill queries VirusTotal for a single IOC argument and returns a concise summary.

Supported IOC types:
- File hash (MD5/SHA1/SHA256)
- IP address
- Domain
- URL

## Usage

Provide exactly one argument (the IOC). The script auto-detects the IOC type.

Examples:
- `python3 vt_search.py 8.8.8.8`
- `python3 vt_search.py example.com`
- `python3 vt_search.py https://example.com/path`
- `python3 vt_search.py 44d88612fea8a8f36de82e1278abb02f`

## Scripts

- `python3 vt_search.py`: VirusTotal lookup using vt-py client, with auto-detection and concise output.
