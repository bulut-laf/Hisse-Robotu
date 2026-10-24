from pathlib import Path
import json

from backend.app.prebreakout.prebreakout_operation_closure import DailyOperationClosureSummary
from backend.app.prebreakout.prebreakout_operation_finalization import (
    OperationPhaseStatus,
    OperationSystemCheck,
    operasyon_fazini_sonlandir,
    operasyon_final_raporunu_kaydet,
    operasyon_final_raporunu_tabloya_cevir,
)


def _closure(*, ready=True, critical=0):
    return DailyOperationClosureSummary(
        run_date="2026-08-01",
        decision="ÇALIŞTIR",
        confidence_score=92,
        priority="NORMAL",
        open_risk_count=critical,
        critical_open_risk_count=critical,
        open_risks=(),
        pending_actions=(),
        retry_allowed=True,
        decision_recorded=True,
        closure_ready=ready,
        headline="test",
        final_message="test",
    )


def _fake_required_modules(root: Path):
    paths = (
        "backend/app/prebreakout/prebreakout_daily_operation.py",
        "backend/app/prebreakout/prebreakout_alarm_journal.py",
        "backend/app/prebreakout/prebreakout_operation_diagnosis.py",
        "backend/app/prebreakout/prebreakout_operation_recovery.py",
        "backend/app/prebreakout/prebreakout_operation_confidence.py",
        "backend/app/prebreakout/prebreakout_operation_action_summary.py",
        "backend/app/prebreakout/prebreakout_operation_closure.py",
    )
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# test\n", encoding="utf-8")


def test_tum_kontroller_gecerse_operasyon_fazi_hazir(tmp_path: Path):
    _fake_required_modules(tmp_path)
    result = operasyon_fazini_sonlandir(_closure(), project_root=tmp_path)
    assert result.status is OperationPhaseStatus.READY
    assert result.failed_check_count == 0
    assert result.closure_ready


def test_kapanis_hazir_degilse_faz_bloke(tmp_path: Path):
    _fake_required_modules(tmp_path)
    result = operasyon_fazini_sonlandir(_closure(ready=False), project_root=tmp_path)
    assert result.status is OperationPhaseStatus.BLOCKED
    assert result.failed_check_count >= 1


def test_kritik_risk_final_kontrolu_bloke_eder(tmp_path: Path):
    _fake_required_modules(tmp_path)
    result = operasyon_fazini_sonlandir(_closure(ready=False, critical=1), project_root=tmp_path)
    assert result.status is OperationPhaseStatus.BLOCKED
    assert any(item.code == "CRITICAL_RISK" and not item.passed for item in result.checks)


def test_zorunlu_modul_eksigi_final_kontrolu_bloke_eder(tmp_path: Path):
    result = operasyon_fazini_sonlandir(_closure(), project_root=tmp_path)
    assert result.status is OperationPhaseStatus.BLOCKED
    assert any(item.code.startswith("MOD_") and not item.passed for item in result.checks)


def test_ek_sistem_kontrolu_final_karara_katilir(tmp_path: Path):
    _fake_required_modules(tmp_path)
    extra = OperationSystemCheck("EXTRA", "Ek kontrol", False, "Başarısız")
    result = operasyon_fazini_sonlandir(_closure(), project_root=tmp_path, extra_checks=(extra,))
    assert result.status is OperationPhaseStatus.BLOCKED
    assert any(item.code == "EXTRA" for item in result.checks)


def test_final_rapor_atomik_json_kaydedilir(tmp_path: Path):
    _fake_required_modules(tmp_path)
    report = operasyon_fazini_sonlandir(_closure(), project_root=tmp_path)
    target = tmp_path / "final.json"
    operasyon_final_raporunu_kaydet(report, target)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["status"] == "HAZIR"
    assert payload["failed_check_count"] == 0
    assert not target.with_suffix(".json.tmp").exists()


def test_final_rapor_tabloya_cevrilir(tmp_path: Path):
    _fake_required_modules(tmp_path)
    report = operasyon_fazini_sonlandir(_closure(), project_root=tmp_path)
    rows = operasyon_final_raporunu_tabloya_cevir(report)
    fields = {row["Alan"] for row in rows}
    assert {"Final durum", "Başarılı kontrol", "Başarısız kontrol", "Kapanış"} <= fields
