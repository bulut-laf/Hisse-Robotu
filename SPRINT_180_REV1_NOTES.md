# Sprint-180 Rev1 — Halka Açık Haber Akışı Performans Düzeltmesi

## Neden
Canlı RSS doğrulamasında 80 kayıt başarıyla okundu ve 80 yeni haber bulundu; ancak Kaynak Besleme sayfası belirgin biçimde yavaşladı.

## Düzeltmeler
- RSS dry-run duplicate kontrolü artık her haber için tüm arşivi tekrar okumaz; tek yenilemede arşiv hash indeksi bir kez yüklenir.
- Aynı yenileme içinde yinelenen içerik ikinci kez yeni haber sayılmaz.
- Önizleme tablosu performans için en yeni 20 satırı render eder; tam önizleme listesi ve aktarım kapsamı bellekte korunur.
- Arşive aktarım, doğrulanmış preview nesnesini kullanır ve her kayıt öncesi gereksiz tam arşiv taramasını tekrarlamaz.
- Mevcut açık onay, kaynak doğrulama, duplicate ve veritabanı UNIQUE güvenlik davranışları korunur.
