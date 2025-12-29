from __future__ import annotations

import time
from typing import Any, Dict, Optional

import orjson

from .storage_lmdb import LMDBStore


def _to_int_ts(ts: Any) -> int:
    t = int(ts)
    if t > 10_000_000_000:
        t //= 1000
    return t


def _price_key(condition_id: str, ts: int) -> str:
    return f"price:{condition_id}:{ts:010d}"


def compute_yes_price_proxy_from_recent_trades(store: LMDBStore, condition_id: str, lookback: int = 5000) -> Optional[float]:
    """
    Proxy yes_price computed from most recent trades:
      - if last trade outcome == Yes => yes_price = price
      - if last trade outcome == No  => yes_price = 1 - price
    If we can't find any, return None.
    """
    # Scan last trades by reading from end is hard in LMDB prefix scan; simplest:
    # scan prefix with limit and take the last element (works for MVP).
    # keys are time-sorted because timestamp is in key.
    prefix = f"trade:{condition_id}:"
    last_trade = None
    for _, v in store.scan_prefix(prefix, limit=lookback):
        last_trade = v
    if last_trade is None:
        return None
    t = orjson.loads(last_trade)
    outcome = t.get("outcome")
    price = t.get("price")
    if outcome not in ("Yes", "No"):
        return None
    try:
        p = float(price)
    except Exception:
        return None
    yes_price = p if outcome == "Yes" else (1.0 - p)
    # clamp
    if yes_price < 0.0:
        yes_price = 0.0
    if yes_price > 1.0:
        yes_price = 1.0
    return yes_price


def write_price_snap(store: LMDBStore, condition_id: str, ts: int, yes_price: float) -> None:
    store.put_json(_price_key(condition_id, ts), {"conditionId": condition_id, "ts": ts, "yes_price": yes_price})
    store.put_json(LMDBStore.k_last_price_ts(condition_id), ts)


def price_tick(store: LMDBStore, condition_id: str) -> Optional[float]:
    yes_price = compute_yes_price_proxy_from_recent_trades(store, condition_id)
    if yes_price is None:
        return None
    ts = int(time.time())
    write_price_snap(store, condition_id, ts, yes_price)
    return yes_price
