from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

from backend.app.prebreakout.prebreakout_operational_health import (
    HealthLevel,
    operasyon_saglik_raporunu_kaydet,
    operasyon_sagligini_degerlendir,
    operasyon_sagligini_tabloya_cevir,
)


@dataclass(frozen=True)
class _Perf:
    available_session_count: int


@dataclass(frozen=True)
class _Portfolio:
    total_trade_count: int


@dataclass(frozen=True)
class _Daily:
    run_date: str = "2026-08-01"
    total_signal_count: int = 1
    lifecycle_records: tuple = (object(),)
    performance_records: tuple = (_Perf(5),)
    paper_trades: tuple = (object(),)
    portfolio_summary: _Portfolio = _Portfolio(1)
    missing_observation_symbols: tuple[str, ...] = ()


def test_saglikli_gunluk_akis_hazirdir(tmp_path: Path) -> None:
    daily_path = tmp_path / "daily.json"
    daily_path.write_text(json.dumps({"run_date": "2026-08-01"}), encoding="utf-8")
    report = operasyon_sagligini_degerlendir(
        _Daily(), expected_run_date=date(2026, 8, 1), daily_report_path=daily_path
    )
    assert report.ready is True
    assert report.overall_level is HealthLevel.OK
    assert report.error_count == 0


def test_eksik_fiyat_verisi_hata_uretir() -> None:
    daily = _Daily(missing_observation_symbols=("THYAO.IS",))
    report = operasyon_sagligini_degerlendir(daily, expected_run_date=date(2026, 8, 1))
    assert report.ready is False
    assert any(item.code == "market_data" and item.level is HealthLevel.HATA for item in report.checks)


def test_sayim_tutarsizligi_hata_uretir() -> None:
    daily = _Daily(lifecycle_records=())
    report = operasyon_sagligini_degerlendir(daily, expected_run_date=date(2026, 8, 1))
    assert report.ready is False
    assert any(item.code == "lifecycle" and item.level is HealthLevel.HATA for item in report.checks)


def test_henuz_olculemeyen_performans_uyaridir() -> None:
    daily = _Daily(performance_records=(_Perf(0),))
    report = operasyon_sagligini_degerlendir(daily, expected_run_date=date(2026, 8, 1))
    assert report.ready is True
    assert report.overall_level is HealthLevel.UYARI
    assert report.warning_count == 1


def test_gunluk_rapor_tarihi_uyusmazsa_hatadir(tmp_path: Path) -> None:
    daily_path = tmp_path / "daily.json"
    daily_path.write_text(json.dumps({"run_date": "2026-07-31"}), encoding="utf-8")
    report = operasyon_sagligini_degerlendir(
        _Daily(), expected_run_date=date(2026, 8, 1), daily_report_path=daily_path
    )
    assert report.ready is False
    assert any(item.code == "daily_report" and item.level is HealthLevel.HATA for item in report.checks)


def test_bozuk_json_hata_uretir(tmp_path: Path) -> None:
    daily_path = tmp_path / "daily.json"
    daily_path.write_text("{bozuk", encoding="utf-8")
    report = operasyon_sagligini_degerlendir(_Daily(), daily_report_path=daily_path)
    assert any(item.code == "daily_report" and item.level is HealthLevel.HATA for item in report.checks)


def test_saglik_raporu_json_kaydedilir(tmp_path: Path) -> None:
    report = operasyon_sagligini_degerlendir(_Daily(), expected_run_date=date(2026, 8, 1))
    path = tmp_path / "health.json"
    operasyon_saglik_raporunu_kaydet(report, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["ready"] is True
    assert payload["overall_level"] == "OK"


def test_saglik_raporu_tabloya_cevrilir() -> None:
    report = operasyon_sagligini_degerlendir(_Daily(), expected_run_date=date(2026, 8, 1))
    rows = operasyon_sagligini_tabloya_cevir(report)
    assert rows
    assert {"Kontrol", "Durum", "Açıklama"} == set(rows[0])
