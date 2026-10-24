from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "dashboard.py"
BACKUP = TARGET.with_suffix(".py.sprint43-vbts-lifecycle.bak")

NEW_IMPORT = 'from backend.app.compliance.dashboard_vbts_manager import (\n    DashboardVbtsManagerError,\n    add_vbts_record,\n    build_vbts_record,\n    classify_vbts_records,\n    configured_vbts_csv_path,\n    delete_vbts_record,\n    list_vbts_records,\n    purge_expired_vbts_records,\n    sync_active_vbts_csv,\n)\n'
NEW_PANEL = 'def vbts_yonetim_paneli_goster() -> None:\n    csv_path = configured_vbts_csv_path()\n\n    with st.expander("VBTS kayıt yönetimi", expanded=False):\n        st.caption(\n            "Yalnızca resmî KAP bildirimlerinden doğrulanmış tedbirleri girin. "\n            "Taramada sadece bugün aktif olan kayıtlar kullanılır."\n        )\n\n        try:\n            records = list_vbts_records(csv_path)\n            lifecycle = sync_active_vbts_csv(csv_path, records)\n        except DashboardVbtsManagerError as hata:\n            st.error(str(hata))\n            records = ()\n            lifecycle = classify_vbts_records(())\n\n        metrik_izgarasi_goster(\n            (\n                ("Aktif kayıt", str(len(lifecycle.active))),\n                ("Gelecekte başlayacak", str(len(lifecycle.future))),\n                ("Süresi dolmuş", str(len(lifecycle.expired))),\n                ("Toplam arşiv kaydı", str(len(records))),\n            )\n        )\n\n        if records:\n            st.dataframe(\n                pd.DataFrame(record.as_display_row() for record in records),\n                width="stretch",\n                hide_index=True,\n            )\n        else:\n            st.info("Kayıtlı VBTS tedbiri bulunmuyor.")\n\n        if lifecycle.expired:\n            st.warning(\n                "Süresi dolmuş kayıtlar arşivde tutuluyor ancak toplu tarama "\n                "filtresine dahil edilmiyor."\n            )\n            cleanup_confirmed = st.checkbox(\n                "Süresi dolmuş kayıtların kalıcı olarak silinmesini onaylıyorum.",\n                value=False,\n                key="vbts_suresi_dolmus_temizlik_onayi",\n            )\n            cleanup_requested = st.button(\n                "Süresi dolmuş kayıtları temizle",\n                width="stretch",\n                disabled=not cleanup_confirmed,\n                key="vbts_suresi_dolmus_temizle",\n            )\n            if cleanup_requested:\n                try:\n                    remaining = purge_expired_vbts_records(csv_path)\n                except DashboardVbtsManagerError as hata:\n                    st.error(str(hata))\n                else:\n                    st.session_state["vbts_yonetim_bildirimi"] = (\n                        "Süresi dolmuş VBTS kayıtları temizlendi. "\n                        f"Kalan arşiv kaydı: {len(remaining)}"\n                    )\n                    st.rerun()\n\n        st.markdown("**Yeni VBTS kaydı ekle**")\n        with st.form("vbts_kaydi_ekle_formu", clear_on_submit=True):\n            sol, sag = st.columns(2)\n            with sol:\n                sembol = st.text_input("Hisse sembolü", value="")\n                tedbir_turu = st.text_input("VBTS tedbir türü", value="")\n                baslangic = st.date_input(\n                    "Başlangıç tarihi",\n                    value=date.today(),\n                    key="vbts_baslangic_tarihi",\n                )\n            with sag:\n                bitis = st.date_input(\n                    "Bitiş tarihi",\n                    value=date.today() + timedelta(days=30),\n                    key="vbts_bitis_tarihi",\n                )\n                kap_referansi = st.text_input(\n                    "Resmî KAP bildirim referansı",\n                    value="",\n                )\n                resmi_onay = st.checkbox(\n                    "Resmî KAP bildirimiyle doğruladım.",\n                    value=False,\n                )\n\n            ekle = st.form_submit_button(\n                "VBTS kaydını ekle",\n                type="primary",\n                width="stretch",\n            )\n\n        if ekle:\n            if not resmi_onay:\n                st.error(\n                    "VBTS kaydı eklemek için resmî KAP bildirimiyle "\n                    "doğrulama onayı verilmelidir."\n                )\n                return\n\n            try:\n                record = build_vbts_record(\n                    symbol=sembol,\n                    measure_type=tedbir_turu,\n                    start_date=baslangic,\n                    end_date=bitis,\n                    source_reference=kap_referansi,\n                )\n                updated = add_vbts_record(csv_path, record)\n            except DashboardVbtsManagerError as hata:\n                st.error(str(hata))\n            else:\n                st.session_state["vbts_yonetim_bildirimi"] = (\n                    f"{record.symbol.removesuffix(\'.IS\')} VBTS kaydı eklendi. "\n                    f"Toplam arşiv kaydı: {len(updated)}"\n                )\n                st.rerun()\n\n        if records:\n            st.divider()\n            record_map = {\n                (\n                    f"{record.symbol.removesuffix(\'.IS\')} · "\n                    f"{record.status()} · {record.measure_type} · "\n                    f"{record.source_reference}"\n                ): record\n                for record in records\n            }\n            selected_label = st.selectbox(\n                "Silinecek VBTS kaydı",\n                options=tuple(record_map),\n                key="vbts_silinecek_kayit",\n            )\n            delete_confirmed = st.checkbox(\n                "Seçili kaydın arşivden kalıcı olarak kaldırılmasını onaylıyorum.",\n                value=False,\n                key="vbts_silme_onayi",\n            )\n            delete_requested = st.button(\n                "Seçili VBTS kaydını sil",\n                width="stretch",\n                disabled=not delete_confirmed,\n                key="vbts_kaydi_sil",\n            )\n\n            if delete_requested:\n                selected = record_map[selected_label]\n                try:\n                    remaining = delete_vbts_record(\n                        csv_path,\n                        selected.record_key,\n                    )\n                except DashboardVbtsManagerError as hata:\n                    st.error(str(hata))\n                else:\n                    st.session_state["vbts_yonetim_bildirimi"] = (\n                        "VBTS kaydı silindi. "\n                        f"Kalan arşiv kaydı: {len(remaining)}"\n                    )\n                    st.rerun()\n\n\n'


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def replace_import_block(source: str) -> str:
    start = source.find(
        "from backend.app.compliance.dashboard_vbts_manager import ("
    )
    if start < 0:
        fail("VBTS yönetici import bloğu bulunamadı.")

    end = source.find("\n)\n", start)
    if end < 0:
        fail("VBTS yönetici import bloğu sonu bulunamadı.")

    return source[:start] + NEW_IMPORT + source[end + 3:]


def replace_panel(source: str) -> str:
    start = source.find("def vbts_yonetim_paneli_goster() -> None:")
    if start < 0:
        fail("VBTS yönetim paneli bulunamadı.")

    end = source.find("\ndef manuel_vbts_durum_paneli_goster()", start)
    if end < 0:
        fail("VBTS yönetim paneli sonu bulunamadı.")

    return source[:start] + NEW_PANEL + source[end + 1:]


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    shutil.copy2(TARGET, BACKUP)

    source = replace_import_block(source)
    source = replace_panel(source)

    compile(source, str(TARGET), "exec")
    TARGET.write_text(source, encoding="utf-8", newline="\n")

    print("Sprint-43 VBTS yaşam döngüsü uygulandı.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
