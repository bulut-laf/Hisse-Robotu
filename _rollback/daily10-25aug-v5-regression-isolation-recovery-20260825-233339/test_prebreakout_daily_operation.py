from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace

import backend.app.prebreakout.prebreakout_daily_operation as module


def _state_path(tmp_path: Path) -> Path:
    return tmp_path / "operation-state.json"


def test_durum_dosyasi_atomik_olarak_yazilir_ve_yuklenir(tmp_path: Path) -> None:
    path = _state_path(tmp_path)
    state = module.DailyOperationState(
        run_date="2026-08-01",
        status=module.DailyOperationStatus.FAILED,
        attempt_count=2,
        completed_steps=("GUNLUK_IZLEME",),
        failed_step="SISTEM_SAGLIGI",
        error_message="ornek",
    )
    module.gunluk_operasyon_durumunu_kaydet(state, path)
    assert module.gunluk_operasyon_durumunu_yukle(path) == state
    assert not path.with_suffix(path.suffix + ".tmp").exists()


def test_bozuk_durum_dosyasi_guvenli_bicimde_yok_sayilir(tmp_path: Path) -> None:
    path = _state_path(tmp_path)
    path.write_text("{bozuk", encoding="utf-8")
    assert module.gunluk_operasyon_durumunu_yukle(path) is None


def test_gunluk_izleme_hatasi_tamamlandi_sayilmaz(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "gunluk_izleme_akisini_calistir", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("veri hatasi")))
    result = module.gunluk_operasyonu_guvenli_calistir([], date(2026, 8, 1), object(), {}, state_path=_state_path(tmp_path))
    assert result.state.status is module.DailyOperationStatus.FAILED
    assert result.state.failed_step == "GUNLUK_IZLEME"
    assert result.state.attempt_count == 1


def test_saglik_kilidi_hazir_degilse_blocked_olur(tmp_path: Path, monkeypatch) -> None:
    monitor = SimpleNamespace(run_date="2026-08-01")
    monkeypatch.setattr(module, "gunluk_izleme_akisini_calistir", lambda *a, **k: monitor)
    monkeypatch.setattr(module, "operasyon_sagligini_degerlendir", lambda *a, **k: SimpleNamespace(ready=False, error_count=2))
    result = module.gunluk_operasyonu_guvenli_calistir([], date(2026, 8, 1), object(), {}, state_path=_state_path(tmp_path))
    assert result.state.status is module.DailyOperationStatus.BLOCKED
    assert result.state.completed_steps == ("GUNLUK_IZLEME", "SISTEM_SAGLIGI")
    assert "2 hata" in (result.state.error_message or "")


def test_tum_adimlar_saglikliysa_completed_olur(tmp_path: Path, monkeypatch) -> None:
    monitor = SimpleNamespace(run_date="2026-08-01")
    health = SimpleNamespace(ready=True, error_count=0)
    monkeypatch.setattr(module, "gunluk_izleme_akisini_calistir", lambda *a, **k: monitor)
    monkeypatch.setattr(module, "operasyon_sagligini_degerlendir", lambda *a, **k: health)
    result = module.gunluk_operasyonu_guvenli_calistir([], date(2026, 8, 1), object(), {}, state_path=_state_path(tmp_path))
    assert result.state.status is module.DailyOperationStatus.COMPLETED
    assert result.state.completed_steps[-1] == "TAMAMLANDI"


def test_basarisiz_kosu_yeniden_denenince_deneme_sayisi_artar(tmp_path: Path, monkeypatch) -> None:
    path = _state_path(tmp_path)
    calls = {"count": 0}
    monitor = SimpleNamespace(run_date="2026-08-01")
    def run(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("gecici hata")
        return monitor
    monkeypatch.setattr(module, "gunluk_izleme_akisini_calistir", run)
    monkeypatch.setattr(module, "operasyon_sagligini_degerlendir", lambda *a, **k: SimpleNamespace(ready=True, error_count=0))
    first = module.gunluk_operasyonu_guvenli_calistir([], date(2026, 8, 1), object(), {}, state_path=path)
    second = module.gunluk_operasyonu_guvenli_calistir([], date(2026, 8, 1), object(), {}, state_path=path)
    assert first.state.status is module.DailyOperationStatus.FAILED
    assert second.state.status is module.DailyOperationStatus.COMPLETED
    assert second.state.attempt_count == 2


def test_ayni_gun_tamamlanmis_operasyon_force_yoksa_tekrar_calistirilmaz(tmp_path: Path, monkeypatch) -> None:
    path = _state_path(tmp_path)
    module.gunluk_operasyon_durumunu_kaydet(
        module.DailyOperationState("2026-08-01", module.DailyOperationStatus.COMPLETED, 1, ("TAMAMLANDI",)), path
    )
    monkeypatch.setattr(module, "gunluk_izleme_akisini_calistir", lambda *a, **k: (_ for _ in ()).throw(AssertionError("calismamali")))
    result = module.gunluk_operasyonu_guvenli_calistir([], date(2026, 8, 1), object(), {}, state_path=path)
    assert result.state.status is module.DailyOperationStatus.SKIPPED
    assert result.state.attempt_count == 1
