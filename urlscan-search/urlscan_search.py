#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import urlscan


def load_config():
    file_path = "/home/ubuntu/.openclaw/api_config.json"
    with open(file_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("api_token", {}).get("urlscan-search", {}).get("api_key", "")

def print_title(s: str) -> None:
    print(s)
    print("-" * 80)


def main() -> int:
    ap = argparse.ArgumentParser(description="urlscan.io client via urlscan-python")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="scan a URL")
    p_scan.add_argument("url", help="target URL")
    p_scan.add_argument("--visibility", choices=["public", "unlisted", "private"], default="unlisted")
    p_scan.add_argument("--no-wait", action="store_true", help="do not wait for result")
    p_scan.add_argument("--json", action="store_true", help="print raw JSON")

    p_search = sub.add_parser("search", help="search scans")
    p_search.add_argument("query", help='search query, e.g. "page.domain:example.com"')
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--json", action="store_true", help="print raw JSON")

    p_get = sub.add_parser("get", help="get result by uuid")
    p_get.add_argument("uuid", help="scan uuid")
    p_get.add_argument("--json", action="store_true", help="print raw JSON")

    args = ap.parse_args()

    try:
        api_key = load_config()
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    client = urlscan.Client(api_key)

    try:
        if args.cmd == "scan":
            if not args.no_wait and hasattr(client, "scan_and_get_result"):
                result = client.scan_and_get_result(args.url, visibility=args.visibility)
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print_title(f"[urlscan] scan url={args.url} visibility={args.visibility}")
                    page = result.get("page") or {}
                    task = result.get("task") or {}
                    print(f"uuid: {task.get('uuid') or result.get('uuid')}")
                    print(f"time: {task.get('time')}")
                    print(f"page.url: {page.get('url')}")
                    print(f"page.domain: {page.get('domain')}")
                    print(f"page.ip: {page.get('ip')}")
                return 0

            # fallback scan -> (optional) wait -> get
            res = client.scan(args.url, visibility=args.visibility)
            uuid = res.get("uuid")
            if args.no_wait or not uuid:
                if args.json:
                    print(json.dumps(res, ensure_ascii=False, indent=2))
                else:
                    print_title(f"[urlscan] scan submitted url={args.url} visibility={args.visibility}")
                    print(f"uuid: {uuid}")
                    print(f"result: {res}")
                return 0

            client.wait_for_result(uuid)
            result = client.get_result(uuid)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print_title(f"[urlscan] scan url={args.url} uuid={uuid}")
                page = result.get("page") or {}
                task = result.get("task") or {}
                print(f"time: {task.get('time')}")
                print(f"page.url: {page.get('url')}")
                print(f"page.domain: {page.get('domain')}")
                print(f"page.ip: {page.get('ip')}")
            return 0

        if args.cmd == "search":
            out = []
            i = 0
            for r in client.search(args.query):
                out.append(r)
                i += 1
                if i >= args.limit:
                    break
            if args.json:
                print(json.dumps({"query": args.query, "results": out}, ensure_ascii=False, indent=2))
            else:
                print_title(f"[urlscan] search query={args.query} limit={args.limit}")
                print(f"results: {len(out)}")
                for r in out:
                    _id = r.get("_id") or r.get("uuid") or (r.get("task") or {}).get("uuid")
                    page = r.get("page") or {}
                    task = r.get("task") or {}
                    print(f"- id={_id} time={task.get('time')} url={page.get('url')} domain={page.get('domain')}")
            return 0

        if args.cmd == "get":
            result = client.get_result(args.uuid)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print_title(f"[urlscan] get uuid={args.uuid}")
                page = result.get("page") or {}
                task = result.get("task") or {}
                print(f"time: {task.get('time')}")
                print(f"page.url: {page.get('url')}")
                print(f"page.domain: {page.get('domain')}")
                print(f"page.ip: {page.get('ip')}")
                print(f"keys: {list(result.keys())[:20]}")
            return 0

        print("error: unknown command", file=sys.stderr)
        return 2

    except Exception as e:
        print(f"error: urlscan_failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()
