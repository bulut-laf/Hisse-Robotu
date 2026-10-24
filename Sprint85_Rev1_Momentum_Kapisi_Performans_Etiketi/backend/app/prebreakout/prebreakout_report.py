from __future__ import annotations

import pandas as pd

from backend.app.prebreakout.prebreakout_backtest import (
    PreBreakoutReplayResult,
    PreBreakoutReplaySummary,
    performans_etiketi_belirle,
)


def replay_sonuclarini_tabloya_cevir(
    results: list[PreBreakoutReplayResult],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for result in results:
        row: dict[str, object] = {
            "symbol": result.symbol,
            "cutoff_date": result.cutoff_date.isoformat(),
            "score": result.analysis.score,
            "stage": result.analysis.stage.value,
            "stage_label": result.analysis.stage_label,
            "accepted": result.analysis.accepted,
            "late_entry": result.analysis.late_entry,
            "performance_label": performans_etiketi_belirle(result),
            "entry_close": result.entry_close,
        }

        for performance in result.forward:
            suffix = f"{performance.horizon}d"
            row[f"close_return_{suffix}_pct"] = performance.close_return_pct
            row[f"max_return_{suffix}_pct"] = performance.max_return_pct
            row[f"min_return_{suffix}_pct"] = performance.min_return_pct
            row[f"available_{suffix}"] = performance.available

        rows.append(row)

    return pd.DataFrame(rows)


def replay_ozetini_tabloya_cevir(
    summary: PreBreakoutReplaySummary,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "total_replays": summary.total_replays,
                "accepted_candidates": summary.accepted_candidates,
                "late_entry_count": summary.late_entry_count,
                "rejected_count": summary.rejected_count,
                "positive_5d_count": summary.positive_5d_count,
                "positive_5d_rate_pct": summary.positive_5d_rate_pct,
                "five_day_at_least_5_pct_count": (
                    summary.five_day_at_least_5_pct_count
                ),
                "five_day_at_least_5_pct_rate_pct": (
                    summary.five_day_at_least_5_pct_rate_pct
                ),
                "ten_day_at_least_5_pct_count": (
                    summary.ten_day_at_least_5_pct_count
                ),
                "ten_day_at_least_5_pct_rate_pct": (
                    summary.ten_day_at_least_5_pct_rate_pct
                ),
                "twenty_day_at_least_10_pct_count": (
                    summary.twenty_day_at_least_10_pct_count
                ),
                "twenty_day_at_least_10_pct_rate_pct": (
                    summary.twenty_day_at_least_10_pct_rate_pct
                ),
            }
        ]
    )
