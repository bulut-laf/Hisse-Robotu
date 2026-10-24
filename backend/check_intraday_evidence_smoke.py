from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.analysis.intraday_movement_evidence import (
    build_intraday_movement_evidence,
)
from backend.app.data.delayed_data_pilot import (
    DelayedDataPilotConfig,
)
from backend.app.operations.scheduled_intraday_batch import (
    _extract_symbol_frame,
)
import yfinance as yf


ISTANBUL = ZoneInfo("Europe/Istanbul")

SYMBOLS = (
    "THYAO.IS",
    "AKBNK.IS",
    "YKBNK.IS",
    "ASELS.IS",
    "BIMAS.IS",
    "TUPRS.IS",
    "EREGL.IS",
    "SISE.IS",
    "KCHOL.IS",
    "GARAN.IS",
)


def main() -> None:
    config = DelayedDataPilotConfig()

    now = datetime.now(ISTANBUL)

    print()
    print("INTRADAY MOVEMENT EVIDENCE — LIVE SMOKE")
    print("=" * 72)
    print(f"Olcum zamani : {now:%Y-%m-%d %H:%M:%S}")
    print(f"Interval     : {config.interval}")
    print(f"Period       : {config.period}")
    print()

    raw = yf.download(
        tickers=list(SYMBOLS),
        period=config.period,
        interval=config.interval,
        auto_adjust=True,
        progress=False,
        threads=True,
        prepost=False,
        timeout=45,
        group_by="ticker",
    )

    print(
        f"{'SYMBOL':<10}"
        f"{'BAR':>5}"
        f"{'PRICE':>10}"
        f"{'5m %':>9}"
        f"{'15m %':>9}"
        f"{'30m %':>9}"
        f"{'VOL':>9}"
        f"{'MOVE':>12}"
        f"{'VOLUME':>14}"
    )
    print("-" * 96)

    successful = 0

    for symbol in SYMBOLS:
        try:
            frame = _extract_symbol_frame(
                raw,
                symbol,
                chunk_size=len(SYMBOLS),
            )

            evidence = build_intraday_movement_evidence(
                symbol,
                frame,
            )

            successful += 1

            def fmt(value: float | None) -> str:
                if value is None:
                    return "-"

                return f"{value:+.2f}"

            price = (
                f"{evidence.last_price:.2f}"
                if evidence.last_price is not None
                else "-"
            )

            volume_ratio = (
                f"{evidence.volume_ratio_5m:.2f}x"
                if evidence.volume_ratio_5m is not None
                else "-"
            )

            print(
                f"{symbol:<10}"
                f"{evidence.bar_count:>5}"
                f"{price:>10}"
                f"{fmt(evidence.price_change_5m_pct):>9}"
                f"{fmt(evidence.price_change_15m_pct):>9}"
                f"{fmt(evidence.price_change_30m_pct):>9}"
                f"{volume_ratio:>9}"
                f"{evidence.movement_state:>12}"
                f"{evidence.volume_state:>14}"
            )

        except Exception as error:
            print(
                f"{symbol:<10}"
                f"{'ERROR':>5}  {error}"
            )

    print()
    print("-" * 72)
    print(f"BIST test evreni : {len(SYMBOLS)}")
    print(f"Evidence üretildi: {successful}")
    print("=" * 72)


if __name__ == "__main__":
    main()
