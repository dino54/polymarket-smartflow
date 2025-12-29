#!/usr/bin/env python3
from pathlib import Path
from pmsf.storage_lmdb import LMDBStore

def main() -> int:
    path = Path("./data/polymarket.lmdb")
    store = LMDBStore(path)
    try:
        store.put_json("test:hello", {"ok": True})
        print("get:", store.get_json("test:hello"))
        store.put_json("test:prefix:1", {"n": 1})
        store.put_json("test:prefix:2", {"n": 2})
        print("scan prefix:")
        for k, v in store.scan_prefix("test:prefix:"):
            print(" ", k, v)
        return 0
    finally:
        store.close()

if __name__ == "__main__":
    raise SystemExit(main())
