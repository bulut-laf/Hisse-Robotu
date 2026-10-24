# Sprint-131 — Erken Radar Tarama Entegrasyonu

## Amaç
Sprint-129 karar motoru ile Sprint-130 UI kartlarını gerçek tarama çıktısına bağlayan köprü katmanı.

## Yeni modül
`backend/app/prebreakout/prebreakout_scan_radar_integration.py`

## Akış
Tarama adayı
→ ScanCandidateSnapshot
→ EarlyRadarInput
→ Sprint-129 classify_early_radar
→ Sprint-130 EarlyRadarCard
→ Streamlit paneli

## Desteklenen girişler
- Doğrudan tipli tarama adayı
- Mapping/dict satırı
- Türkçe export sütunları
- Sade İngilizce alan adları

## Güvenlik
- Ana tarama motorunun sırası değişmez.
- Mevcut teknik skor değiştirilmez.
- Erken Radar ikinci karar ekseni olarak kalır.
- Geçmiş metrikleri eksikse güvenli şekilde 0/None kullanılır; sahte ivme üretilmez.
- UI entegrasyonu için mevcut büyük Streamlit dosyaları doğrudan yamalanmaz.

## Sonraki doğrulama
Sprint-132'de gerçek/historik tarama çıktılarında günlük sıra geçmişi oluşturulup
Erken Radar kartlarının gerçek veriyle uçtan uca davranışı doğrulanabilir.
