import pandas as pd

from backend.app.analysis.bist_universe import BistUniverse
from backend.app.prebreakout.prebreakout_universe import (
    ON_YUKSELIS_EVRENLERI,
    on_yukselis_evrenini_yukle,
    sonuc_limitini_kesim_bazinda_uygula,
    sonuc_limitini_uygula,
)


class SahteEvrenDeposu:
    def evreni_yukle(self, evren_adi: str, internetten_guncelle: bool = True) -> BistUniverse:
        return BistUniverse(
            ad=evren_adi,
            endeks_kodu="XU050",
            semboller=("AAA.IS", "BBB.IS"),
            tarih="02/08/2026",
            kaynak="Test kaynağı",
            resmi_kaynaktan_guncel=internetten_guncelle,
        )


def test_tum_beklenen_evren_secenekleri_sunulur() -> None:
    assert ON_YUKSELIS_EVRENLERI == (
        "BIST 30",
        "BIST 50",
        "BIST 100",
        "BIST Tüm",
        "Özel Liste",
    )


def test_bist_evreni_ortak_depodan_yuklenir() -> None:
    selection = on_yukselis_evrenini_yukle(
        "BIST 50",
        repository=SahteEvrenDeposu(),  # type: ignore[arg-type]
    )
    assert selection.semboller == ("AAA.IS", "BBB.IS")
    assert selection.kaynak == "Test kaynağı"
    assert selection.tarih == "02/08/2026"


def test_ozel_liste_normalize_edilir() -> None:
    selection = on_yukselis_evrenini_yukle(
        "Özel Liste",
        "thyao, ASELS.IS, thyao",
    )
    assert selection.semboller == ("THYAO.IS", "ASELS.IS")


def test_sonuc_limiti_siralanmis_tablonun_basina_uygulanir() -> None:
    table = pd.DataFrame({"score": list(range(60))})
    assert len(sonuc_limitini_uygula(table, "İlk 25")) == 25
    assert len(sonuc_limitini_uygula(table, "Tümü")) == 60


def test_toplu_dogrulama_limiti_her_kesime_ayri_uygulanir() -> None:
    table = pd.DataFrame(
        {
            "cutoff_date": ["2026-07-01"] * 30 + ["2026-07-08"] * 30,
            "score": list(range(60)),
        }
    )
    result = sonuc_limitini_kesim_bazinda_uygula(table, "İlk 10")
    assert result.groupby("cutoff_date").size().to_dict() == {
        "2026-07-01": 10,
        "2026-07-08": 10,
    }
