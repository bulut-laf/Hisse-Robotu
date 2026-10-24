from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from backend.app.history.trade_journal import (
    DENEME_HESABI,
    GERCEK_HESAP,
    TradeJournalError,
    TradeJournalStore,
    TradeRecord,
    csv_template_bytes,
    records_from_csv_bytes,
    records_to_csv_bytes,
)


def _record(**changes: object) -> TradeRecord:
    values: dict[str, object] = {
        "account_type": GERCEK_HESAP,
        "symbol": "THYAO",
        "entry_date": date(2026, 7, 1),
        "exit_date": date(2026, 7, 10),
        "entry_price": 100.0,
        "exit_price": 110.0,
        "quantity": 100,
        "capital_at_entry": 100_000.0,
        "stop_loss": 95.0,
        "target_price": 110.0,
        "fees": 20.0,
        "signal_class": "E3",
        "created_at": "2026-07-10T18:00:00",
    }
    values.update(changes)
    return TradeRecord(**values)  # type: ignore[arg-type]


def test_islem_kaydi_kar_risk_ve_rr_hesaplar() -> None:
    record = _record()

    assert record.symbol == "THYAO.IS"
    assert record.gross_pnl == pytest.approx(1_000.0)
    assert record.net_pnl == pytest.approx(980.0)
    assert record.return_pct == pytest.approx(9.8)
    assert record.planned_risk_amount == pytest.approx(500.0)
    assert record.planned_risk_pct == pytest.approx(0.5)
    assert record.planned_reward_risk == pytest.approx(2.0)
    assert record.realized_r == pytest.approx(1.96)


def test_islem_kaydi_gecersiz_tarih_ve_hesap_turunu_reddeder() -> None:
    with pytest.raises(ValueError, match="Çıkış tarihi"):
        _record(entry_date=date(2026, 7, 11), exit_date=date(2026, 7, 10))

    with pytest.raises(ValueError, match="Geçersiz hesap"):
        _record(account_type="Bilinmiyor")


def test_islem_gunlugu_jsona_yazar_okur_ve_siler(tmp_path: Path) -> None:
    store = TradeJournalStore(tmp_path / "islemler.json")
    first = _record(record_id="ilk")
    second = _record(
        record_id="ikinci",
        account_type=DENEME_HESABI,
        symbol="GARAN.IS",
        exit_date=date(2026, 7, 11),
    )

    store.save(first)
    store.save(second)

    assert [item.record_id for item in store.list_records()] == ["ilk", "ikinci"]
    assert store.delete("ilk") is True
    assert store.delete("yok") is False
    assert [item.record_id for item in store.list_records()] == ["ikinci"]


def test_csv_disari_ve_ice_aktarma_turkce_ondaliklari_destekler() -> None:
    csv_bytes = records_to_csv_bytes((_record(),))
    roundtrip = records_from_csv_bytes(csv_bytes)

    assert len(roundtrip) == 1
    assert roundtrip[0].symbol == "THYAO.IS"
    assert roundtrip[0].entry_price == pytest.approx(100.0)

    comma_csv = (
        "Hesap_Turu;Sembol;Giris_Tarihi;Cikis_Tarihi;Giris_Fiyati;"
        "Cikis_Fiyati;Lot;Sermaye;Stop;Hedef;Masraf;Sinyal_Sinifi;"
        "Gec_Giris;Kaybedene_Ekleme;Asiri_Yukselmis_Giris;Notlar\n"
        "Gerçek;ASELS;01.07.2026;10.07.2026;100,50;98,25;10;100000;"
        "97,00;107,50;5,50;E2;Evet;Hayır;Hayır;Test\n"
    ).encode("utf-8")
    parsed = records_from_csv_bytes(comma_csv)

    assert parsed[0].entry_price == pytest.approx(100.50)
    assert parsed[0].fees == pytest.approx(5.50)
    assert parsed[0].late_entry is True


def test_csv_sablonu_gecerli_ornek_islem_icerir() -> None:
    records = records_from_csv_bytes(csv_template_bytes())

    assert len(records) == 1
    assert records[0].account_type == DENEME_HESABI
    assert records[0].symbol == "THYAO.IS"


def test_csv_zorunlu_alan_eksikliginde_acik_hata_verir() -> None:
    with pytest.raises(TradeJournalError, match="zorunlu alanları eksik"):
        records_from_csv_bytes(b"Sembol;Lot\nTHYAO;10\n")


def test_ayni_csv_tekrar_aktarilinca_ayni_kayit_kimligi_uretilir(tmp_path: Path) -> None:
    content = records_to_csv_bytes((_record(),))
    first = records_from_csv_bytes(content)[0]
    second = records_from_csv_bytes(content)[0]
    store = TradeJournalStore(tmp_path / "islemler.json")

    store.save_many((first,))
    store.save_many((second,))

    assert first.record_id == second.record_id
    assert len(store.list_records()) == 1
