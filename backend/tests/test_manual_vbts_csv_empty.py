from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest


def test_bos_resmi_vbts_csv_guvenli_bicimde_reddedilir(
    tmp_path: Path,
) -> None:
    from backend.app.compliance.manual_vbts_csv import (
        ManualVbtsCsvError,
        load_official_vbts_csv,
    )

    csv_path = tmp_path / "vbts.csv"
    csv_path.write_text(
        "symbol,measure_type,start_date,end_date,source_reference\n",
        encoding="utf-8",
    )

    now = datetime.now(timezone.utc)

    with pytest.raises(
        ManualVbtsCsvError,
        match="kayıt içermiyor",
    ):
        load_official_vbts_csv(
            csv_path,
            fetched_at=now,
            now_provider=lambda: now,
        )
