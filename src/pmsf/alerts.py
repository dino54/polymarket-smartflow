from __future__ import annotations

from typing import Any, Dict

from rich.console import Console

from .flow import smart_flow_market

console = Console()


def check_alert(flow: Dict[str, Any], threshold_usd: float) -> bool:
    return abs(float(flow.get("smart_net_usd", 0.0))) >= float(threshold_usd)


def run_alert_once(
    store,
    condition_id: str,
    window_sec: int,
    threshold_usd: float,
    smart_min_trades: int,
    smart_min_volume_usd: float,
    smart_score_threshold: float,
) -> bool:
    flow = smart_flow_market(
        store,
        condition_id,
        window_sec=window_sec,
        smart_min_trades=smart_min_trades,
        smart_min_volume_usd=smart_min_volume_usd,
        smart_score_threshold=smart_score_threshold,
    )

    if check_alert(flow, threshold_usd):
        console.print(
            f"[bold yellow]ALERT[/bold yellow] market={condition_id} "
            f"smart_net_usd={flow['smart_net_usd']:.2f} "
            f"smart_vol_usd={flow['smart_vol_usd']:.2f} "
            f"wallets={flow['smart_wallets']} trades={flow['smart_trades']} "
            f"window={window_sec}s"
        )
        return True

    console.print(
        f"[dim]no alert[/dim] market={condition_id} net={flow['smart_net_usd']:.2f} vol={flow['smart_vol_usd']:.2f}"
    )
    return False
