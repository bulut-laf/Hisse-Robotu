# Sprint-159 — Ekonomik Takvim ve Beklenti/Olay İzleme

- Manuel, deterministik ekonomik takvim.
- Olay adı, ülke/bölge, kategori, Türkiye saati, önem, önceki/beklenti/açıklanan, kaynak ve not.
- Önceki/beklenti/açıklanan değerleri ham metin olarak saklanır.
- Sistem “beklentiden iyi/kötü”, fiyat yönü veya AL/SAT yorumu üretmez.
- Aynı olay (başlık + ülke + kategori + zaman) SHA-256 kimliğiyle duplicate engellenir.
- Sonuç açıklandıktan sonra değerler güncellenebilir.
- Aynı News Center SQLite dosyasında ayrı `economic_calendar` tablosu kullanılır.
- Otomatik internet/API ve AI yok.
