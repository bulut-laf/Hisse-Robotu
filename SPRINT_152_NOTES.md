# Sprint-152 — Olay Gruplama ve Tekrarlı Haber Birleştirme Motoru

## Amaç

Aynı piyasa olayını farklı kaynakların ayrı haberları olarak arşivlemek yerine,
güvenli ve deterministik kurallarla tek olay altında toplamak.

## Yeni davranış

- `AUTO_ATTACH`: yalnız güçlü ve açıklanabilir eşleşmede haber mevcut olaya
  otomatik bağlanır.
- `REVIEW`: benzer olay adayı vardır fakat güvenli otomatik eşik sağlanmaz.
  Kayıt yazılmaz; kullanıcıya mevcut olaya bağlama veya ayrı olay oluşturma
  kararı bırakılır.
- Eşleşme yoksa yeni olay normal şekilde oluşturulur.

## Eşleştirme girdileri

- Olay türü
- Piyasa kapsamı
- Olay zamanı / aynı takvim günü
- Hisse kesişimi (şirket olaylarında zorunlu)
- Başlık benzerliği (deterministik token/Jaccard)
- Güçlü kaynak referansı eşleşmesi

## Güvenlik sınırları

- `DIGER` olay türü otomatik gruplanmaz.
- `OTHER` piyasa kapsamı otomatik gruplanmaz.
- Farklı olay türleri asla otomatik birleştirilmez.
- Şirket olaylarında ortak hisse yoksa otomatik eşleşme yapılmaz.
- İnceleme düzeyindeki aday sessizce birleştirilmez.
- Kullanıcı otomatik eşleştirmeyi kapatarak bilinçli biçimde ayrı olay
  oluşturabilir.
- Manuel "Mevcut olaya haber bağla" seçimi otomatik motordan önce gelir.

## Değişmeyenler

- SQLite şeması
- Deterministik 0–100 önem skoru
- Kaynak sözlüğü ve Sprint-151 sınıflandırma kuralları
- Teknik analiz karar motoru
- AI entegrasyonu
- Otomatik internet/KAP/Reuters/Bloomberg çekme
