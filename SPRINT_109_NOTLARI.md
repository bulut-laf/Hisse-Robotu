# Sprint-109 — Teşhise Dayalı Kurtarma Rehberi

- Sprint-108 kök neden sınıfları güvenli kurtarma adımlarına bağlandı.
- VERI ve KAYIT_BUTUNLUGU sorunlarında otomatik yeniden deneme önerilmez.
- SAGLIK_KILIDI ve HESAPLAMA sorunlarında önce düzeltme/doğrulama, sonra güvenli yeniden deneme önerilir.
- PORTFOY sorununda işlem/özet tutarlılığı doğrulanmadan yeniden hesaplama yapılmaz.
- Sağlıklı operasyonda kurtarma işlemi gerekmiyor olarak raporlanır.
- Kurtarma rehberi atomik JSON olarak backend/data/prebreakout_operation_recovery.json dosyasına yazılır.
- Günlük operasyon FAILED, BLOCKED ve COMPLETED sonuçlarında teşhis ile birlikte kurtarma rehberi de üretir.
- Sistem otomatik dosya düzeltmesi veya veri onarımı yapmaz; yalnız kontrollü öneri üretir.
- Yeni indikatör veya strateji eklenmemiştir.
