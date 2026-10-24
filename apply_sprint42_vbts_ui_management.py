from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "dashboard.py"
BACKUP = TARGET.with_suffix(".py.sprint42-vbts-ui.bak")

IMPORT_ANCHOR = 'from backend.app.compliance.dashboard_market_scanner_source_factory import (\n    DashboardMarketScannerSourceError,\n    build_dashboard_market_scanner,\n)\n'
MANAGER_IMPORT = 'from backend.app.compliance.dashboard_vbts_manager import (\n    DashboardVbtsManagerError,\n    add_vbts_record,\n    build_vbts_record,\n    configured_vbts_csv_path,\n    delete_vbts_record,\n    list_vbts_records,\n)\n'
FUNCTION_ANCHOR = 'def manuel_vbts_durum_paneli_goster() -> None:\\n'
PANEL_FUNCTION = 'def vbts_yonetim_paneli_goster() -> None:\n    """VBTS kayıtlarını arayüzden güvenli biçimde ekler, listeler ve siler."""\n\n    csv_path = configured_vbts_csv_path()\n\n    with st.expander("VBTS kayıt yönetimi", expanded=False):\n        st.caption(\n            "Yalnızca resmî KAP bildirimlerinden doğrulanmış aktif tedbirleri "\n            "girin. Bu bölüm yatırım tavsiyesi üretmez."\n        )\n\n        try:\n            records = list_vbts_records(csv_path)\n        except DashboardVbtsManagerError as hata:\n            st.error(str(hata))\n            records = ()\n\n        if records:\n            st.dataframe(\n                pd.DataFrame(record.as_display_row() for record in records),\n                width="stretch",\n                hide_index=True,\n            )\n        else:\n            st.info("Kayıtlı aktif VBTS tedbiri bulunmuyor.")\n\n        st.markdown("**Yeni VBTS kaydı ekle**")\n        with st.form("vbts_kaydi_ekle_formu", clear_on_submit=True):\n            sol, sag = st.columns(2)\n            with sol:\n                sembol = st.text_input("Hisse sembolü", value="")\n                tedbir_turu = st.text_input("VBTS tedbir türü", value="")\n                baslangic = st.date_input(\n                    "Başlangıç tarihi",\n                    value=date.today(),\n                    key="vbts_baslangic_tarihi",\n                )\n            with sag:\n                bitis = st.date_input(\n                    "Bitiş tarihi",\n                    value=date.today() + timedelta(days=30),\n                    key="vbts_bitis_tarihi",\n                )\n                kap_referansi = st.text_input(\n                    "Resmî KAP bildirim referansı",\n                    value="",\n                )\n                resmi_onay = st.checkbox(\n                    "Kaydı resmî KAP bildirimiyle doğruladım.",\n                    value=False,\n                )\n\n            ekle = st.form_submit_button(\n                "VBTS kaydını ekle",\n                type="primary",\n                width="stretch",\n                disabled=not resmi_onay,\n            )\n\n        if ekle:\n            try:\n                record = build_vbts_record(\n                    symbol=sembol,\n                    measure_type=tedbir_turu,\n                    start_date=baslangic,\n                    end_date=bitis,\n                    source_reference=kap_referansi,\n                )\n                updated = add_vbts_record(csv_path, record)\n            except DashboardVbtsManagerError as hata:\n                st.error(str(hata))\n            else:\n                st.session_state["vbts_yonetim_bildirimi"] = (\n                    f"{record.symbol.removesuffix(\'.IS\')} VBTS kaydı eklendi. "\n                    f"Toplam kayıt: {len(updated)}"\n                )\n                st.rerun()\n\n        if records:\n            st.divider()\n            st.markdown("**Kayıt silme**")\n            record_map = {\n                (\n                    f"{record.symbol.removesuffix(\'.IS\')} · "\n                    f"{record.measure_type} · {record.source_reference}"\n                ): record\n                for record in records\n            }\n            selected_label = st.selectbox(\n                "Silinecek VBTS kaydı",\n                options=tuple(record_map),\n                key="vbts_silinecek_kayit",\n            )\n            delete_confirmed = st.checkbox(\n                "Seçili kaydın CSV dosyasından kaldırılmasını onaylıyorum.",\n                value=False,\n                key="vbts_silme_onayi",\n            )\n            delete_requested = st.button(\n                "Seçili VBTS kaydını sil",\n                type="secondary",\n                width="stretch",\n                disabled=not delete_confirmed,\n                key="vbts_kaydi_sil",\n            )\n\n            if delete_requested:\n                selected = record_map[selected_label]\n                try:\n                    remaining = delete_vbts_record(\n                        csv_path,\n                        selected.record_key,\n                    )\n                except DashboardVbtsManagerError as hata:\n                    st.error(str(hata))\n                else:\n                    st.session_state["vbts_yonetim_bildirimi"] = (\n                        "VBTS kaydı silindi. "\n                        f"Kalan kayıt: {len(remaining)}"\n                    )\n                    st.rerun()\n\n\n'
FORM_ANCHOR = 'def bist_toplu_tarama_formu() -> None:\n    kap_vbts_durum_karti_goster()\n    manuel_vbts_durum_paneli_goster()\n'
FORM_REPLACEMENT = 'def bist_toplu_tarama_formu() -> None:\n    bildirim = st.session_state.pop("vbts_yonetim_bildirimi", None)\n    if bildirim:\n        st.success(bildirim)\n\n    kap_vbts_durum_karti_goster()\n    manuel_vbts_durum_paneli_goster()\n    vbts_yonetim_paneli_goster()\n'


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    shutil.copy2(TARGET, BACKUP)

    if MANAGER_IMPORT not in source:
        if IMPORT_ANCHOR not in source:
            fail("Dashboard compliance import bölümü bulunamadı.")
        source = source.replace(
            IMPORT_ANCHOR,
            IMPORT_ANCHOR + MANAGER_IMPORT,
            1,
        )

    if "def vbts_yonetim_paneli_goster() -> None:" not in source:
        if FUNCTION_ANCHOR not in source:
            fail("Manuel VBTS durum paneli bulunamadı.")
        source = source.replace(
            FUNCTION_ANCHOR,
            PANEL_FUNCTION + FUNCTION_ANCHOR,
            1,
        )

    if FORM_REPLACEMENT not in source:
        if FORM_ANCHOR not in source:
            fail("BIST toplu tarama formu başlangıcı bulunamadı.")
        source = source.replace(FORM_ANCHOR, FORM_REPLACEMENT, 1)

    compile(source, str(TARGET), "exec")
    TARGET.write_text(source, encoding="utf-8", newline="\n")

    print("Sprint-42 VBTS arayüz yönetimi uygulandı.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
