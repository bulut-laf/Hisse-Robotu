# Veri Tazeliği Rev1 — Toplu yfinance end tarihi düzeltmesi

Sorun:
- Tek sembol günlük sorgusu 2026-07-31 barını alıyordu.
- BIST 100 toplu sorgusu 100 sembolün tamamını 2026-07-30 ile kapatıyordu.
- yfinance `end` tarihini sonuçlara dahil etmediği için toplu tarama son günü
  bir gün eksik indiriyordu.

Düzeltme:
- Toplu ve referans günlük sorgularında `period=` kaldırıldı.
- Açık `start=` ve `end=` tarihleri kullanılmaya başlandı.
- `end`, bugünün ertesi günü olarak gönderilir.
- 2026-07-31 için yfinance sorgusu `end=2026-08-01` kullanır.
- Veri tazeliği kilidi kaldırılmadı veya gevşetilmedi.
- Yalnızca doğru son günlük barın indirilmesi sağlandı.
