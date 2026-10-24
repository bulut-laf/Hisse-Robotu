# Sprint-133 — Tarih Aralığı Toplu Tarihsel Export Motoru

## Amaç
Tek tek gün seçip CSV dışa aktarma ihtiyacını kaldırmak.

## Yeni motor
`backend/app/history/batch_historical_export.py`

## Özellikler
- Başlangıç tarihi
- Bitiş tarihi
- Evren: BIST100 / BIST Tüm / mevcut tarayıcının desteklediği diğer evrenler
- Hafta sonlarını otomatik atlama
- Her kesim tarihini otomatik taratma
- Her satıra `Kesim Tarihi` ve `Evren` ekleme
- Tek birleşik CSV üretme
- İsteğe bağlı günlük CSV'leri tek ZIP içinde üretme
- Türkçe export sütunlarını aynen koruma

## Tercih edilen çıktı
Tek birleşik CSV:
`tarihsel_toplu_BIST100_2026-06-29_2026-07-29.csv`

Bu yapı Sprint-132 günlük sıra yolculuğu analizine doğrudan uygundur.

## Mimari not
Bu sprint toplu export motorunu güvenli ve test edilebilir biçimde ekler.
Mevcut tarihsel replay tarayıcısının gerçek `scan_day` fonksiyonuna UI üzerinden bağlanması
bir sonraki entegrasyon adımıdır; mevcut tarayıcıya riskli yama yapılmamıştır.
