#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VirusTotal lookup using vt-py (VirusTotal official Python client: 'vt').

- Single argument only: ip or url or domain or hash
- Auto-detects IOC type and queries VT v3 accordingly

Install:
  pip install vt-py
"""

from __future__ import annotations

import ipaddress
import os
import re
import sys
import json
from typing import Literal, Tuple

import vt  # vt-py


HASH_RE = re.compile(r"^[A-Fa-f0-9]{32}$|^[A-Fa-f0-9]{40}$|^[A-Fa-f0-9]{64}$")
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}\.?$)(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}\.?$"
)


IocType = Literal["hash", "ip", "domain", "url"]


def detect_ioc(value: str) -> Tuple[IocType, str]:
    v = value.strip()
    if not v:
        raise ValueError("empty_ioc")

    # URL: quick heuristic
    if "://" in v:
        return "url", v

    # IP
    try:
        ipaddress.ip_address(v)
        return "ip", v
    except ValueError:
        pass

    # Hash
    if HASH_RE.fullmatch(v):
        return "hash", v.lower()

    # Domain
    if DOMAIN_RE.fullmatch(v):
        return "domain", v.rstrip(".").lower()

    # Fallback: domain-like token
    if "." in v and " " not in v and "/" not in v and "@" not in v:
        return "domain", v.rstrip(".").lower()

    raise ValueError("unsupported_ioc_type")


def safe_get(d: dict, path: str):
    cur = d
    for p in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def load_config():
    file_path = "/home/ubuntu/.openclaw/api_config.json"
    with open(file_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("api_token", {}).get("virustotal-search", {}).get("vt_token", "")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: vt_lookup.py <ioc>", file=sys.stderr)
        return 2

    api_key = load_config()
    if not api_key:
        print("error: VT_API_KEY is not set", file=sys.stderr)
        return 2

    ioc_raw = sys.argv[1]
    try:
        ioc_type, ioc = detect_ioc(ioc_raw)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    # vt-py client
    with vt.Client(api_key) as client:
        try:
            if ioc_type == "hash":
                obj = client.get_object(f"/files/{ioc}")
            elif ioc_type == "ip":
                obj = client.get_object(f"/ip_addresses/{ioc}")
            elif ioc_type == "domain":
                obj = client.get_object(f"/domains/{ioc}")
            elif ioc_type == "url":
                # vt-py supports passing raw URL to /urls endpoint (it will handle encoding),
                # but behavior depends on version; safest approach is to use /urls with vt.url_id
                url_id = vt.url_id(ioc)  # base64url without '='
                obj = client.get_object(f"/urls/{url_id}")
            else:
                print("error: unsupported_ioc_type", file=sys.stderr)
                return 2
        except vt.error.APIError as e:
            # includes 404/401/429 etc
            print(f"error: vt_api_error: {e}", file=sys.stderr)
            return 1

    # obj is vt.object.Object-like; convert to dict safely
    data = obj.to_dict() if hasattr(obj, "to_dict") else dict(obj)

    attrs = data.get("attributes") or {}
    stats = attrs.get("last_analysis_stats") or {}

    summary = {
        "ioc": ioc_raw,
        "ioc_type": ioc_type,
        "id": data.get("id"),
        "vt_type": data.get("type"),
        "reputation": attrs.get("reputation"),
        "last_analysis_date": attrs.get("last_analysis_date"),
        "last_analysis_stats": {
            "malicious": stats.get("malicious"),
            "suspicious": stats.get("suspicious"),
            "harmless": stats.get("harmless"),
            "undetected": stats.get("undetected"),
        },
    }

    # type-specific extras
    if ioc_type == "hash":
        summary["meaningful_name"] = attrs.get("meaningful_name")
        summary["type_description"] = attrs.get("type_description")
        summary["size"] = attrs.get("size")
        names = (attrs.get("names") or [])[:10]
        if names:
            summary["names_top10"] = names
    elif ioc_type == "ip":
        summary["asn"] = attrs.get("asn")
        summary["as_owner"] = attrs.get("as_owner")
        summary["country"] = attrs.get("country")
        summary["network"] = attrs.get("network")
    elif ioc_type == "domain":
        summary["registrar"] = attrs.get("registrar")
        summary["creation_date"] = attrs.get("creation_date")
        summary["last_dns_records_date"] = attrs.get("last_dns_records_date")
        cats = attrs.get("categories")
        if isinstance(cats, dict) and cats:
            summary["categories_top5"] = dict(list(cats.items())[:5])
    elif ioc_type == "url":
        summary["url"] = attrs.get("url") or ioc
        cats = attrs.get("categories")
        if isinstance(cats, dict) and cats:
            summary["categories_top5"] = dict(list(cats.items())[:5])

    # Human-readable output (simple)
    s = summary["last_analysis_stats"]
    print(f"[VirusTotal] type={summary['ioc_type']} ioc={summary['ioc']}")
    print(f"- id: {summary['id']} / vt_type: {summary['vt_type']}")
    print(f"- verdict: malicious={s.get('malicious')} suspicious={s.get('suspicious')} harmless={s.get('harmless')} undetected={s.get('undetected')}")
    print(f"- reputation: {summary.get('reputation')}  last_analysis_date: {summary.get('last_analysis_date')}")

    # Show a few extras if present
    for k in ("meaningful_name", "type_description", "size", "asn", "as_owner", "country", "network", "registrar", "creation_date", "last_dns_records_date", "url"):
        if k in summary and summary[k] is not None:
            print(f"- {k}: {summary[k]}")
    if "names_top10" in summary:
        print(f"- names(top10): {', '.join(summary['names_top10'])}")
    if "categories_top5" in summary:
        cats = summary["categories_top5"]
        print("- categories(top5): " + ", ".join([f"{k}={v}" for k, v in cats.items()]))

    return 0


if __name__ == "__main__":
    main()
