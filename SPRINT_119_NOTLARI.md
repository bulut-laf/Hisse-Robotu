# Sprint-119 — Gerçek Kullanım V2 Canlı Gözlem Başlangıcı

Amaç: Sprint-118 ile kapanan V2 modelini yeni özellik eklemeden gerçek kullanım verisi üzerinde gözlemlemek.

- Üretim eşikleri değiştirilmez.
- Model değişikliği otomatik uygulanmaz.
- Varsayılan değerlendirme eşiği: en az 20 gözlem günü, 30 ölçülmüş E2-E4 aday ve 2 güvenilir rejim/aşama grubu.
- Eşikler karşılanmadan sonuç `Veri biriktir` olarak kalır.
- Teknik sağlık bozuksa model değişikliği dondurulur.
- Eşikler karşılandığında yalnız `Değerlendirmeye hazır` durumu üretilir; otomatik kalibrasyon yapılmaz.

Başlangıç regresyon tabanı: 1482 passed.
