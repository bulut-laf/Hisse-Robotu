from datetime import datetime, timedelta, timezone

import pytest


def test_guncel_ve_dogrulanmis_kaynak_kullanilabilir():
    from backend.app.compliance.vbts_source_status import VbtsSourceStatus

    fetched_at = datetime(2026, 7, 28, 18, 0, tzinfo=timezone.utc)

    status = VbtsSourceStatus(
        source="KAP",
        fetched_at=fetched_at,
        is_verified=True,
        record_count=12,
    )

    assert status.is_usable_at(
        control_time=fetched_at + timedelta(hours=2),
        maximum_age=timedelta(hours=6),
    ) is True


def test_eski_kaynak_kullanilamaz():
    from backend.app.compliance.vbts_source_status import VbtsSourceStatus

    fetched_at = datetime(2026, 7, 27, 8, 0, tzinfo=timezone.utc)

    status = VbtsSourceStatus(
        source="KAP",
        fetched_at=fetched_at,
        is_verified=True,
        record_count=12,
    )

    assert status.is_usable_at(
        control_time=datetime(2026, 7, 28, 18, 0, tzinfo=timezone.utc),
        maximum_age=timedelta(hours=6),
    ) is False


def test_dogrulanmamis_kaynak_kullanilamaz():
    from backend.app.compliance.vbts_source_status import VbtsSourceStatus

    fetched_at = datetime(2026, 7, 28, 18, 0, tzinfo=timezone.utc)

    status = VbtsSourceStatus(
        source="KAP",
        fetched_at=fetched_at,
        is_verified=False,
        record_count=12,
    )

    assert status.is_usable_at(
        control_time=fetched_at + timedelta(minutes=10),
        maximum_age=timedelta(hours=6),
    ) is False


def test_bos_kaynak_adi_reddedilir():
    from backend.app.compliance.vbts_source_status import VbtsSourceStatus

    with pytest.raises(ValueError):
        VbtsSourceStatus(
            source=" ",
            fetched_at=datetime.now(timezone.utc),
            is_verified=True,
            record_count=1,
        )


def test_negatif_kayit_sayisi_reddedilir():
    from backend.app.compliance.vbts_source_status import VbtsSourceStatus

    with pytest.raises(ValueError):
        VbtsSourceStatus(
            source="KAP",
            fetched_at=datetime.now(timezone.utc),
            is_verified=True,
            record_count=-1,
        )


def test_saat_dilimi_olmayan_zaman_reddedilir():
    from backend.app.compliance.vbts_source_status import VbtsSourceStatus

    with pytest.raises(ValueError):
        VbtsSourceStatus(
            source="KAP",
            fetched_at=datetime(2026, 7, 28, 18, 0),
            is_verified=True,
            record_count=1,
        )