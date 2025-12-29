# Polymarket Smart Flow (LMDB)

Local-first Python toolkit to track Polymarket markets, identify “smart money” wallets, and generate copy-style alerts on an **hourly horizon**, without running any database server.

This project is designed for **research, monitoring, and paper-trading first**.

---

## What this project does

- Tracks **trades (bets)** for ~100 Polymarket markets
- Stores everything locally using **LMDB** (fast embedded key-value store)
- Samples **price snapshots** over time (proxy pricing, see below)
- Computes a **smart-money score** per wallet based on timing edge
- Aggregates **smart net flow** per market
- Triggers **alerts** when smart flow crosses a configurable threshold

All components run locally, with minimal setup.

---

## High-level architecture

Trades (Data API)
↓
collector.py → LMDB (trades)
↓
pricer.py → LMDB (price snapshots)
↓
scorer.py → LMDB (wallet stats / smart score)
↓
flow.py → smart net flow (per market)
↓
alerts.py → console alerts (copy signals)

yaml
Copier le code

No database server, no cloud infrastructure.

---

## Project structure

polymarket-smartflow/
README.md
requirements.txt
pyproject.toml
.env.example
.gitignore

src/pmsf/
config.py
types.py
storage_lmdb.py
polymarket_client.py
universe.py
collector.py
pricer.py
features.py
scorer.py
flow.py
alerts.py
cli.py

scripts/
fetch_market_trades.py
market_wallets.py
smoke_lmdb.py

data/
polymarket.lmdb/ # created automatically (not versioned)
logs/

yaml
Copier le code

---

## Smart money definition (v1)

**Goal**: identify wallets that consistently enter trades **before favorable price moves** on an hourly horizon.

For each trade at time `t`:

- Compute a **proxy YES price** at `t`
- Measure price change after:
  - **1 hour**
  - **4 hours**
- Edge = `(price(t + horizon) - price(t)) × direction`

Wallet score:

score = 0.6 × mean(edge_1h) + 0.4 × mean(edge_4h)

yaml
Copier le code

A wallet is considered **smart** if:
- minimum number of trades
- minimum traded volume (USD proxy)
- score above a threshold

This is a **timing-based smart money definition**, not final PnL.

---

## Pricing model (important)

Polymarket does not expose a single, stable “mid price” endpoint for all markets.

### In this MVP:
- `pricer.py` computes a **proxy YES price** from the **most recent trade**
- If last trade is `BUY Yes @ p` → YES price = `p`
- If last trade is `BUY No @ p`  → YES price = `1 - p`
- Price snapshots are written every `N` seconds (default: 60s)

This approach is intentionally simple and sufficient for **hourly edge detection**.

---

## Installation

### Requirements
- Python **3.10+** (3.11 recommended)
- macOS / Linux / Windows

### Setup

```bash
git clone <your-repo-url>
cd polymarket-smartflow

python -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
cp .env.example .env
Quick tests (recommended)
1) Test LMDB
bash
Copier le code
python scripts/smoke_lmdb.py
2) Fetch trades for a single market
bash
Copier le code
python scripts/fetch_market_trades.py \
  --slug will-anyone-be-charged-over-daycare-fraud-in-minnesota \
  --limit 200
3) Aggregate wallet exposure (no LMDB)
bash
Copier le code
python scripts/market_wallets.py \
  --slug will-anyone-be-charged-over-daycare-fraud-in-minnesota \
  --limit 500
Running the full pipeline (100 markets)
1) Build the market universe
Select the top markets by volume/liquidity.

bash
Copier le code
pmsf universe --size 100 --out ./data/universe.json
2) Backfill trades
Fetch historical trades for all markets.

bash
Copier le code
pmsf collect \
  --universe ./data/universe.json \
  --mode backfill \
  --pages 10 \
  --limit 200
3) Start price sampling (run continuously)
Writes proxy YES prices every 60 seconds.

bash
Copier le code
pmsf price \
  --universe ./data/universe.json \
  --interval 60
4) Compute smart-money scores
Run after price snapshots have accumulated (≥ 1 hour recommended).

bash
Copier le code
pmsf score \
  --universe ./data/universe.json \
  --windows 3600,14400
5) Run smart-flow alerts
Detect strong smart-money flow on an hourly window.

bash
Copier le code
pmsf alerts \
  --universe ./data/universe.json \
  --window 3600 \
  --threshold 20000 \
  --interval 60
Environment variables (.env)
Main parameters (defaults shown):

bash
Copier le code
PMSF_LMDB_PATH=./data/polymarket.lmdb
PMSF_UNIVERSE_SIZE=100

PMSF_PRICE_INTERVAL_SEC=60
PMSF_SCORE_WINDOWS=3600,14400

PMSF_SMART_MIN_TRADES=25
PMSF_SMART_MIN_VOLUME_USD=2000
PMSF_SMART_SCORE_THRESHOLD=0.002

PMSF_ALERT_WINDOW_SEC=3600
PMSF_ALERT_THRESHOLD_USD=20000
Current limitations (MVP)
Price is a proxy, not a full order-book mid price

Live collection uses polling, not WebSockets

Scoring is not idempotent (reprocesses trades)

No wallet clustering / Sybil detection

Alerts are console-only

These are deliberate trade-offs to keep the system simple and debuggable.

Roadmap
 Idempotent scoring cursors

 Order-book based pricing (CLOB)

 Market-maker detection & filtering

 Wallet clustering (Sybil)

 Paper trading simulator

 Execution module (optional, after validation)

Disclaimer
This software is for research and educational purposes only.
It is not financial advice. Prediction markets involve risk, and automated copying can lose money due to latency, slippage, and liquidity constraints.