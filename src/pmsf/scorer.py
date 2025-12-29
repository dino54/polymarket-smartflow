from __future__ import annotations

from typing import Any, Dict, List, Tuple

import orjson

from .features import edge_for_trade, trade_usd_abs
from .storage_lmdb import LMDBStore


def wallet_key_stats(wallet: str) -> str:
    return f"wallet:{wallet}:stats"


def is_smart(stats: Dict[str, Any], min_trades: int, min_vol_usd: float, score_threshold: float) -> bool:
    return (
        int(stats.get("n_trades", 0)) >= min_trades
        and float(stats.get("volume_usd", 0.0)) >= min_vol_usd
        and float(stats.get("score", 0.0)) >= score_threshold
    )


def update_wallet_stats(store: LMDBStore, wallet: str, delta: Dict[str, Any]) -> Dict[str, Any]:
    cur = store.get_json(wallet_key_stats(wallet)) or {
        "wallet": wallet,
        "n_trades": 0,
        "volume_usd": 0.0,
        "sum_edge_1h": 0.0,
        "cnt_edge_1h": 0,
        "sum_edge_4h": 0.0,
        "cnt_edge_4h": 0,
        "score_1h": 0.0,
        "score_4h": 0.0,
        "score": 0.0,
    }

    cur["n_trades"] = int(cur["n_trades"]) + int(delta.get("n_trades", 0))
    cur["volume_usd"] = float(cur["volume_usd"]) + float(delta.get("volume_usd", 0.0))

    cur["sum_edge_1h"] = float(cur["sum_edge_1h"]) + float(delta.get("sum_edge_1h", 0.0))
    cur["cnt_edge_1h"] = int(cur["cnt_edge_1h"]) + int(delta.get("cnt_edge_1h", 0))

    cur["sum_edge_4h"] = float(cur["sum_edge_4h"]) + float(delta.get("sum_edge_4h", 0.0))
    cur["cnt_edge_4h"] = int(cur["cnt_edge_4h"]) + int(delta.get("cnt_edge_4h", 0))

    cur["score_1h"] = (float(cur["sum_edge_1h"]) / max(1, int(cur["cnt_edge_1h"])))
    cur["score_4h"] = (float(cur["sum_edge_4h"]) / max(1, int(cur["cnt_edge_4h"])))
    cur["score"] = 0.6 * cur["score_1h"] + 0.4 * cur["score_4h"]

    store.put_json(wallet_key_stats(wallet), cur)
    return cur


def score_market(store: LMDBStore, condition_id: str, windows: List[int]) -> Tuple[int, int]:
    """
    Iterate trades for the market and update wallet stats.
    MVP behavior: processes ALL trades found (idempotency not perfect).
    We'll improve with per-market scoring cursor later.
    Returns: (trades_seen, edges_computed)
    """
    prefix = f"trade:{condition_id}:"
    trades_seen = 0
    edges_done = 0

    for _, v in store.scan_prefix(prefix):
        trade = orjson.loads(v)
        trades_seen += 1
        wallet = (trade.get("proxyWallet") or trade.get("user") or "").lower()
        if not wallet.startswith("0x"):
            continue

        vol = trade_usd_abs(trade)
        delta = {"n_trades": 1, "volume_usd": vol}

        # compute edges for 1h/4h if possible (needs price snapshots after horizons)
        # windows are seconds; we only use first two as 1h/4h in this MVP.
        if len(windows) >= 1:
            e1 = edge_for_trade(store, condition_id, trade, windows[0])
            if e1 is not None:
                delta["sum_edge_1h"] = float(delta.get("sum_edge_1h", 0.0)) + float(e1)
                delta["cnt_edge_1h"] = int(delta.get("cnt_edge_1h", 0)) + 1
                edges_done += 1
        if len(windows) >= 2:
            e4 = edge_for_trade(store, condition_id, trade, windows[1])
            if e4 is not None:
                delta["sum_edge_4h"] = float(delta.get("sum_edge_4h", 0.0)) + float(e4)
                delta["cnt_edge_4h"] = int(delta.get("cnt_edge_4h", 0)) + 1
                edges_done += 1

        update_wallet_stats(store, wallet, delta)

    return trades_seen, edges_done
