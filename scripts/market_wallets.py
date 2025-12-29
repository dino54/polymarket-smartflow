#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Any, Dict, List, Tuple

import httpx

DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


def resolve_condition_id_from_slug(client: httpx.Client, slug: str) -> str:
    r = client.get(f"{GAMMA_API}/markets/slug/{slug}", timeout=20)
    if r.status_code != 200:
        r = client.get(f"{GAMMA_API}/markets", params={"slug": slug}, timeout=20)
        r.raise_for_status()
        data = r.json()
        cid = data[0].get("conditionId") if data else None
    else:
        data = r.json()
        if isinstance(data, list):
            data = data[0]
        cid = data.get("conditionId")
    if not cid:
        raise ValueError("Could not resolve conditionId")
    return cid


def fetch_trades(client: httpx.Client, condition_id: str, limit: int) -> List[Dict[str, Any]]:
    r = client.get(f"{DATA_API}/trades", params={"market": condition_id, "limit": limit, "offset": 0, "takerOnly": "true"})
    r.raise_for_status()
    return r.json()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True)
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--top", type=int, default=15)
    args = p.parse_args()

    with httpx.Client(headers={"User-Agent": "pmsf-wallets/0.1"}) as client:
        cid = resolve_condition_id_from_slug(client, args.slug)
        trades = fetch_trades(client, cid, args.limit)

    # net exposure in shares (simple)
    net_yes = defaultdict(float)
    net_no = defaultdict(float)
    vol = defaultdict(float)
    ntr = defaultdict(int)

    for t in trades:
        w = (t.get("proxyWallet") or t.get("user") or "").lower()
        if not w.startswith("0x"):
            continue
        side = t.get("side")
        outcome = t.get("outcome")
        try:
            size = float(t.get("size"))
            price = float(t.get("price"))
        except Exception:
            continue

        if outcome == "Yes":
            net_yes[w] += size if side == "BUY" else -size
        elif outcome == "No":
            net_no[w] += size if side == "BUY" else -size
        vol[w] += abs(size * price)
        ntr[w] += 1

    rows: List[Tuple[str, float, float, float, int]] = []
    for w in vol:
        rows.append((w, net_yes[w], net_no[w], vol[w], ntr[w]))

    rows.sort(key=lambda x: x[3], reverse=True)

    print(f"market slug={args.slug}")
    print(f"conditionId={cid}")
    print(f"trades={len(trades)}\n")
    print(f"{'wallet':42}  {'net_yes':>10}  {'net_no':>10}  {'vol_usd':>12}  {'n':>5}")
    print("-" * 90)
    for w, ny, nn, v, n in rows[: args.top]:
        print(f"{w:42}  {ny:10.2f}  {nn:10.2f}  {v:12.2f}  {n:5d}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
