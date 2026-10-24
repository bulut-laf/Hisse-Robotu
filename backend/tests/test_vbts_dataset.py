from datetime import date, datetime, timedelta, timezone

import pytest

from backend.app.compliance.vbts_models import VbtsMeasure
from backend.app.compliance.vbts_source_status import VbtsSourceStatus


def _measure(symbol: str) -> VbtsMeasure:
    return VbtsMeasure(
        symbol=symbol,
        measure_type="BRUT_TAKAS",
        start_date=date(2026, 7, 20),
        end_date=date(2026, 8, 19),
        source="KAP",
        source_reference=f"bildirim-{symbol}",
    )


def test_guncel_ve_tutarli_paket_kullanilabilir():
    from backend.app.compliance.vbts_dataset import VbtsDataset

    fetched_at = datetime(2026, 7, 28, 18, 0, tzinfo=timezone.utc)

    dataset = VbtsDataset(
        measures=[_measure("EREGL"), _measure("CCOLA")],
        status=VbtsSourceStatus(
            source="KAP",
            fetched_at=fetched_at,
            is_verified=True,
            record_count=2,
        ),
    )

    assert dataset.is_usable_at(
        control_time=fetched_at + timedelta(hours=1),
        maximum_age=timedelta(hours=6),
    ) is True

    assert len(dataset.measures) == 2


def test_kayit_sayisi_uyusmazligi_reddedilir():
    from backend.app.compliance.vbts_dataset import VbtsDataset

    with pytest.raises(ValueError):
        VbtsDataset(
            measures=[_measure("EREGL")],
            status=VbtsSourceStatus(
                source="KAP",
                fetched_at=datetime.now(timezone.utc),
                is_verified=True,
                record_count=2,
            ),
        )


def test_farkli_kaynakli_tedbir_reddedilir():
    from backend.app.compliance.vbts_dataset import VbtsDataset

    measure = VbtsMeasure(
        symbol="OYAKC",
        measure_type="TEK_FIYAT",
        start_date=date(2026, 7, 20),
        end_date=date(2026, 8, 19),
        source="BASKA_KAYNAK",
        source_reference="bildirim-oyakc",
    )

    with pytest.raises(ValueError):
        VbtsDataset(
            measures=[measure],
            status=VbtsSourceStatus(
                source="KAP",
                fetched_at=datetime.now(timezone.utc),
                is_verified=True,
                record_count=1,
            ),
        )


def test_eski_paket_kullanilamaz():
    from backend.app.compliance.vbts_dataset import VbtsDataset

    fetched_at = datetime(2026, 7, 27, 8, 0, tzinfo=timezone.utc)

    dataset = VbtsDataset(
        measures=[_measure("EREGL")],
        status=VbtsSourceStatus(
            source="KAP",
            fetched_at=fetched_at,
            is_verified=True,
            record_count=1,
        ),
    )

    assert dataset.is_usable_at(
        control_time=datetime(2026, 7, 28, 18, 0, tzinfo=timezone.utc),
        maximum_age=timedelta(hours=6),
    ) is False