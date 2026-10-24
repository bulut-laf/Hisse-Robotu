from __future__ import annotations

import pandas as pd

from backend.app.prebreakout.prebreakout_validation import (
    PreBreakoutValidationRecord,
    PreBreakoutValidationSummary,
)


def dogrulama_kayitlarini_tabloya_cevir(
    records: tuple[PreBreakoutValidationRecord, ...],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for record in records:
        analysis = record.replay.analysis
        features = analysis.features

        row: dict[str, object] = {
            "symbol": record.symbol,
            "cutoff_date": record.cutoff_date.isoformat(),
            "score": analysis.score,
            "stage": analysis.stage.value,
            "stage_label": analysis.stage_label,
            "accepted": analysis.accepted,
            "late_entry": analysis.late_entry,
            "performance_label": record.performance_label,
            "entry_close": record.replay.entry_close,
            "rsi14": None if features is None else features.rsi14,
            "macd_histogram_slope": (
                None if features is None else features.macd_histogram_egimi
            ),
            "resistance_distance_pct": (
                None if features is None else features.direnc_uzaklik_pct
            ),
            "volume_ratio_3_10": (
                None if features is None else features.hacim_orani_3_10
            ),
            "risk_reward": (
                None if features is None else features.risk_odul
            ),
        }

        for performance in record.replay.forward:
            suffix = f"{performance.horizon}d"
            row[f"close_return_{suffix}_pct"] = (
                performance.close_return_pct
            )
            row[f"max_return_{suffix}_pct"] = (
                performance.max_return_pct
            )
            row[f"min_return_{suffix}_pct"] = (
                performance.min_return_pct
            )
            row[f"available_{suffix}"] = performance.available

        rows.append(row)

    return pd.DataFrame(rows)


def dogrulama_ozetini_tabloya_cevir(
    summary: PreBreakoutValidationSummary,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "total_replays": summary.total_replays,
                "score_threshold_passed": summary.score_threshold_passed,
                "accepted_candidates": summary.accepted_candidates,
                "successful": summary.successful,
                "limited_move": summary.limited_move,
                "false_positive": summary.false_positive,
                "late_entry": summary.late_entry,
                "insufficient_data": summary.insufficient_data,
                "not_candidate": summary.not_candidate,
                "success_rate_pct": summary.success_rate_pct,
                "false_positive_rate_pct": (
                    summary.false_positive_rate_pct
                ),
            }
        ]
    )


def asama_bazli_ozet(
    records: tuple[PreBreakoutValidationRecord, ...],
) -> pd.DataFrame:
    table = dogrulama_kayitlarini_tabloya_cevir(records)
    if table.empty:
        return pd.DataFrame(
            columns=[
                "stage",
                "count",
                "successful",
                "false_positive",
                "success_rate_pct",
            ]
        )

    grouped_rows: list[dict[str, object]] = []
    for stage, group in table.groupby("stage", sort=True):
        evaluated = group[
            group["performance_label"].isin(
                ["Başarılı", "Sınırlı hareket", "Yanlış pozitif"]
            )
        ]
        successful = int(
            (evaluated["performance_label"] == "Başarılı").sum()
        )
        false_positive = int(
            (evaluated["performance_label"] == "Yanlış pozitif").sum()
        )
        denominator = len(evaluated)
        grouped_rows.append(
            {
                "stage": stage,
                "count": len(group),
                "successful": successful,
                "false_positive": false_positive,
                "success_rate_pct": (
                    successful / denominator * 100.0
                    if denominator
                    else 0.0
                ),
            }
        )

    return pd.DataFrame(grouped_rows)
