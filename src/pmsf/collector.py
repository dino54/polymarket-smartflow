from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Tuple

import orjson

from .storage_lmdb import LMDBStore
from .polymarket_client import PolymarketClient


def _to_int_ts(ts: Any) -> int:
    # Data API timestamps are usually seconds; handle ms too
    if ts is None:
        return 0
    t = int(ts)
    if t > 10_000_000_000:
        t //= 1000
    return t


def _trade_key(condition_id: str, ts: int, seq: int) -> str:
    return f"trade:{condition_id}:{ts:010d}:{seq:06d}"


def ingest_trades(store: LMDBStore, condition_id: str, trades: List[Dict[str, Any]]) -> int:
    """
    Append trades to LMDB. Returns max timestamp ingested.
    """
    items: List[Tuple[str, bytes]] = []
    max_ts = 0
    for i, t in enumerate(trades):
        ts = _to_int_ts(t.get("timestamp"))
        if ts <= 0:
            continue
        max_ts = max(max_ts, ts)
        key = _trade_key(condition_id, ts, i)
        items.append((key, orjson.dumps(t)))
    if items:
        store.write_batch(items)
        store.put_json(LMDBStore.k_last_trade_ts(condition_id), max_ts)
    return max_ts


def backfill_market(
    store: LMDBStore,
    condition_id: str,
    pages: int,
    limit: int,
    sleep_sec: float = 0.2,
) -> None:
    client = PolymarketClient()
    try:
        for page in range(pages):
            offset = page * limit
            trades = client.fetch_trades(condition_id, limit=limit, offset=offset)
            if not trades:
                break
            ingest_trades(store, condition_id, trades)
            time.sleep(sleep_sec)
    finally:
        client.close()


def poll_live_once(
    store: LMDBStore,
    condition_id: str,
    limit: int,
) -> int:
    """
    Simple live mode (polling): fetch latest trades page and store only new ones by timestamp.
    This is not perfect but good enough to start.
    """
    last_ts = store.get_json(LMDBStore.k_last_trade_ts(condition_id)) or 0
    client = PolymarketClient()
    try:
        trades = client.fetch_trades(condition_id, limit=limit, offset=0)
        # Keep only trades newer than last_ts
        new_trades = [t for t in trades if _to_int_ts(t.get("timestamp")) > int(last_ts)]
        if new_trades:
            return ingest_trades(store, condition_id, new_trades)
        return int(last_ts)
    finally:
        client.close()
