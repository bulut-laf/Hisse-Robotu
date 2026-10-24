from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend" / "dashboard.py"


def test_dashboard_piyasa_rejimi_modunu_icerir() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")
    assert '"Piyasa Rejimi"' in kaynak
    assert "def piyasa_rejimi_formu" in kaynak
    assert "Piyasa rejimini analiz et" in kaynak
    assert "Saatlik veri bulunamazsa analiz durmaz" in kaynak


def test_pytest_yedekleri_toplamaz() -> None:
    kaynak = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "testpaths = backend/tests" in kaynak
    assert "backups" in kaynak
    assert "releases" in kaynak



def test_piyasa_rejimi_baglami_guvenli_aktarim_icerir() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")
    servis = (
        ROOT
        / "backend"
        / "app"
        / "ui"
        / "market_regime_dashboard.py"
    ).read_text(encoding="utf-8")

    assert "class MarketRegimeContext" in servis
    assert "def piyasa_rejimi_baglami_olustur" in servis
    assert "PIYASA_REJIMI_BAGLAMI_KEY" in kaynak
    assert "def piyasa_rejimi_baglami_dogrula" in kaynak


def test_eski_ve_kilitli_rejim_otomatik_kapatilir() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")

    assert "Oturumdaki piyasa rejimi önceki güne ait" in kaynak
    assert "Piyasa rejimi verisi güncel olmadığı için filtre kapatıldı" in kaynak
    assert "disabled=rejim_baglami is None" in kaynak
    assert "rejim_baglami is None" in kaynak


def test_momentum_rejim_kaynagi_tarihi_guveni_gosterilir() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")

    assert "Rejim bağlamı:" in kaynak
    assert "Doğrulanmış piyasa rejimi bağlamı:" in kaynak
    assert "guven_duzeyi" in kaynak
    assert "analiz_tarihi" in kaynak
    assert "kaynak" in kaynak


def test_rejim_baglami_momentum_imzasina_dahil_edilir() -> None:
    kaynak = DASHBOARD.read_text(encoding="utf-8")

    assert "rejim_baglami_imzasi:" in kaynak
    assert "def piyasa_rejimi_baglami_imzasi" in kaynak
    assert "rejim_baglami_imzasi=piyasa_rejimi_baglami_imzasi(" in kaynak
