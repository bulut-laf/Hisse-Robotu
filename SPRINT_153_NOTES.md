# Sprint-153 — Haber/Olay Etki Etiketleri ve Sektör-Hisse Bağlantı Motoru

## Amaç

Haber Merkezi olaylarını deterministik biçimde BIST geneli, sektörler ve açıkça
belirtilen hisselerle ilişkilendirmek.

## Eklenenler

- `impact.py` bağımsız deterministik etki motoru.
- Etki hedef türleri: MARKET / SECTOR / SYMBOL.
- Bağlantı türleri:
  - DIRECT: olay kaydında açıkça bulunan hedef.
  - SENSITIVITY: sınırlı ve açıklanabilir sabit duyarlılık kuralı.
- Etki etiketleri: piyasa geneli, şirket, sektör, faiz, enflasyon, döviz,
  emtia, regülasyon, finansal sonuç, temettü, sermaye işlemi, finansman ve
  jeopolitik.
- Faiz/para politikası için Banka ve Gayrimenkul duyarlılığı.
- Döviz için sınırlı sektör duyarlılığı; şirket/hisse yönü çıkarılmaz.
- Enflasyon için Perakende ve Gıda duyarlılığı.
- Brent/petrol/doğal gaz ve metal emtia anahtar kelimelerine dayalı sınırlı
  sektör bağlantıları.
- Olay detayında deterministik etki bağlantıları tablosu.
- Haber Merkezi'nde yeni `Etki Bağlantıları` sekmesi.

## Güvenlik sınırları

- Motor olumlu/olumsuz fiyat yönü tahmini yapmaz.
- Teknik analiz skoru bu motora girmez ve bu motor tarafından değiştirilmez.
- AI kullanılmaz.
- Şirket kapsamındaki olayda hisse sembolü yoksa hisse uydurulmaz.
- Sektör kapsamındaki olayda sektör etiketi yoksa sektör uydurulmaz.
- Duyarlılık bağlantısı, şirket bazında kesin etki iddiası değildir.
- SQLite arşiv şeması değiştirilmez.
- Mevcut 0-100 haber önem formülü değiştirilmez.

## Sonraki katmanlara hazırlık

Bu yapı ileride Sektör Etki Haritası ve Portföy Etki Radarı için güvenli,
açıklanabilir ilişki tabanı sağlar. Portföy etkisi bu sprintte hesaplanmaz.
