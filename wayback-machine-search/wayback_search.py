#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wayback_lookup.py

Wayback Machine lookup via waybackpy.

- Input: one URL (http/https)
- Modes:
  - newest
  - oldest
  - near (year/month/day/hour/minute or --wayback-ts or --unix-ts)
  - snapshots (range with --start/--end, prints up to --limit)
  - save (Save API)

Env:
  WAYBACK_USER_AGENT (recommended)

Install:
  pip install waybackpy
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from waybackpy import WaybackMachineCDXServerAPI, WaybackMachineSaveAPI  # per official docs


DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"


def validate_url(url: str) -> str:
    u = url.strip()
    if not u:
        raise ValueError("empty_url")
    if not (u.startswith("http://") or u.startswith("https://")):
        raise ValueError("url_must_start_with_http_or_https")
    return u


def get_default_user_agent() -> str:
    return DEFAULT_UA


def print_capture(item) -> None:
    """
    item: waybackpy snapshot/capture object (CDX result)
    Fields shown in docs: archive_url, original, timestamp, datetime_timestamp, statuscode, mimetype, urlkey
    """
    print(f"archive_url : {getattr(item, 'archive_url', None)}")
    print(f"original    : {getattr(item, 'original', None)}")
    print(f"timestamp   : {getattr(item, 'timestamp', None)}")
    print(f"datetime    : {getattr(item, 'datetime_timestamp', None)}")
    print(f"statuscode  : {getattr(item, 'statuscode', None)}")
    print(f"mimetype    : {getattr(item, 'mimetype', None)}")
    # urlkey is sometimes helpful for debugging
    if hasattr(item, "urlkey"):
        print(f"urlkey      : {getattr(item, 'urlkey', None)}")


def mode_newest(url: str) -> int:
    cdx = WaybackMachineCDXServerAPI(url, get_default_user_agent())
    item = cdx.newest()
    print("== newest ==")
    print_capture(item)
    return 0


def mode_oldest(url: str) -> int:
    cdx = WaybackMachineCDXServerAPI(url, get_default_user_agent())
    item = cdx.oldest()
    print("== oldest ==")
    print_capture(item)
    return 0


def mode_near(url: str, year: Optional[int], month: Optional[int], day: Optional[int],
              hour: Optional[int], minute: Optional[int],
              wayback_ts: Optional[str], unix_ts: Optional[int]) -> int:
    cdx = WaybackMachineCDXServerAPI(url, get_default_user_agent())

    print("== near ==")
    if wayback_ts:
        item = cdx.near(wayback_machine_timestamp=wayback_ts)
        print(f"query: wayback_machine_timestamp={wayback_ts}")
        print_capture(item)
        return 0

    if unix_ts is not None:
        item = cdx.near(unix_timestamp=unix_ts)
        print(f"query: unix_timestamp={unix_ts}")
        print_capture(item)
        return 0

    # date components (defaults)
    y = year if year is not None else 2010
    m = month if month is not None else 1
    d = day if day is not None else 1
    h = hour if hour is not None else 0
    mi = minute if minute is not None else 0

    item = cdx.near(year=y, month=m, day=d, hour=h, minute=mi)
    print(f"query: {y:04d}-{m:02d}-{d:02d} {h:02d}:{mi:02d}")
    print_capture(item)
    return 0


def mode_snapshots(url: str, start: Optional[int], end: Optional[int], limit: int) -> int:
    """
    start/end:
      - keep it simple: accept year (e.g., 2018) or full timestamp string (e.g., 20180101000000)
      waybackpy docs show start_timestamp/end_timestamp can be year numbers. :contentReference[oaicite:1]{index=1}
    """
    cdx_kwargs = {}
    if start is not None:
        cdx_kwargs["start_timestamp"] = start
    if end is not None:
        cdx_kwargs["end_timestamp"] = end

    cdx = WaybackMachineCDXServerAPI(url, get_default_user_agent(), **cdx_kwargs)

    print("== snapshots ==")
    if start is not None or end is not None:
        print(f"range: start={start} end={end}")
    print(f"limit: {limit}")

    n = 0
    for item in cdx.snapshots():
        n += 1
        ts = getattr(item, "timestamp", "")
        sc = getattr(item, "statuscode", "")
        au = getattr(item, "archive_url", "")
        print(f"{n:04d}  {ts}  {sc}  {au}")
        if n >= limit:
            break

    if n == 0:
        print("(no snapshots found)")
    return 0


def mode_save(url: str) -> int:
    save_api = WaybackMachineSaveAPI(url, get_default_user_agent())
    saved_url = save_api.save()
    print("== save ==")
    print(f"saved_url   : {saved_url}")
    # cached_save indicates whether it was already saved recently
    if hasattr(save_api, "cached_save"):
        print(f"cached_save : {getattr(save_api, 'cached_save', None)}")
    if hasattr(save_api, "timestamp"):
        try:
            print(f"timestamp   : {save_api.timestamp()}")
        except Exception:
            pass
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Wayback Machine lookup via waybackpy")
    p.add_argument("url", help="Target URL (http/https)")
    p.add_argument("--mode", choices=["newest", "oldest", "near", "snapshots", "save"], default="newest")

    # near options
    p.add_argument("--year", type=int)
    p.add_argument("--month", type=int)
    p.add_argument("--day", type=int)
    p.add_argument("--hour", type=int)
    p.add_argument("--minute", type=int)
    p.add_argument("--wayback-ts", type=str, help="Wayback timestamp (YYYYMMDDhhmmss or similar)")
    p.add_argument("--unix-ts", type=int, help="Unix timestamp (seconds)")

    # snapshots options
    p.add_argument("--start", type=int, help="Start timestamp/year (e.g., 2018 or 20180101000000)")
    p.add_argument("--end", type=int, help="End timestamp/year (e.g., 2019 or 20191231235959)")
    p.add_argument("--limit", type=int, default=50, help="Max snapshots to print (default: 50)")

    return p.parse_args()


def main() -> int:
    args = parse_args()

    try:
        url = validate_url(args.url)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    try:
        if args.mode == "newest":
            return mode_newest(url)
        if args.mode == "oldest":
            return mode_oldest(url)
        if args.mode == "near":
            return mode_near(
                url,
                year=args.year, month=args.month, day=args.day,
                hour=args.hour, minute=args.minute,
                wayback_ts=args.wayback_ts,
                unix_ts=args.unix_ts,
            )
        if args.mode == "snapshots":
            return mode_snapshots(url, start=args.start, end=args.end, limit=args.limit)
        if args.mode == "save":
            return mode_save(url)

        print("error: unknown mode", file=sys.stderr)
        return 2

    except Exception as e:
        # waybackpy can raise various exceptions depending on network / IA responses / rate limiting
        print(f"error: waybackpy_failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()
