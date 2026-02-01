#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
censys_ip_lookup.py (Censys Platform SDK / global_data.get_host)

- New SDK: censys_platform
- Lookup: sdk.global_data.get_host(host_id=<ip>)
- Output: human-readable print (NO table, NO raw JSON dump, NO huge http bodies)

Auth:
  - env: CENSYS_PAT
  - or openclaw.json: secrets.censys.pat
Optional:
  - env: CENSYS_ORG_ID
  - or openclaw.json: secrets.censys.organization_id

Install:
  pip install censys-platform

Usage:
  export CENSYS_PAT="..."
  export CENSYS_ORG_ID="..."   # optional
  python censys_ip_lookup.py --ip 8.8.8.8
  python censys_ip_lookup.py --ip 8.8.8.8 --include_threats
  python censys_ip_lookup.py --ip 8.8.8.8 --max-dns 30
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from censys_platform import SDK, RetryConfig
from censys_platform.utils import BackoffStrategy


# ----------------------------
# config / secrets
# ----------------------------

def _read_json_file(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_censys_config() -> Tuple[str, Optional[str]]:
    """
    Returns: (pat, organization_id)

    Priority:
      - PAT:
        1) env CENSYS_PAT
        2) openclaw.json secrets.censys.pat
      - ORG_ID (optional):
        1) env CENSYS_ORG_ID
        2) openclaw.json secrets.censys.organization_id
    """
    pat = os.getenv("CENSYS_PAT", "").strip()
    org_id = os.getenv("CENSYS_ORG_ID", "").strip() or None

    candidates = [
        Path(os.getenv("OPENCLAW_CONFIG", "")).expanduser(),
        Path.home() / ".config" / "openclaw" / "openclaw.json",
        Path.home() / ".openclaw" / "openclaw.json",
        Path.cwd() / "openclaw.json",
    ]

    if not pat or not org_id:
        for p in candidates:
            if not p or str(p) in ("", ".") or not p.exists():
                continue
            data = _read_json_file(p)
            if not isinstance(data, dict):
                continue
            secrets = data.get("secrets") or {}
            censys = secrets.get("censys") or {}

            if not pat:
                pat2 = str(censys.get("pat") or "").strip()
                if pat2:
                    pat = pat2

            if not org_id:
                org2 = str(censys.get("organization_id") or "").strip()
                if org2:
                    org_id = org2

            if pat and org_id:
                break

    if not pat:
        raise RuntimeError("Censys PAT not found. Set CENSYS_PAT or put secrets.censys.pat in openclaw.json.")

    return pat, org_id


def validate_ip(value: str) -> str:
    v = value.strip()
    if not v:
        raise ValueError("empty_ip")
    try:
        ipaddress.ip_address(v)
    except ValueError:
        raise ValueError("invalid_ip")
    return v


# ----------------------------
# SDK response helpers
# ----------------------------

def _is_unset(v: Any) -> bool:
    return v is None or v.__class__.__name__.lower() == "unset"


def _safe_get(obj: Any, *path: str, default: Any = None) -> Any:
    cur = obj
    for p in path:
        if cur is None or _is_unset(cur):
            return default
        if isinstance(cur, dict):
            cur = cur.get(p, default)
            continue
        if hasattr(cur, p):
            cur = getattr(cur, p)
            continue
        return default
    return default if _is_unset(cur) else cur


def unwrap_host_resource(envelope: Any) -> Any:
    """
    sdk.global_data.get_host(host_id=ip) returns something like:
      headers={...} result=ResponseEnvelopeHostAsset(result=HostAsset(resource=Host(...)))

    We want Host(...) (resource).
    """
    host = _safe_get(envelope, "result", "result", "resource", default=None)
    if host is not None:
        return host

    host = _safe_get(envelope, "result", "resource", default=None)
    if host is not None:
        return host

    if hasattr(envelope, "ip") and hasattr(envelope, "services"):
        return envelope

    raise RuntimeError("Unexpected Censys SDK response shape: cannot locate Host resource.")


# ----------------------------
# summarization (JSON object in memory)
# ----------------------------

def summarize_host(host: Any, include_threats: bool = False, max_dns: int = 50) -> Dict[str, Any]:
    # ---- DNS ----
    dns = _safe_get(host, "dns", default=None)

    fwd_dns_keys: List[str] = []
    rev_dns_names: List[str] = []

    fwd_dns = _safe_get(dns, "forward_dns", default=None)
    if isinstance(fwd_dns, dict):
        fwd_dns_keys = list(fwd_dns.keys())[:max_dns]
    elif fwd_dns and hasattr(fwd_dns, "__iter__"):
        fwd_dns_keys = [str(x) for x in list(fwd_dns)[:max_dns]]

    rev_dns = _safe_get(dns, "reverse_dns", default=None)
    rev_names = _safe_get(rev_dns, "names", default=None)
    if isinstance(rev_names, list):
        rev_dns_names = [str(x) for x in rev_names[:max_dns]]
    elif rev_names and hasattr(rev_names, "__iter__"):
        rev_dns_names = [str(x) for x in list(rev_names)[:max_dns]]

    dns_names_all = _safe_get(dns, "names", default=[]) or []
    dns_names_top = [str(x) for x in dns_names_all[:max_dns]] if isinstance(dns_names_all, list) else []

    # ---- Location ----
    loc = _safe_get(host, "location", default=None)
    coords = _safe_get(loc, "coordinates", default=None)
    location = {
        "continent": _safe_get(loc, "continent"),
        "country_code": _safe_get(loc, "country_code"),
        "country": _safe_get(loc, "country"),
        "province": _safe_get(loc, "province"),
        "city": _safe_get(loc, "city"),
        "timezone": _safe_get(loc, "timezone"),
        "latitude": _safe_get(coords, "latitude"),
        "longitude": _safe_get(coords, "longitude"),
    }

    # ---- Routing ----
    routing = {
        "asn": _safe_get(host, "autonomous_system", "asn"),
        "bgp_prefix": _safe_get(host, "autonomous_system", "bgp_prefix"),
        "country_code": _safe_get(host, "autonomous_system", "country_code"),
        "as_name": _safe_get(host, "autonomous_system", "name"),
        "as_description": _safe_get(host, "autonomous_system", "description"),
    }

    # ---- Services ----
    services_obj = _safe_get(host, "services", default=[]) or []
    service_count = _safe_get(host, "service_count")

    ports: Set[int] = set()
    protocols: Set[str] = set()

    software_rows: List[Dict[str, Optional[str]]] = []
    threat_rows: List[Dict[str, Optional[str]]] = []

    for svc in services_obj:
        port = _safe_get(svc, "port")
        proto = _safe_get(svc, "protocol")

        if isinstance(port, int):
            ports.add(port)
        elif isinstance(port, str) and port.isdigit():
            ports.add(int(port))

        if isinstance(proto, str) and proto:
            protocols.add(proto)

        # software
        sw_list = _safe_get(svc, "software", default=[]) or []
        for sw in sw_list:
            vendor = _safe_get(sw, "vendor")
            product = _safe_get(sw, "product")
            version = _safe_get(sw, "version")
            cpe = _safe_get(sw, "cpe")

            if not any([vendor, product, version, cpe]):
                continue

            software_rows.append(
                {
                    "port": str(port) if port is not None else None,
                    "protocol": str(proto) if proto is not None else None,
                    "vendor": vendor,
                    "product": product,
                    "version": version,
                    "cpe": cpe,
                }
            )

        # threats (optional)
        if include_threats:
            thr_list = _safe_get(svc, "threats", default=[]) or []
            for thr in thr_list:
                name = _safe_get(thr, "name")
                ttype = _safe_get(thr, "type")
                if not any([name, ttype]):
                    continue
                threat_rows.append(
                    {
                        "port": str(port) if port is not None else None,
                        "protocol": str(proto) if proto is not None else None,
                        "name": name,
                        "type": ttype,
                    }
                )

    summary: Dict[str, Any] = {
        "ip": _safe_get(host, "ip"),
        "routing": routing,
        "location": location,
        "dns": {
            "forward_dns_top": fwd_dns_keys,
            "reverse_dns_top": rev_dns_names,
            "names_top": dns_names_top,
            "counts": {
                "forward_dns": len(fwd_dns) if isinstance(fwd_dns, dict) else len(fwd_dns_keys),
                "reverse_dns": len(rev_names) if isinstance(rev_names, list) else len(rev_dns_names),
                "names": len(dns_names_all) if isinstance(dns_names_all, list) else len(dns_names_top),
            },
        },
        "services": {
            "service_count": service_count,
            "ports": sorted(ports),
            "protocols": sorted(protocols),
            "software": software_rows,
        },
    }

    if include_threats:
        summary["services"]["threats"] = threat_rows

    return summary


# ----------------------------
# human-readable print (no JSON dump)
# ----------------------------

def _print_kv(key: str, value: Any, indent: int = 0) -> None:
    pad = " " * indent
    if value is None or value == "" or value == [] or value == {}:
        return
    print(f"{pad}{key}: {value}")


def print_summary(summary: Dict[str, Any], max_list_items: int = 30) -> None:
    """
    Print readable summary without dumping raw JSON.
    Caps long lists.
    """
    ip = summary.get("ip")
    print(f"[Censys Platform] Host Summary")
    print(f"IP: {ip}")

    routing = summary.get("routing", {}) or {}
    print("\n== Routing ==")
    _print_kv("ASN", routing.get("asn"), 0)
    _print_kv("BGP Prefix", routing.get("bgp_prefix"), 0)
    _print_kv("AS Name", routing.get("as_name"), 0)
    _print_kv("AS Desc", routing.get("as_description"), 0)

    loc = summary.get("location", {}) or {}
    print("\n== Location ==")
    _print_kv("Continent", loc.get("continent"), 0)
    _print_kv("Country", f"{loc.get('country')} ({loc.get('country_code')})" if loc.get("country") else loc.get("country_code"), 0)
    _print_kv("Province", loc.get("province"), 0)
    _print_kv("City", loc.get("city"), 0)
    _print_kv("Timezone", loc.get("timezone"), 0)
    if loc.get("latitude") is not None and loc.get("longitude") is not None:
        _print_kv("Coordinates", f"{loc.get('latitude')}, {loc.get('longitude')}", 0)

    dns = summary.get("dns", {}) or {}
    counts = dns.get("counts", {}) or {}
    print("\n== DNS ==")
    _print_kv("Forward DNS count", counts.get("forward_dns"), 0)
    _print_kv("Reverse DNS count", counts.get("reverse_dns"), 0)
    _print_kv("DNS names count", counts.get("names"), 0)

    def _print_list(title: str, items: List[str]):
        if not items:
            return
        show = items[:max_list_items]
        more = len(items) - len(show)
        print(f"\n{title} (showing {len(show)}{' +'+str(more) if more>0 else ''}):")
        for x in show:
            print(f" - {x}")

    _print_list("Forward DNS (top)", dns.get("forward_dns_top") or [])
    _print_list("Reverse DNS (top)", dns.get("reverse_dns_top") or [])
    _print_list("DNS names (top)", dns.get("names_top") or [])

    svc = summary.get("services", {}) or {}
    print("\n== Services ==")
    _print_kv("Service count", svc.get("service_count"), 0)
    _print_kv("Ports", svc.get("ports"), 0)
    _print_kv("Protocols", svc.get("protocols"), 0)

    software = svc.get("software") or []
    if software:
        print(f"\nSoftware (rows: {len(software)}; showing up to {max_list_items}):")
        for row in software[:max_list_items]:
            port = row.get("port") or "?"
            proto = row.get("protocol") or "?"
            vendor = row.get("vendor") or "N/A"
            product = row.get("product") or "N/A"
            version = row.get("version") or "N/A"
            cpe = row.get("cpe") or "N/A"
            print(f" - {port}/{proto}  {vendor}  {product}  ver={version}  cpe={cpe}")
        if len(software) > max_list_items:
            print(f" ... ({len(software) - max_list_items} more)")

    threats = svc.get("threats") or []
    if threats:
        print(f"\nThreats (rows: {len(threats)}; showing up to {max_list_items}):")
        for row in threats[:max_list_items]:
            port = row.get("port") or "?"
            proto = row.get("protocol") or "?"
            name = row.get("name") or "N/A"
            ttype = row.get("type") or "N/A"
            print(f" - {port}/{proto}  {name}  type={ttype}")
        if len(threats) > max_list_items:
            print(f" ... ({len(threats) - max_list_items} more)")


# ----------------------------
# CLI
# ----------------------------

def load_config():
    file_path = "/home/ubuntu/.openclaw/api_config.json"
    with open(file_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("api_token", {}).get("censys-search", {}).get("pat", "")

def main() -> int:
    if len(sys.argv) == 1:
        print("Usage: censys_search.py <ip_address>", file=sys.stderr)
        return
    ip_address = sys.argv[1]

    try:
        ip_address = validate_ip(ip_address)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    try:
        pat = load_config()
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    retry_cfg = RetryConfig(
        "backoff",
        BackoffStrategy(100, 10000, 1.5, 30000),
        True
    )

    try:
        sdk_kwargs: Dict[str, Any] = {
            "personal_access_token": pat,
            "retry_config": retry_cfg,
        }

        with SDK(**sdk_kwargs) as sdk:
            res = sdk.global_data.get_host(host_id=ip_address)
            host = unwrap_host_resource(res)
            summary = summarize_host(host)

        print_summary(summary)
        return 0

    except Exception as e:
        print(f"error: censys_platform_lookup_failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()
