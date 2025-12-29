from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

import orjson

from .features import trade_direction, trade_ts, trade_usd_abs
from .scorer import is_smart, wallet_key_stats
from .storage_lmdb import LMDBStore


def smart_flow_market(
    store: LMDBStore,
    condition_id: str,
    window_sec: int,
    smart_min_trades: int,
    smart_min_volume_usd: float,
    smart_score_threshold: float,
) -> Dict[str, Any]:
    """
    Compute smart wallets net flow (USD proxy) over last window_sec.
    For each trade in window:
      signed = direction_in_yes_space * (size*price)
    Also compute absolute smart volume.
    """
    now = int(time.time())
    start = now - window_sec

    prefix = f"trade:{condition_id}:"
    net_usd = 0.0
    vol_usd = 0.0
    smart_trades = 0
    smart_wallets_seen = set()

    for _, v in store.scan_prefix(prefix):
        t = orjson.loads(v)
        ts = trade_ts(t)
        if ts < start:
            continue
        if ts > now:
            continue

        wallet = (t.get("proxyWallet") or t.get("user") or "").lower()
        if not wallet.startswith("0x"):
            continue

        stats = store.get_json(wallet_key_stats(wallet))
        if not isinstance(stats, dict):
            continue
        if not is_smart(stats, smart_min_trades, smart_min_volume_usd, smart_score_threshold):
            continue

        d = trade_direction(t)
        usd = trade_usd_abs(t)
        net_usd += float(d) * float(usd)
        vol_usd += float(usd)
        smart_trades += 1
        smart_wallets_seen.add(wallet)

    return {
        "conditionId": condition_id,
        "ts": now,
        "window_sec": window_sec,
        "smart_net_usd": net_usd,
        "smart_vol_usd": vol_usd,
        "smart_trades": smart_trades,
        "smart_wallets": len(smart_wallets_seen),
    }
