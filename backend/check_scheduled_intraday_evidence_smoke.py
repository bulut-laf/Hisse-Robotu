from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.operations.scheduled_intraday_batch import (
    fetch_scheduled_intraday_batch,
)

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
    now = datetime.now(ISTANBUL)

    result = fetch_scheduled_intraday_batch(
        SYMBOLS,
        now=now,
    )

    print()
    print("SCHEDULED INTRADAY BATCH — EVIDENCE SMOKE")
    print("=" * 96)
    print(f"Olcum zamani : {now:%Y-%m-%d %H:%M:%S}")
    print()

    print(
        f"{'SYMBOL':<10}"
        f"{'PRICE':>10}"
        f"{'5m %':>9}"
        f"{'15m %':>9}"
        f"{'30m %':>9}"
        f"{'VOL':>9}"
        f"{'MOVE':>12}"
        f"{'VOLUME':>14}"
        f"{'DATA':>10}"
    )

    print("-" * 96)

    for symbol in SYMBOLS:
        evidence = result.evidence.get(symbol)

        if evidence is None:
            failure = next(
                (
                    item
                    for item in result.failures
                    if item.symbol == symbol
                ),
                None,
            )

            print(
                f"{symbol:<10}"
                f"{'ERROR':>10}"
                f" {failure.error if failure else 'Evidence yok'}"
            )
            continue

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

        data_state = (
            "YETERLI"
            if evidence.data_sufficient
            else "YETERSIZ"
        )

        print(
            f"{symbol:<10}"
            f"{price:>10}"
            f"{fmt(evidence.price_change_5m_pct):>9}"
            f"{fmt(evidence.price_change_15m_pct):>9}"
            f"{fmt(evidence.price_change_30m_pct):>9}"
            f"{volume_ratio:>9}"
            f"{evidence.movement_state:>12}"
            f"{evidence.volume_state:>14}"
            f"{data_state:>10}"
        )

    print()
    print("-" * 96)
    print(f"Talep edilen sembol : {result.requested_count}")
    print(f"Snapshot başarılı    : {result.successful_count}")
    print(f"Evidence başarılı    : {result.evidence_count}")
    print(f"Hata                 : {len(result.failures)}")
    print("=" * 96)


if __name__ == "__main__":
    main()
