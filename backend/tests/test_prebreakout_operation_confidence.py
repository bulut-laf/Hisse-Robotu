from dataclasses import dataclass
from pathlib import Path
import json

from backend.app.prebreakout.prebreakout_operation_confidence import (
    DailyOperationDecision,
    operasyon_guvenini_degerlendir,
    operasyon_guven_raporunu_kaydet,
)
from backend.app.prebreakout.prebreakout_operation_diagnosis import (
    OperationDiagnosisReport,
    RootCauseCategory,
)
from backend.app.prebreakout.prebreakout_operation_recovery import (
    OperationRecoveryGuide,
)


@dataclass
class Status:
    value: str


@dataclass
class State:
    run_date: str
    status: Status


@dataclass
class Health:
    ready: bool
    error_count: int = 0
    warning_count: int = 0


@dataclass
class RunResult:
    state: State
    health_report: Health | None


def _diagnosis(category=RootCauseCategory.NONE, *, status="COMPLETED", retry=False):
    return OperationDiagnosisReport("2026-08-01", status, category, (), "test", retry)


def _recovery(category=RootCauseCategory.NONE, *, retry=False):
    return OperationRecoveryGuide("2026-08-01", "COMPLETED", category, (), retry, "test")


def test_saglikli_tamamlanan_operasyon_calistir_karari_verir():
    run = RunResult(State("2026-08-01", Status("COMPLETED")), Health(True))
    report = operasyon_guvenini_degerlendir(run, _diagnosis(), _recovery())
    assert report.score == 100
    assert report.decision is DailyOperationDecision.RUN
    assert "ÇALIŞTIR" in report.summary


def test_tek_uyari_operasyonu_gereksiz_bloklamaz():
    run = RunResult(State("2026-08-01", Status("COMPLETED")), Health(True, warning_count=1))
    report = operasyon_guvenini_degerlendir(run, _diagnosis(), _recovery())
    assert report.score == 95
    assert report.decision is DailyOperationDecision.RUN


def test_veri_kok_nedeni_bekle_karari_verir():
    run = RunResult(State("2026-08-01", Status("BLOCKED")), Health(False, error_count=1))
    diagnosis = _diagnosis(RootCauseCategory.DATA, status="BLOCKED")
    recovery = _recovery(RootCauseCategory.DATA)
    report = operasyon_guvenini_degerlendir(run, diagnosis, recovery)
    assert report.decision is DailyOperationDecision.WAIT
    assert "BEKLE" in report.summary


def test_kayit_butunlugu_bekle_karari_verir():
    run = RunResult(State("2026-08-01", Status("FAILED")), Health(True))
    diagnosis = _diagnosis(RootCauseCategory.RECORD_INTEGRITY, status="FAILED")
    report = operasyon_guvenini_degerlendir(run, diagnosis, _recovery(RootCauseCategory.RECORD_INTEGRITY))
    assert report.decision is DailyOperationDecision.WAIT


def test_hesaplama_hatasi_incele_karari_verir():
    run = RunResult(State("2026-08-01", Status("FAILED")), Health(True))
    diagnosis = _diagnosis(RootCauseCategory.CALCULATION, status="FAILED", retry=True)
    recovery = _recovery(RootCauseCategory.CALCULATION, retry=True)
    report = operasyon_guvenini_degerlendir(run, diagnosis, recovery)
    assert report.decision is DailyOperationDecision.REVIEW
    assert "İNCELE" in report.summary
    assert "yeniden deneme" in report.summary


def test_guven_raporu_atomik_json_kaydedilir(tmp_path: Path):
    run = RunResult(State("2026-08-01", Status("COMPLETED")), Health(True))
    report = operasyon_guvenini_degerlendir(run, _diagnosis(), _recovery())
    path = tmp_path / "confidence.json"
    operasyon_guven_raporunu_kaydet(report, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["decision"] == "ÇALIŞTIR"
    assert payload["score"] == 100
    assert payload["primary_category"] == "YOK"
    assert not path.with_suffix(".json.tmp").exists()
