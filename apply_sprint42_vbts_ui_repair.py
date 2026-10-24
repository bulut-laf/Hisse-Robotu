from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "dashboard.py"
BACKUP = TARGET.with_suffix(".py.sprint42-vbts-ui-repair.bak")

MANAGER_IMPORT = 'from backend.app.compliance.dashboard_vbts_manager import (\n    DashboardVbtsManagerError,\n    add_vbts_record,\n    build_vbts_record,\n    configured_vbts_csv_path,\n    delete_vbts_record,\n    list_vbts_records,\n)\n'
PANEL_FUNCTION = 'def vbts_yonetim_paneli_goster() -> None:\n    csv_path = configured_vbts_csv_path()\n\n    with st.expander("VBTS kayıt yönetimi", expanded=False):\n        st.caption(\n            "Yalnızca resmî KAP bildirimlerinden doğrulanmış aktif tedbirleri girin."\n        )\n\n        try:\n            records = list_vbts_records(csv_path)\n        except DashboardVbtsManagerError as hata:\n            st.error(str(hata))\n            records = ()\n\n        if records:\n            st.dataframe(\n                pd.DataFrame(record.as_display_row() for record in records),\n                width="stretch",\n                hide_index=True,\n            )\n        else:\n            st.info("Kayıtlı aktif VBTS tedbiri bulunmuyor.")\n\n        st.markdown("**Yeni VBTS kaydı ekle**")\n        with st.form("vbts_kaydi_ekle_formu", clear_on_submit=True):\n            sol, sag = st.columns(2)\n            with sol:\n                sembol = st.text_input("Hisse sembolü", value="")\n                tedbir_turu = st.text_input("VBTS tedbir türü", value="")\n                baslangic = st.date_input(\n                    "Başlangıç tarihi",\n                    value=date.today(),\n                    key="vbts_baslangic_tarihi",\n                )\n            with sag:\n                bitis = st.date_input(\n                    "Bitiş tarihi",\n                    value=date.today() + timedelta(days=30),\n                    key="vbts_bitis_tarihi",\n                )\n                kap_referansi = st.text_input(\n                    "Resmî KAP bildirim referansı",\n                    value="",\n                )\n                resmi_onay = st.checkbox(\n                    "Kaydı resmî KAP bildirimiyle doğruladım.",\n                    value=False,\n                )\n\n            ekle = st.form_submit_button(\n                "VBTS kaydını ekle",\n                type="primary",\n                width="stretch",\n                disabled=not resmi_onay,\n            )\n\n        if ekle:\n            try:\n                record = build_vbts_record(\n                    symbol=sembol,\n                    measure_type=tedbir_turu,\n                    start_date=baslangic,\n                    end_date=bitis,\n                    source_reference=kap_referansi,\n                )\n                updated = add_vbts_record(csv_path, record)\n            except DashboardVbtsManagerError as hata:\n                st.error(str(hata))\n            else:\n                st.session_state["vbts_yonetim_bildirimi"] = (\n                    f"{record.symbol.removesuffix(\'.IS\')} VBTS kaydı eklendi. "\n                    f"Toplam kayıt: {len(updated)}"\n                )\n                st.rerun()\n\n        if records:\n            st.divider()\n            record_map = {\n                (\n                    f"{record.symbol.removesuffix(\'.IS\')} · "\n                    f"{record.measure_type} · {record.source_reference}"\n                ): record\n                for record in records\n            }\n            selected_label = st.selectbox(\n                "Silinecek VBTS kaydı",\n                options=tuple(record_map),\n                key="vbts_silinecek_kayit",\n            )\n            delete_confirmed = st.checkbox(\n                "Seçili kaydın CSV dosyasından kaldırılmasını onaylıyorum.",\n                value=False,\n                key="vbts_silme_onayi",\n            )\n            delete_requested = st.button(\n                "Seçili VBTS kaydını sil",\n                width="stretch",\n                disabled=not delete_confirmed,\n                key="vbts_kaydi_sil",\n            )\n\n            if delete_requested:\n                selected = record_map[selected_label]\n                try:\n                    remaining = delete_vbts_record(\n                        csv_path,\n                        selected.record_key,\n                    )\n                except DashboardVbtsManagerError as hata:\n                    st.error(str(hata))\n                else:\n                    st.session_state["vbts_yonetim_bildirimi"] = (\n                        "VBTS kaydı silindi. "\n                        f"Kalan kayıt: {len(remaining)}"\n                    )\n                    st.rerun()\n\n\n'


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")
    shutil.copy2(TARGET, BACKUP)

    if MANAGER_IMPORT not in source:
        anchor = "from backend.app.compliance.kap_factory import build_kap_vbts_service\n"
        if anchor not in source:
            fail("Compliance import yerleştirme noktası bulunamadı.")
        source = source.replace(anchor, MANAGER_IMPORT + anchor, 1)

    if "def vbts_yonetim_paneli_goster() -> None:" not in source:
        anchors = (
            "def manuel_vbts_durum_paneli_goster() -> None:",
            "def kap_vbts_durum_karti_goster() -> bool:",
        )
        pos = -1
        for anchor in anchors:
            pos = source.find(anchor)
            if pos >= 0:
                break
        if pos < 0:
            fail("VBTS paneli için yerleştirme noktası bulunamadı.")
        source = source[:pos] + PANEL_FUNCTION + source[pos:]

    form_start = source.find("def bist_toplu_tarama_formu() -> None:")
    if form_start < 0:
        fail("BIST toplu tarama formu bulunamadı.")

    next_def = source.find("\ndef ", form_start + 1)
    form_end = len(source) if next_def < 0 else next_def
    section = source[form_start:form_end]

    if 'st.session_state.pop("vbts_yonetim_bildirimi", None)' not in section:
        section = section.replace(
            "def bist_toplu_tarama_formu() -> None:\n",
            "def bist_toplu_tarama_formu() -> None:\n"
            '    bildirim = st.session_state.pop("vbts_yonetim_bildirimi", None)\n'
            "    if bildirim:\n"
            "        st.success(bildirim)\n\n",
            1,
        )

    if "vbts_yonetim_paneli_goster()" not in section:
        if "    manuel_vbts_durum_paneli_goster()\n" in section:
            section = section.replace(
                "    manuel_vbts_durum_paneli_goster()\n",
                "    manuel_vbts_durum_paneli_goster()\n"
                "    vbts_yonetim_paneli_goster()\n",
                1,
            )
        elif "    kap_vbts_durum_karti_goster()\n" in section:
            section = section.replace(
                "    kap_vbts_durum_karti_goster()\n",
                "    kap_vbts_durum_karti_goster()\n"
                "    vbts_yonetim_paneli_goster()\n",
                1,
            )
        else:
            fail("Toplu tarama VBTS çağrı noktası bulunamadı.")

    source = source[:form_start] + section + source[form_end:]
    compile(source, str(TARGET), "exec")
    TARGET.write_text(source, encoding="utf-8", newline="\n")

    print("Sprint-42 VBTS arayüz yönetimi onarılarak uygulandı.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
