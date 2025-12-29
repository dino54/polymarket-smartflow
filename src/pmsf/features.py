from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import orjson

from .storage_lmdb import LMDBStore


def trade_direction(trade: Dict[str, Any]) -> int:
    """
    Direction in YES-price space:
      - BUY Yes  -> +1
      - SELL Yes -> -1
      - BUY No   -> -1  (buying No implies betting yes_price down)
      - SELL No  -> +1
    """
    side = trade.get("side")
    outcome = trade.get("outcome")
    if side not in ("BUY", "SELL") or outcome not in ("Yes", "No"):
        return 0
    if outcome == "Yes":
        return 1 if side == "BUY" else -1
    # outcome == "No"
    return -1 if side == "BUY" else 1


def trade_usd_abs(trade: Dict[str, Any]) -> float:
    try:
        size = float(trade.get("size"))
        price = float(trade.get("price"))
        return abs(size * price)
    except Exception:
        return 0.0


def trade_ts(trade: Dict[str, Any]) -> int:
    ts = int(trade.get("timestamp") or 0)
    if ts > 10_000_000_000:
        ts //= 1000
    return ts


def get_yes_price_at_or_after(store: LMDBStore, condition_id: str, target_ts: int) -> Optional[float]:
    """
    Find the first price snapshot at or after target_ts.
    Keys: price:{cid}:{ts:010d}
    """
    prefix = f"price:{condition_id}:"
    # start from "price:cid:target_ts"
    start_key = f"{prefix}{target_ts:010d}"
    for k, v in store.scan_prefix(prefix):
        if k < start_key:
            continue
        obj = orjson.loads(v)
        try:
            return float(obj["yes_price"])
        except Exception:
            return None
    return None


def edge_for_trade(store: LMDBStore, condition_id: str, trade: Dict[str, Any], horizon_sec: int) -> Optional[float]:
    t0 = trade_ts(trade)
    p0_yes = None
    # p0 computed from trade itself
    try:
        price = float(trade.get("price"))
        outcome = trade.get("outcome")
        if outcome == "Yes":
            p0_yes = price
        elif outcome == "No":
            p0_yes = 1.0 - price
    except Exception:
        return None
    if p0_yes is None:
        return None

    p1_yes = get_yes_price_at_or_after(store, condition_id, t0 + horizon_sec)
    if p1_yes is None:
        return None

    d = trade_direction(trade)
    if d == 0:
        return None

    return (p1_yes - p0_yes) * float(d)
