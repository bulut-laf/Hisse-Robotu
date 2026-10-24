# Sprint-123 — Karar Geçmişi ve Gerçek Kullanım Dönem Karşılaştırması

- Sprint-122 karar geçmişi append-only JSONL kayıt yapısıyla kalıcılaştırıldı.
- Aynı dönem ve aynı gözlem günü ikinci kez yazılmaz.
- Gerçek kullanım verisi dönem bazında özetlenir.
- Dönemler: İyileşiyor / Benzer / Kötüleşiyor / Yetersiz veri olarak karşılaştırılır.
- Modeli koru ve Kalibrasyon adayı karar payları; başarı, yanlış pozitif ve deneme portföyü getirileri birlikte değerlendirilir.
- Dönem karşılaştırması otomatik eşik değişikliği yapmaz.
