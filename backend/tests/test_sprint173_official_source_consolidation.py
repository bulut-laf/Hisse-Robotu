from pathlib import Path


ROOT = Path("backend/app/news_center")
ADAPTERS = (
    "kap_adapter.py",
    "tcmb_adapter.py",
    "tuik_adapter.py",
    "spk_adapter.py",
    "hmb_adapter.py",
    "borsa_istanbul_adapter.py",
    "resmi_gazete_adapter.py",
)


def _source(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_yedi_adapter_ortak_http_cekrdegini_kullanir():
    for name in ADAPTERS:
        text = _source(name)
        assert "from .official_source_http import (" in text, name
        assert "fetch_official_source_bytes" in text, name
        assert "validate_official_source_html_payload" in text, name
        assert "decode_official_source_html" in text, name
        assert "validate_official_source_timeout" in text, name


def test_adapterlerde_dogrudan_urllib_transport_kalmadi():
    for name in ADAPTERS:
        text = _source(name)
        assert "from urllib.request import Request, urlopen" not in text, name
        assert "from urllib.error import HTTPError, URLError" not in text, name
        assert "urlopen(" not in text, name


def test_adapterlerde_iki_mb_ve_timeout_sabitleri_ortaktan_gelir():
    for name in ADAPTERS:
        text = _source(name)
        assert "MAX_RESPONSE_BYTES = OFFICIAL_SOURCE_MAX_RESPONSE_BYTES" in text, name
        assert "DEFAULT_TIMEOUT_SECONDS = OFFICIAL_SOURCE_DEFAULT_TIMEOUT_SECONDS" in text, name
        assert "MAX_RESPONSE_BYTES = 2_000_000" not in text, name
        assert "DEFAULT_TIMEOUT_SECONDS = 10" not in text, name


def test_adapterlerin_default_fetch_enjeksiyon_sozlesmesi_korunur():
    for name in ADAPTERS:
        text = _source(name)
        assert "def _default_fetch(url: str, timeout_seconds: int) -> tuple[bytes, str, str]:" in text, name
        assert "FetchBytes = Callable[[str, int], tuple[bytes, str, str]]" in text, name


def test_url_whitelistleri_adapterlerde_kalmaya_devam_eder():
    for name in ADAPTERS:
        text = _source(name)
        assert "_ALLOWED_HOSTS" in text, name
        assert "urlparse(" in text, name


def test_ag_varsayilan_kapali_sozlesmesi_korunur():
    for name in ADAPTERS:
        text = _source(name)
        assert "network_enabled: bool = False" in text, name
        assert "if not self.network_enabled:" in text, name


def test_ui_yedi_adapteri_korumaya_devam_eder():
    text = Path("backend/app/ui/news_center_dashboard.py").read_text(encoding="utf-8")
    assert "official_source_adapter_names" in text
    assert 'metric("Aktif adapter",' in text
    assert "Sprint-173" in text


def test_polling_ve_otomatik_tarama_acilmadi():
    text = Path("backend/app/ui/news_center_dashboard.py").read_text(encoding="utf-8")
    assert "otomatik polling yapmaz" in text
