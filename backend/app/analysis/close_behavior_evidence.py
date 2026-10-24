from dataclasses import dataclass
from enum import Enum

import pandas as pd


class CloseBehaviorState(str, Enum):
    POZITIF_KAPANIS = "POZITIF_KAPANIS"
    ZAYIF_KAPANIS = "ZAYIF_KAPANIS"
    NEGATIF_KAPANIS = "NEGATIF_KAPANIS"
    YETERSIZ_VERI = "YETERSIZ_VERI"


@dataclass(frozen=True)
class CloseBehaviorEvidence:
    close_state: CloseBehaviorState
    close_change_pct: float | None
    day_position_pct: float | None
    data_sufficient: bool
    error: str | None = None


def build_close_behavior_evidence(frame: pd.DataFrame) -> CloseBehaviorEvidence:
    if frame is None or len(frame) < 3:
        return CloseBehaviorEvidence(
            close_state=CloseBehaviorState.YETERSIZ_VERI,
            close_change_pct=None,
            day_position_pct=None,
            data_sufficient=False,
            error="Kapanış davranışı için yeterli veri yok.",
        )

    if not {"High", "Low", "Close"}.issubset(frame.columns):
        return CloseBehaviorEvidence(
            close_state=CloseBehaviorState.YETERSIZ_VERI,
            close_change_pct=None,
            day_position_pct=None,
            data_sufficient=False,
            error="High/Low/Close kolonları eksik.",
        )

    close = pd.to_numeric(frame["Close"], errors="coerce")
    high = pd.to_numeric(frame["High"], errors="coerce")
    low = pd.to_numeric(frame["Low"], errors="coerce")

    valid = pd.concat(
        [close.rename("Close"), high.rename("High"), low.rename("Low")],
        axis=1,
    ).dropna()

    if len(valid) < 3:
        return CloseBehaviorEvidence(
            close_state=CloseBehaviorState.YETERSIZ_VERI,
            close_change_pct=None,
            day_position_pct=None,
            data_sufficient=False,
            error="Geçerli OHLC verisi yetersiz.",
        )

    first_close = float(valid["Close"].iloc[0])
    last_close = float(valid["Close"].iloc[-1])
    day_high = float(valid["High"].max())
    day_low = float(valid["Low"].min())

    if first_close == 0:
        return CloseBehaviorEvidence(
            close_state=CloseBehaviorState.YETERSIZ_VERI,
            close_change_pct=None,
            day_position_pct=None,
            data_sufficient=False,
            error="Başlangıç kapanışı sıfır.",
        )

    close_change_pct = (last_close / first_close - 1.0) * 100.0

    day_range = day_high - day_low
    if day_range > 0:
        day_position_pct = (
            (last_close - day_low) / day_range
        ) * 100.0
    else:
        day_position_pct = 50.0

    if close_change_pct > 0.20:
        state = CloseBehaviorState.POZITIF_KAPANIS
    elif close_change_pct < -0.20:
        state = CloseBehaviorState.NEGATIF_KAPANIS
    else:
        state = CloseBehaviorState.ZAYIF_KAPANIS

    return CloseBehaviorEvidence(
        close_state=state,
        close_change_pct=close_change_pct,
        day_position_pct=day_position_pct,
        data_sufficient=True,
    )

