from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json

from backend.app.prebreakout.prebreakout_operation_diagnosis import (
    RootCauseCategory,
    operasyon_kok_nedenini_teshis_et,
    operasyon_teshisini_kaydet,
)

class Level(str, Enum):
    OK="OK"; UYARI="UYARI"; HATA="HATA"

@dataclass
class Check:
    code: str
    level: Level
    message: str

@dataclass
class Health:
    checks: tuple = ()

@dataclass
class State:
    run_date: str="2026-08-01"
    status: str="COMPLETED"
    failed_step: str|None=None
    error_message: str|None=None

@dataclass
class Result:
    state: object
    health_report: object|None=None


def test_saglikli_operasyonda_kok_neden_yok():
    report=operasyon_kok_nedenini_teshis_et(Result(State()))
    assert report.primary_category is RootCauseCategory.NONE
    assert report.findings == ()
    assert report.retry_recommended is False


def test_eksik_piyasa_verisi_birincil_veri_kok_nedenidir():
    health=Health((Check("market_data",Level.HATA,"Fiyat gözlemi eksik."),))
    report=operasyon_kok_nedenini_teshis_et(Result(State(status="BLOCKED"),health))
    assert report.primary_category is RootCauseCategory.DATA
    assert report.retry_recommended is False


def test_kayit_sayim_uyusmazligi_kayit_butunlugu_olarak_siniflanir():
    health=Health((Check("performance",Level.HATA,"2/3 kayıt; zincir sayımı uyuşmuyor."),))
    report=operasyon_kok_nedenini_teshis_et(Result(State(),health))
    assert report.primary_category is RootCauseCategory.RECORD_INTEGRITY


def test_portfoy_ozeti_tutarsizligi_portfoy_olarak_siniflanir():
    health=Health((Check("portfolio_summary",Level.HATA,"Özet 1, işlem listesi 2 kayıt içeriyor."),))
    report=operasyon_kok_nedenini_teshis_et(Result(State(),health))
    assert report.primary_category is RootCauseCategory.PORTFOLIO


def test_gunluk_izleme_exception_hesaplama_kategorisidir():
    state=State(status="FAILED",failed_step="GUNLUK_IZLEME",error_message="hesaplama patladı")
    report=operasyon_kok_nedenini_teshis_et(Result(state))
    assert report.primary_category is RootCauseCategory.CALCULATION
    assert report.retry_recommended is True


def test_teshis_json_atomik_kaydedilir(tmp_path: Path):
    report=operasyon_kok_nedenini_teshis_et(Result(State()))
    path=tmp_path/'diagnosis.json'
    operasyon_teshisini_kaydet(report,path)
    payload=json.loads(path.read_text(encoding='utf-8'))
    assert payload['primary_category']=='YOK'
    assert not path.with_suffix('.json.tmp').exists()
