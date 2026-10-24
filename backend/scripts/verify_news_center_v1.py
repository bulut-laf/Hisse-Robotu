from __future__ import annotations
from pathlib import Path
import sys

def _force_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass

_force_utf8_console()

from backend.app.news_center.v1_release import NEWS_CENTER_V1_OFFICIAL_SOURCES, NEWS_CENTER_V1_VERSION, NewsCenterV1Check, validate_news_center_v1_backend
from backend.app.ui.official_source_feed_renderer import official_source_feed_ui_names

def _make(name,passed,detail): return NewsCenterV1Check(name=name,passed=bool(passed),detail="" if passed else detail)
def _ui_checks():
    root=Path(__file__).resolve().parents[2]
    try:
        dashboard=(root/'backend/app/ui/news_center_dashboard.py').read_text(encoding='utf-8')
        panel=(root/'backend/app/ui/daily_news_operations_panel.py').read_text(encoding='utf-8')
    except OSError as exc:
        return (_make('ui_files',False,f'V1 UI dosyaları okunamadı: {exc}'),)
    tabs=("Günlük Operasyon","Kaynak Besleme","Son Dakika","Bugünün Önemli Gelişmeleri","Gün Sonu Özeti","Ekonomik Takvim","KAP Akışı","Hisse Haberleri","Manuel Haber Ekle","Olay Arşivi","Etki Bağlantıları","Sektör Etki Haritası","Portföy Etki Radarı","Haber Arşivi")
    normalized=' '.join(panel.split())
    return (
        _make('feed_ui_sources',official_source_feed_ui_names()==NEWS_CENTER_V1_OFFICIAL_SOURCES,'Kaynak Besleme UI kaynak listesi backend V1 manifestiyle eşleşmiyor.'),
        _make('dashboard_v1_version','NEWS_CENTER_V1_VERSION' in dashboard and 'Haber Merkezi V' in dashboard and 'Sprint-178' in dashboard,'Dashboard V1 sürüm kimliğini göstermiyor.'),
        _make('dashboard_tabs',all(f'"{x}"' in dashboard for x in tabs),'V1 Haber Merkezi sekmelerinden biri dashboardda eksik.'),
        _make('dashboard_no_legacy_streamlit_width','use_container_width' not in dashboard and 'use_container_width' not in panel,'V1 UI içinde eski Streamlit width API kullanımı bulundu.'),
        _make('daily_operations_guardrails','Yeni birleşik skor' in panel and 'AL/SAT' in panel and 'AI yorumu' in panel and 'yeni ağ' in normalized and 'isteği göndermez' in normalized,'Günlük Operasyon ekranı V1 karar/güvenlik sınırlarını açıklamıyor.'),
    )
def main():
    checks=validate_news_center_v1_backend().checks+_ui_checks()
    print(f'HABER MERKEZİ V{NEWS_CENTER_V1_VERSION} — SİSTEM KONTROLÜ'); print('='*58)
    for x in checks:
        print(f"{'[OK]' if x.passed else '[HATA]'} {x.name}" + (f' — {x.detail}' if x.detail else ''))
    passed=sum(x.passed for x in checks); failed=len(checks)-passed
    print('='*58); print(f'Sonuç: {passed} başarılı / {failed} hata')
    if failed: print('HABER MERKEZİ V1 DOĞRULAMASI BAŞARISIZ'); return 1
    print(f'HABER MERKEZİ V{NEWS_CENTER_V1_VERSION} SİSTEM KONTROLÜ BAŞARILI'); return 0
if __name__=='__main__': raise SystemExit(main())
