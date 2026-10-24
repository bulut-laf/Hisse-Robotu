# Sprint-168 — Üçüncü Kontrollü Resmî Kaynak Adapteri (TÜİK)

Yeni TÜİK Veri Portalı tek haber bülteni URL'si desteklenir:
`https://veriportali.tuik.gov.tr/tr/press/<sayı>`.

- Ağ erişimi varsayılan kapalıdır ve her önizlemede açık kullanıcı onayı ister.
- Yalnız HTTPS, yalnız `veriportali.tuik.gov.tr`, yalnız `/tr/press/<sayı>` kabul edilir.
- URL numarası ile sayfadaki `Sayı` uyuşmazsa kayıt reddedilir.
- 10 saniye timeout, 2 MB yanıt sınırı, HTML zorunluluğu vardır.
- Otomatik polling, toplu scraping ve arka plan taraması yoktur.
- Yayım Tarihi, Sayı, başlık ve görünür bülten metni alınır.
- Hisse veya sektör çıkarılmaz; kapsam `TURKEY_MACRO` olur.
- Başlık temelli deterministik olay türü: ENFLASYON / ISTIHDAM / BUYUME / SEKTOR / DIGER.
- AI sınıflandırması, yön, AL/SAT veya teknik skor değişikliği yoktur.
- Dry-run ve ayrıca açık arşivleme onayı zorunludur.
