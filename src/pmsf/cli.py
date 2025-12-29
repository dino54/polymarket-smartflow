from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any, Dict, List

import orjson
from rich.console import Console

from .config import load_settings
from .storage_lmdb import LMDBStore
from .universe import select_universe
from .collector import backfill_market, poll_live_once
from .pricer import price_tick
from .scorer import score_market
from .alerts import run_alert_once

console = Console()


def _load_universe(path: Path) -> List[Dict[str, Any]]:
    obj = orjson.loads(path.read_bytes())
    return obj["markets"]


def cmd_universe(args: argparse.Namespace) -> int:
    s = load_settings()
    out = Path(args.out or s.universe_out)
    uni = select_universe(size=int(args.size or s.universe_size), out_path=out)
    console.print(f"[green]Universe written[/green] {out} ({len(uni)} markets)")
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    s = load_settings()
    store = LMDBStore(s.lmdb_path)
    try:
        uni = _load_universe(Path(args.universe))
        pages = int(args.pages or s.backfill_pages)
        limit = int(args.limit or s.trade_limit)

        if args.mode == "backfill":
            for m in uni:
                cid = m["conditionId"]
                console.print(f"[cyan]backfill[/cyan] {cid} {m.get('slug','')}")
                backfill_market(store, cid, pages=pages, limit=limit)
            return 0

        # live polling
        interval = float(args.interval or 20.0)
        while True:
            for m in uni:
                cid = m["conditionId"]
                poll_live_once(store, cid, limit=limit)
            time.sleep(interval)
    finally:
        store.close()


def cmd_price(args: argparse.Namespace) -> int:
    s = load_settings()
    store = LMDBStore(s.lmdb_path)
    try:
        uni = _load_universe(Path(args.universe))
        interval = int(args.interval or s.price_interval_sec)

        while True:
            for m in uni:
                cid = m["conditionId"]
                p = price_tick(store, cid)
                if p is not None:
                    console.print(f"[dim]price[/dim] {cid} yes_price~{p:.4f}")
            time.sleep(interval)
    finally:
        store.close()


def cmd_score(args: argparse.Namespace) -> int:
    s = load_settings()
    store = LMDBStore(s.lmdb_path)
    try:
        uni = _load_universe(Path(args.universe))
        windows = [int(x) for x in (args.windows.split(",") if args.windows else s.score_windows)]

        for m in uni:
            cid = m["conditionId"]
            seen, edges = score_market(store, cid, windows=windows)
            console.print(f"[magenta]score[/magenta] {cid} trades_seen={seen} edges={edges}")
        return 0
    finally:
        store.close()


def cmd_alerts(args: argparse.Namespace) -> int:
    s = load_settings()
    store = LMDBStore(s.lmdb_path)
    try:
        uni = _load_universe(Path(args.universe))
        window_sec = int(args.window or s.alert_window_sec)
        threshold = float(args.threshold or s.alert_threshold_usd)

        while True:
            for m in uni:
                cid = m["conditionId"]
                run_alert_once(
                    store,
                    condition_id=cid,
                    window_sec=window_sec,
                    threshold_usd=threshold,
                    smart_min_trades=s.smart_min_trades,
                    smart_min_volume_usd=s.smart_min_volume_usd,
                    smart_score_threshold=s.smart_score_threshold,
                )
            time.sleep(float(args.interval or 60.0))
    finally:
        store.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pmsf", description="Polymarket Smart Flow (LMDB) - MVP")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_u = sub.add_parser("universe", help="Build a universe (top N markets) and write data/universe.json")
    p_u.add_argument("--size", type=int, default=None)
    p_u.add_argument("--out", type=str, default=None)
    p_u.set_defaults(fn=cmd_universe)

    p_c = sub.add_parser("collect", help="Collect trades into LMDB (backfill or live polling)")
    p_c.add_argument("--universe", type=str, required=True)
    p_c.add_argument("--mode", choices=["backfill", "live"], default="backfill")
    p_c.add_argument("--pages", type=int, default=None)
    p_c.add_argument("--limit", type=int, default=None)
    p_c.add_argument("--interval", type=float, default=20.0, help="live polling interval seconds")
    p_c.set_defaults(fn=cmd_collect)

    p_p = sub.add_parser("price", help="Write proxy yes-price snapshots into LMDB")
    p_p.add_argument("--universe", type=str, required=True)
    p_p.add_argument("--interval", type=int, default=None)
    p_p.set_defaults(fn=cmd_price)

    p_s = sub.add_parser("score", help="Compute wallet scores from stored trades + price snaps")
    p_s.add_argument("--universe", type=str, required=True)
    p_s.add_argument("--windows", type=str, default=None, help="comma list seconds e.g. 3600,14400")
    p_s.set_defaults(fn=cmd_score)

    p_a = sub.add_parser("alerts", help="Compute smart flow and alert on threshold")
    p_a.add_argument("--universe", type=str, required=True)
    p_a.add_argument("--window", type=int, default=None)
    p_a.add_argument("--threshold", type=float, default=None)
    p_a.add_argument("--interval", type=float, default=60.0)
    p_a.set_defaults(fn=cmd_alerts)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    rc = args.fn(args)
    raise SystemExit(rc)
