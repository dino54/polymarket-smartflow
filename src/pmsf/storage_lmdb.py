from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple

import lmdb
import orjson


def _enc(obj: Any) -> bytes:
    return orjson.dumps(obj)


def _dec(b: Optional[bytes]) -> Any:
    if b is None:
        return None
    return orjson.loads(b)


class LMDBStore:
    """
    Simple LMDB wrapper:
      - put/get bytes
      - put/get json
      - prefix scan iterator
      - batch write via write_txn context
    """

    def __init__(self, path: Path, map_size: int = 2 * 1024**3) -> None:
        # 2GB by default; adjust later if needed
        self.env = lmdb.open(
            str(path),
            map_size=map_size,
            subdir=True,
            create=True,
            lock=True,
            readahead=True,
            writemap=False,
            max_dbs=1,
        )

    def close(self) -> None:
        self.env.close()

    def put(self, key: str, value: bytes) -> None:
        with self.env.begin(write=True) as txn:
            txn.put(key.encode("utf-8"), value)

    def get(self, key: str) -> Optional[bytes]:
        with self.env.begin(write=False) as txn:
            return txn.get(key.encode("utf-8"))

    def put_json(self, key: str, obj: Any) -> None:
        self.put(key, _enc(obj))

    def get_json(self, key: str) -> Any:
        return _dec(self.get(key))

    def delete(self, key: str) -> None:
        with self.env.begin(write=True) as txn:
            txn.delete(key.encode("utf-8"))

    def now_ts(self) -> int:
        return int(time.time())

    def scan_prefix(self, prefix: str, limit: Optional[int] = None) -> Iterator[Tuple[str, bytes]]:
        pref = prefix.encode("utf-8")
        with self.env.begin(write=False) as txn:
            cur = txn.cursor()
            if not cur.set_range(pref):
                return
            n = 0
            for k, v in cur:
                if not k.startswith(pref):
                    break
                yield k.decode("utf-8"), v
                n += 1
                if limit is not None and n >= limit:
                    break

    def write_batch(self, items: Iterable[Tuple[str, bytes]]) -> None:
        with self.env.begin(write=True) as txn:
            for k, v in items:
                txn.put(k.encode("utf-8"), v)

    # Helpers for common keys
    @staticmethod
    def k_last_trade_ts(condition_id: str) -> str:
        return f"idx:market:{condition_id}:last_trade_ts"

    @staticmethod
    def k_last_price_ts(condition_id: str) -> str:
        return f"idx:market:{condition_id}:last_price_ts"
