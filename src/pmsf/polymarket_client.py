from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


def is_condition_id(s: str) -> bool:
    s = s.strip()
    if not (s.startswith("0x") and len(s) == 66):
        return False
    hexpart = s[2:]
    return all(c in "0123456789abcdefABCDEF" for c in hexpart)


class PolymarketClient:
    def __init__(self, timeout_sec: float = 20.0) -> None:
        self.client = httpx.Client(headers={"User-Agent": "pmsf/0.1"}, timeout=timeout_sec)

    def close(self) -> None:
        self.client.close()

    # -------- Gamma API --------
    def market_by_slug(self, slug: str) -> Dict[str, Any]:
        # try /markets/slug/{slug}, fallback /markets?slug=
        r = self.client.get(f"{GAMMA_API}/markets/slug/{slug}")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data[0]
            if isinstance(data, dict):
                return data
        # fallback
        r2 = self.client.get(f"{GAMMA_API}/markets", params={"slug": slug})
        r2.raise_for_status()
        data2 = r2.json()
        if not isinstance(data2, list) or not data2:
            raise ValueError(f"Slug not found: {slug}")
        return data2[0]

    def resolve_condition_id(self, slug: str) -> str:
        m = self.market_by_slug(slug)
        cid = m.get("conditionId") or m.get("condition_id")
        if not isinstance(cid, str) or not is_condition_id(cid):
            raise ValueError(f"Could not resolve conditionId for slug={slug}. Got: {cid}")
        return cid

    def list_markets(self, limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
        # Gamma /markets returns a list; supports limit/offset on many deployments
        params = {"limit": limit, "offset": offset}
        r = self.client.get(f"{GAMMA_API}/markets", params=params)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected /markets response type: {type(data)}")
        return data

    # -------- Data API --------
    def fetch_trades(self, condition_id: str, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        params = {
            "market": condition_id,
            "limit": limit,
            "offset": offset,
            "takerOnly": "true",
        }
        r = self.client.get(f"{DATA_API}/trades", params=params)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected /trades response type: {type(data)}")
        return data

    def fetch_trades_multi(self, condition_ids: List[str], limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        params = {
            "market": ",".join(condition_ids),
            "limit": limit,
            "offset": offset,
            "takerOnly": "true",
        }
        r = self.client.get(f"{DATA_API}/trades", params=params)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected /trades response type: {type(data)}")
        return data
