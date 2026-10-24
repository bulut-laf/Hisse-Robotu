from datetime import date, datetime, timedelta, timezone

import pytest

from backend.app.compliance.vbts_dataset import VbtsDataset
from backend.app.compliance.vbts_models import VbtsMeasure
from backend.app.compliance.vbts_source_status import VbtsSourceStatus


def _dataset(
    fetched_at: datetime,
    is_verified: bool = True,
) -> VbtsDataset:
    measures = [
        VbtsMeasure(
            symbol="EREGL",
            measure_type="BRUT_TAKAS",
            start_date=date(2026, 7, 20),
            end_date=date(2026, 8, 19),
            source="KAP",
            source_reference="bildirim-1",
        )
    ]

    return VbtsDataset(
        measures=measures,
        status=VbtsSourceStatus(
            source="KAP",
            fetched_at=fetched_at,
            is_verified=is_verified,
            record_count=len(measures),
        ),
    )


def test_aktif_tedbirli_sembol_tarama_evreninden_cikarilir():
    from backend.app.compliance.vbts_scan_filter import VbtsScanFilter

    fetched_at = datetime(2026, 7, 28, 18, 0, tzinfo=timezone.utc)

    scan_filter = VbtsScanFilter(
        dataset=_dataset(fetched_at),
        maximum_age=timedelta(hours=6),
    )

    result = scan_filter.apply(
        symbols=["THYAO", "EREGL.IS", "CCOLA"],
        control_date=date(2026, 7, 28),
        control_time=fetched_at + timedelta(hours=1),
    )

    assert result.allowed_symbols == ("THYAO.IS", "CCOLA.IS")
    assert result.blocked_symbols == ("EREGL.IS",)
    assert result.block_reasons["EREGL.IS"] == ("BRUT_TAKAS",)


def test_tedbir_suresi_disindaki_sembol_engellenmez():
    from backend.app.compliance.vbts_scan_filter import VbtsScanFilter

    fetched_at = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)

    scan_filter = VbtsScanFilter(
        dataset=_dataset(fetched_at),
        maximum_age=timedelta(hours=6),
    )

    result = scan_filter.apply(
        symbols=["EREGL"],
        control_date=date(2026, 8, 20),
        control_time=fetched_at + timedelta(minutes=30),
    )

    assert result.allowed_symbols == ("EREGL.IS",)
    assert result.blocked_symbols == ()
    assert result.block_reasons == {}


def test_eski_veri_paketinde_tarama_guvenli_sekilde_durdurulur():
    from backend.app.compliance.vbts_scan_filter import (
        VbtsDatasetNotUsableError,
        VbtsScanFilter,
    )

    fetched_at = datetime(2026, 7, 27, 8, 0, tzinfo=timezone.utc)

    scan_filter = VbtsScanFilter(
        dataset=_dataset(fetched_at),
        maximum_age=timedelta(hours=6),
    )

    with pytest.raises(VbtsDatasetNotUsableError):
        scan_filter.apply(
            symbols=["THYAO", "EREGL"],
            control_date=date(2026, 7, 28),
            control_time=datetime(
                2026,
                7,
                28,
                18,
                0,
                tzinfo=timezone.utc,
            ),
        )


def test_dogrulanmamis_veri_paketinde_tarama_durdurulur():
    from backend.app.compliance.vbts_scan_filter import (
        VbtsDatasetNotUsableError,
        VbtsScanFilter,
    )

    fetched_at = datetime(2026, 7, 28, 18, 0, tzinfo=timezone.utc)

    scan_filter = VbtsScanFilter(
        dataset=_dataset(
            fetched_at=fetched_at,
            is_verified=False,
        ),
        maximum_age=timedelta(hours=6),
    )

    with pytest.raises(VbtsDatasetNotUsableError):
        scan_filter.apply(
            symbols=["THYAO"],
            control_date=date(2026, 7, 28),
            control_time=fetched_at + timedelta(minutes=10),
        )