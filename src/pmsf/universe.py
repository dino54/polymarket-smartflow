from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import orjson

from .polymarket_client import PolymarketClient, is_condition_id


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def select_universe(size: int, out_path: Path) -> List[Dict[str, Any]]:
    """
    Select ~N markets using Gamma /markets list.
    Heuristic: sort by volume (if present) then by liquidity-ish fields if available.
    The field names can vary; we handle common ones.
    """
    client = PolymarketClient()
    try:
        markets: List[Dict[str, Any]] = []
        offset = 0
        page = 500
        # Pull a few pages; adjust later
        for _ in range(5):
            chunk = client.list_markets(limit=page, offset=offset)
            if not chunk:
                break
            markets.extend(chunk)
            offset += page

        cleaned: List[Dict[str, Any]] = []
        for m in markets:
            cid = m.get("conditionId") or m.get("condition_id")
            slug = m.get("slug")
            title = m.get("title")
            if not (isinstance(cid, str) and is_condition_id(cid)):
                continue
            if not isinstance(slug, str):
                slug = ""
            vol = (
                _safe_float(m.get("volume24hr"))
                or _safe_float(m.get("volume24h"))
                or _safe_float(m.get("volume"))
                or _safe_float(m.get("volumeUSD"))
            )
            liq = _safe_float(m.get("liquidity")) or _safe_float(m.get("liquidityUSD"))
            cleaned.append(
                {
                    "conditionId": cid,
                    "slug": slug,
                    "title": title or "",
                    "volume": vol,
                    "liquidity": liq,
                }
            )

        cleaned.sort(key=lambda x: (x["volume"], x["liquidity"]), reverse=True)
        uni = cleaned[:size]

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(orjson.dumps({"size": size, "markets": uni}, option=orjson.OPT_INDENT_2))
        return uni
    finally:
        client.close()
