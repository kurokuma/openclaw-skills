#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from pysecuritytrails import SecurityTrails, SecurityTrailsError


DOMAIN_RE = re.compile(
    r"^(?=.{1,253}\.?$)(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}\.?$"
)


def load_config():
    file_path = "/home/ubuntu/.openclaw/api_config.json"
    with open(file_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("api_token", {}).get("securitytrails-search", {}).get("api_key", "")


def validate_domain(domain: str) -> str:
    d = domain.strip().rstrip(".")
    if not d:
        raise ValueError("empty_domain")
    if not DOMAIN_RE.fullmatch(d):
        raise ValueError("invalid_domain")
    return d.lower()


def print_title(s: str) -> None:
    print(s)
    print("-" * 80)


def main() -> int:
    ap = argparse.ArgumentParser(description="SecurityTrails domain lookup via pysecuritytrails")
    ap.add_argument("domain", help="target domain (e.g., example.com)")
    ap.add_argument("--mode", choices=["info", "subdomains", "whois", "history_dns", "history_whois", "tags"], default="info")
    ap.add_argument("--limit", type=int, default=50, help="max list items to print (default: 50)")
    ap.add_argument("--json", action="store_true", help="print raw JSON (debug)")
    args = ap.parse_args()

    try:
        domain = validate_domain(args.domain)
        api_key = load_config()
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    st = SecurityTrails(api_key)

    try:
        if args.mode == "info":
            data = st.domain_info(domain)
        elif args.mode == "subdomains":
            data = st.domain_subdomains(domain)
        elif args.mode == "whois":
            data = st.domain_whois(domain)
        elif args.mode == "history_dns":
            data = st.domain_history_dns(domain)
        elif args.mode == "history_whois":
            data = st.domain_history_whois(domain)
        elif args.mode == "tags":
            data = st.domain_tags(domain)
        else:
            print("error: unknown mode", file=sys.stderr)
            return 2
    except SecurityTrailsError as e:
        print(f"error: securitytrails_error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"error: lookup_failed: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"domain": domain, "mode": args.mode, "data": data}, ensure_ascii=False, indent=2))
        return 0

    print(f"[SecurityTrails] domain={domain} mode={args.mode}")
    print("-" * 80)

    # Human-readable summary (best-effort; response shape varies)
    if args.mode == "subdomains":
        subs = None
        if isinstance(data, dict):
            subs = data.get("subdomains") or data.get("records") or data.get("data")
        if isinstance(subs, list):
            print(f"subdomains: {len(subs)} (showing up to {args.limit})")
            for s in subs[:args.limit]:
                if isinstance(s, str):
                    print(f" - {s}.{domain}")
                else:
                    print(f" - {s}")
            if len(subs) > args.limit:
                print(f" ... ({len(subs)-args.limit} more)")
            return 0

    if isinstance(data, dict):
        # show key highlights
        keys = list(data.keys())
        print(f"keys: {keys[:min(len(keys), 30)]}")
        # common highlights if present
        for k in ("apex_domain", "hostname", "registered_domain", "tags"):
            if k in data and data[k]:
                v = data[k]
                if isinstance(v, list):
                    print(f"{k}: count={len(v)} top={v[:min(len(v), args.limit)]}")
                else:
                    print(f"{k}: {str(v)[:200]}")
        return 0

    print(str(data)[:800])
    return 0


if __name__ == "__main__":
    main()
