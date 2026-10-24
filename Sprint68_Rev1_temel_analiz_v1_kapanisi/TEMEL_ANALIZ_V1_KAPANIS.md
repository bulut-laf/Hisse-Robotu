# Temel Analiz V1 — Kapanış Belgesi

## Durum

Sprint-68 otomatik kapanış paketi hazırlanmıştır. V1 kapanışı; hedef test, tam regresyon, sistem kontrolü, sözdizimi kontrolü ve son kullanıcı görsel doğrulaması tamamlandığında onaylanacaktır.

## Dahil edilen yetenekler

1. Finansal dönem veri modeli
2. Veri tazeliği ve güvenlik kilidi
3. Manuel CSV/JSON veri girişi
4. Yapılandırılabilir KAP finansal veri kaynağı
5. Finansal oran hesaplamaları
6. 0–100 temel kalite skoru
7. Beş alt kalite skoru
8. Temel skor yerel deposu
9. Dönemsel skor geçmişi
10. Şirket ve sektör karşılaştırması
11. Sektör temel skor sıralaması
12. Sektör güç haritası
13. CSV ve PDF özet raporu
14. Yerel rapor arşivi
15. Geçmiş rapor karşılaştırması
16. Arşiv arama, filtreleme ve dışa aktarım
17. Temel analiz kullanıcı ayarları
18. Varsayılan ayarlara güvenli dönüş

## Güvenlik ilkeleri

- Temel analiz sonuçları alım/satım tavsiyesi üretmez.
- Temel skor teknik skorun yerine geçmez.
- Temel filtre BIST taramasında varsayılan olarak kapalıdır.
- VBTS güvenlik kilidi değiştirilmez veya atlanmaz.
- Eski, gelecek tarihli, kilitli ve uyumsuz finansal kayıtlar dışlanır.
- Sektör ve piyasa değeri tahmin edilmez.
- Eksik veri raporlarda açıkça belirtilir.

## Otomatik kapanış komutları

Hedef test:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest `
    backend\tests\test_fundamental_v1_closeout.py `
    backend\tests\test_fundamental_models.py `
    backend\tests\test_fundamental_data.py `
    backend\tests\test_fundamental_store.py `
    backend\tests\test_fundamental_analysis.py `
    backend\tests\test_fundamental_quality.py `
    backend\tests\test_fundamental_score_store.py `
    backend\tests\test_fundamental_score_history.py `
    backend\tests\test_sector_reference.py `
    backend\tests\test_sector_score_ranking.py `
    backend\tests\test_sector_strength_map.py `
    backend\tests\test_fundamental_report.py `
    backend\tests\test_fundamental_report_archive.py `
    backend\tests\test_fundamental_report_archive_filter.py `
    backend\tests\test_fundamental_settings.py `
    backend\tests\test_fundamental_settings_integration.py `
    backend\tests\test_streamlit_api_compatibility.py -q
```

Tam regresyon:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -q
```

Sistem kontrolü:

```powershell
& ".\.venv\Scripts\python.exe" -m backend.run_system_check
```

Sözdizimi:

```powershell
& ".\.venv\Scripts\python.exe" -m compileall backend -q
```

## Görsel kapanış ölçütü

Temel Analiz ekranında örnek finansal veriyle aşağıdakiler doğrulanmalıdır:

- Veri tazeliği ve kaynak durumu
- Toplam skor ve beş alt skor
- Skor geçmişi
- Finansal oranlar
- Sektör karşılaştırması
- Sektör sıralaması
- Sektör güç haritası
- CSV/PDF rapor üretimi
- Rapor arşivi ve filtreleri
- Temel analiz ayarları
- Varsayılan ayarlara dönüş

## Snapshot

Tüm doğrulamalar tamamlandıktan sonra:

```powershell
& ".\Hazirla-Temel-Analiz-V1-Snapshot.ps1"
```

komutu temiz kaynak ZIP’i, SHA-256 dosyasını ve kapanış manifestini `releases` klasöründe üretir.
