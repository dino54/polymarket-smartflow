from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _get_env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


def _get_int(name: str, default: int) -> int:
    v = _get_env(name, str(default))
    return int(v)


def _get_float(name: str, default: float) -> float:
    v = _get_env(name, str(default))
    return float(v)


def _get_list_int(name: str, default: str) -> List[int]:
    v = _get_env(name, default)
    parts = [p.strip() for p in v.split(",") if p.strip()]
    return [int(p) for p in parts]


@dataclass(frozen=True)
class Settings:
    lmdb_path: Path
    log_dir: Path

    universe_size: int
    universe_out: Path

    trade_limit: int
    backfill_pages: int

    price_interval_sec: int
    score_windows: List[int]

    smart_min_trades: int
    smart_min_volume_usd: float
    smart_score_threshold: float

    alert_window_sec: int
    alert_threshold_usd: float


def load_settings() -> Settings:
    lmdb_path = Path(_get_env("PMSF_LMDB_PATH", "./data/polymarket.lmdb"))
    log_dir = Path(_get_env("PMSF_LOG_DIR", "./data/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    lmdb_path.parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        lmdb_path=lmdb_path,
        log_dir=log_dir,
        universe_size=_get_int("PMSF_UNIVERSE_SIZE", 100),
        universe_out=Path(_get_env("PMSF_UNIVERSE_OUT", "./data/universe.json")),
        trade_limit=_get_int("PMSF_TRADE_LIMIT", 200),
        backfill_pages=_get_int("PMSF_BACKFILL_PAGES", 10),
        price_interval_sec=_get_int("PMSF_PRICE_INTERVAL_SEC", 60),
        score_windows=_get_list_int("PMSF_SCORE_WINDOWS", "3600,14400"),
        smart_min_trades=_get_int("PMSF_SMART_MIN_TRADES", 25),
        smart_min_volume_usd=_get_float("PMSF_SMART_MIN_VOLUME_USD", 2000.0),
        smart_score_threshold=_get_float("PMSF_SMART_SCORE_THRESHOLD", 0.002),
        alert_window_sec=_get_int("PMSF_ALERT_WINDOW_SEC", 3600),
        alert_threshold_usd=_get_float("PMSF_ALERT_THRESHOLD_USD", 20000.0),
    )
