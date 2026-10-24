from __future__ import annotations

import json
from pathlib import Path

from backend.app.market_context.daily_market_briefing import (
    build_daily_market_briefing_snapshot,
    coverage_rows,
    extract_source_recommendations,
    load_processed_reports,
    recommendation_rows,
)


def _write_report(
    root: Path,
    *,
    name: str,
    source: str,
    raw_text: str,
    report_type: str = "daily_bulletin",
) -> None:
    target = root / "backend" / "data" / "market_context_processed" / "2026-08-06"
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{name}.json").write_text(
        json.dumps(
            {
                "report_id": name,
                "source": source,
                "report_type": report_type,
                "report_date": "2026-08-06",
                "raw_text": raw_text,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_secilen_gunun_tum_islenmis_raporlarini_yukler(tmp_path: Path) -> None:
    _write_report(tmp_path, name="a", source="Kurum A", raw_text="Genel piyasa görünümü")
    _write_report(tmp_path, name="b", source="Kurum B", raw_text="Makro riskler")

    reports = load_processed_reports(tmp_path, "2026-08-06")

    assert len(reports) == 2
    assert {item.source for item in reports} == {"Kurum A", "Kurum B"}
    assert all(item.raw_text for item in reports)


def test_eksik_gun_klasoru_bos_sonuc_verir(tmp_path: Path) -> None:
    assert load_processed_reports(tmp_path, "2026-08-06") == ()


def test_acik_al_tavsiyesi_kaynak_gorusu_olarak_cikarilir(tmp_path: Path) -> None:
    _write_report(
        tmp_path,
        name="rec",
        source="Kurum A",
        raw_text="THYAO AL · Hedef Fiyat: 400,00 · Potansiyel: 27%",
    )
    reports = load_processed_reports(tmp_path, "2026-08-06")

    items = extract_source_recommendations(reports)

    assert len(items) == 1
    assert items[0].symbol == "THYAO"
    assert items[0].source_view == "AL"
    assert items[0].target_price == 400.0
    assert items[0].potential_percent == 27.0
    assert items[0].source == "Kurum A"


def test_pay_geri_alimi_hisse_tavsiyesine_donusturulmez(tmp_path: Path) -> None:
    _write_report(
        tmp_path,
        name="kap",
        source="KAP Özeti",
        raw_text=(
            "AHGAZ - 90 bin adet pay geri alımı gerçekleştirdi.\n"
            "OTTO - Hakim ortağı borsadan 150 bin adet pay alımı gerçekleştirecek."
        ),
    )
    reports = load_processed_reports(tmp_path, "2026-08-06")

    assert extract_source_recommendations(reports) == ()


def test_snapshot_kapsama_ve_kurum_gorusu_satirlarini_hazirlar(tmp_path: Path) -> None:
    _write_report(
        tmp_path,
        name="one",
        source="Kurum A",
        raw_text="ASELS TUT · Hedef fiyat 450,00 · Potansiyel 15%",
    )
    _write_report(
        tmp_path,
        name="two",
        source="Kurum B",
        raw_text="Endeks görünümü seçici.",
    )

    snapshot = build_daily_market_briefing_snapshot(tmp_path, "2026-08-06")

    assert snapshot.report_count == 2
    assert len(snapshot.source_names) == 2
    assert snapshot.recommendation_count == 1
    assert len(coverage_rows(snapshot)) == 2
    rows = recommendation_rows(snapshot)
    assert rows[0]["Kaynak"] == "Kurum A"
    assert rows[0]["Kaynak görüşü"] == "TUT"


def test_ayni_kurum_farkli_buyuk_kucuk_harfle_tek_kaynak_sayilir(tmp_path: Path) -> None:
    _write_report(tmp_path, name="one", source="ICBC", raw_text="Piyasa görünümü")
    _write_report(tmp_path, name="two", source="icbc", raw_text="Makro görünüm")

    snapshot = build_daily_market_briefing_snapshot(tmp_path, "2026-08-06")

    assert snapshot.report_count == 2
    assert snapshot.source_names == ("ICBC",)
