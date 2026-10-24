from __future__ import annotations

from dataclasses import dataclass, field
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = Path("backend/app/prebreakout/prebreakout_operation_archive.py")


def _load_module():
    spec = spec_from_file_location("prebreakout_operation_archive", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_arsiv_ayni_gunu_cogaltmaz(tmp_path: Path) -> None:
    module = _load_module()
    path = tmp_path / "archive.jsonl"
    first = module.DailyOperationArchiveRecord(
        "2026-08-01", "COMPLETED", 1, 2, 5, 5, 5, 5, 1.2, True, 0, 0, 0
    )
    second = module.DailyOperationArchiveRecord(
        "2026-08-01", "COMPLETED", 2, 3, 6, 6, 6, 6, 1.5, True, 1, 0, 0
    )
    module.gunluk_operasyon_arsivini_kaydet(first, path)
    module.gunluk_operasyon_arsivini_kaydet(second, path)
    records = module.gunluk_operasyon_arsivini_yukle(path)
    assert len(records) == 1
    assert records[0].attempt_count == 2
    assert records[0].new_signal_count == 3


def test_gecmis_gun_karsilastirmasi_hesaplanir() -> None:
    module = _load_module()
    previous = module.DailyOperationArchiveRecord(
        "2026-07-31", "COMPLETED", 1, 1, 4, 4, 4, 4, 0.5, True, 1, 0, 1
    )
    current = module.DailyOperationArchiveRecord(
        "2026-08-01", "COMPLETED", 1, 3, 6, 6, 6, 6, 1.25, True, 0, 0, 0
    )
    comparison = module.gunluk_operasyon_karsilastirmasi(current, previous)
    assert comparison.new_signal_delta == 2
    assert comparison.total_signal_delta == 2
    assert comparison.portfolio_return_delta_pct == 0.75
    assert comparison.warning_delta == -1
    assert comparison.health_changed is False


def test_yonetici_ozeti_kisa_ve_sayisal() -> None:
    module = _load_module()
    previous = module.DailyOperationArchiveRecord(
        "2026-07-31", "COMPLETED", 1, 1, 4, 4, 4, 4, 0.5, True, 0, 0, 0
    )
    current = module.DailyOperationArchiveRecord(
        "2026-08-01", "COMPLETED", 1, 2, 5, 5, 5, 5, 1.0, True, 1, 0, 0
    )
    text = module.yonetici_ozeti_olustur(current, previous)
    assert "2026-08-01" in text
    assert "2 yeni aday" in text
    assert "portföy %1.00" in text
    assert "Önceki güne göre" in text


def test_run_result_arsiv_kaydina_donusturulur() -> None:
    module = _load_module()

    @dataclass
    class Status:
        value: str = "COMPLETED"

    @dataclass
    class State:
        run_date: str = "2026-08-01"
        status: object = field(default_factory=Status)
        attempt_count: int = 1

    @dataclass
    class Portfolio:
        portfolio_return_pct: float = 2.3456789

    @dataclass
    class Monitor:
        new_signal_count: int = 2
        total_signal_count: int = 8
        lifecycle_records: tuple = (1, 2)
        performance_records: tuple = (1, 2)
        paper_trades: tuple = (1, 2)
        portfolio_summary: object = field(default_factory=Portfolio)
        missing_observation_symbols: tuple = ("ABC.IS",)

    @dataclass
    class Health:
        ready: bool = True
        warning_count: int = 1
        error_count: int = 0

    @dataclass
    class RunResult:
        state: object = field(default_factory=State)
        monitor_result: object = field(default_factory=Monitor)
        health_report: object = field(default_factory=Health)

    record = module.gunluk_operasyon_arsiv_kaydi_olustur(RunResult())
    assert record.new_signal_count == 2
    assert record.total_signal_count == 8
    assert record.portfolio_return_pct == 2.345679
    assert record.health_ready is True
    assert record.missing_observation_count == 1
