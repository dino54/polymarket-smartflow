from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Side = Literal["BUY", "SELL"]
Outcome = Literal["Yes", "No"]


@dataclass(frozen=True)
class Trade:
    condition_id: str
    timestamp: int  # unix seconds
    wallet: str
    side: Side
    outcome: Outcome
    size: float
    price: float
    tx: Optional[str] = None
    title: Optional[str] = None


@dataclass(frozen=True)
class PriceSnap:
    condition_id: str
    timestamp: int  # unix seconds
    yes_price: float  # proxy yes price in [0,1]


@dataclass(frozen=True)
class WalletStats:
    wallet: str
    n_trades: int
    volume_usd: float
    score: float
    score_1h: float
    score_4h: float
