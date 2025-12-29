#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import sys
from typing import Any, Dict, List

import httpx

DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


def is_condition_id(s: str) -> bool:
    s = s.strip()
    if not (s.startswith("0x") and len(s) == 66):
        return False
    hexpart = s[2:]
    return all(c in "0123456789abcdefABCDEF" for c in hexpart)


def unix_to_iso(ts: int) -> str:
    if ts > 10_000_000_000:
        ts = ts // 1000
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).isoformat()


def resolve_condition_id_from_slug(client: httpx.Client, slug: str) -> str:
    r = client.get(f"{GAMMA_API}/markets/slug/{slug}", timeout=20)
    if r.status_code != 200:
        r = client.get(f"{GAMMA_API}/markets", params={"slug": slug}, timeout=20)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list) or not data:
            raise ValueError(f"Slug not found: {slug}")
        cid = data[0].get("conditionId") or data[0].get("condition_id")
    else:
        data = r.json()
        if isinstance(data, list):
            data = data[0]
        cid = data.get("conditionId") or data.get("condition_id")

    if not cid or not isinstance(cid, str) or not is_condition_id(cid):
        raise ValueError(f"Could not extract a valid conditionId from slug '{slug}'. Got: {cid}")
    return cid


def fetch_trades(client: httpx.Client, condition_id: str, limit: int, offset: int = 0) -> List[Dict[str, Any]]:
    r = client.get(
        f"{DATA_API}/trades",
        params={"market": condition_id, "limit": limit, "offset": offset, "takerOnly": "true"},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError("Unexpected response")
    return data


def main() -> int:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--condition-id")
    g.add_argument("--slug")
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--max-rows", type=int, default=50)
    args = p.parse_args()

    with httpx.Client(headers={"User-Agent": "pmsf-fetch/0.1"}) as client:
        if args.condition_id:
            cid = args.condition_id.strip()
        else:
            cid = resolve_condition_id_from_slug(client, args.slug.strip())

        trades = fetch_trades(client, cid, limit=args.limit, offset=args.offset)

        print(f"conditionId: {cid}")
        print(f"Returned {len(trades)} trades. Showing up to {min(args.max_rows, len(trades))}:\n")
        for t in trades[: args.max_rows]:
            wallet = t.get("proxyWallet") or t.get("user") or "?"
            side = t.get("side", "?")
            outcome = t.get("outcome", "?")
            size = t.get("size", "?")
            price = t.get("price", "?")
            ts = t.get("timestamp")
            when = unix_to_iso(int(ts)) if str(ts).isdigit() else str(ts)
            tx = t.get("transactionHash", "")
            print(f"{when} | {wallet} | {side:<4} {outcome} | size={size} price={price}" + (f" | tx={tx}" if tx else ""))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
