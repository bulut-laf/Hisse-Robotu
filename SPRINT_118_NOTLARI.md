# Sprint-118 — Gerçek Kullanım V2 Kapanışı

## Amaç
Sprint-114–117 doğrulama katmanlarını tek final raporda birleştirmek ve Gerçek Kullanım V2 fazını teknik olarak kapatmak.

## İlkeler
- Teknik hazır olma ile model kanıt seviyesi ayrıdır.
- Yetersiz örneklemde performans başarısı ilan edilmez.
- Kalibrasyon adayı varsa yalnız kontrollü inceleme önerilir.
- Üretim eşikleri otomatik değiştirilmez.
- Aday kalitesi, kaçırılan fırsatlar, piyasa rejimi ve kalibrasyon tek raporda özetlenir.

## Yeni dosyalar
- `backend/app/prebreakout/prebreakout_v2_closure.py`
- `backend/tests/test_prebreakout_v2_closure.py`

## Kabul
- Final rapor teknik kapanışı gösterir.
- Kanıt seviyesi Yetersiz / Gelişiyor / Yeterli olarak ayrılır.
- Karar Gözleme devam / Mevcut eşikleri koru / Kalibrasyon adayını incele biçimindedir.
- Otomatik eşik uygulaması daima kapalıdır.
