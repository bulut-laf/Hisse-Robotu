# Sprint-151 — Güvenilir Kaynak Sözlüğü ve Deterministik Haber/Olay Sınıflandırması

## Amaç

Manuel girilen haberlerde kaynak ve temel olay sınıflandırmasını AI kullanmadan,
açıklanabilir ve tekrar üretilebilir kurallarla desteklemek.

## Eklenenler

- `source_registry.py`
  - Birinci seviye kaynak beyaz listesi:
    - TCMB
    - TÜİK
    - KAP
    - Borsa İstanbul
    - SPK
    - Hazine ve Maliye Bakanlığı
    - Resmî Gazete
    - Şirket Yatırımcı İlişkileri (yalnız açık etiket eşleşmesi)
  - İkinci seviye kaynaklar:
    - Reuters
    - Bloomberg
  - Kaynak adı veya izin verilen resmî alan adı üzerinden deterministik çözümleme.
  - Benzer isim/substring ile otomatik güvenilir kaynak yükseltmesi yapılmaz.

- `classifier.py`
  - Sabit öncelikli anahtar kelime kurallarıyla olay türü önerisi.
  - Türkiye makro / küresel / BIST geneli / sektör / şirket kapsam önerisi.
  - Sınırlı ve açıklanabilir sektör etiketleme kuralları.
  - Her otomatik öneri için çalıştırılan kuralın metinsel gerekçesi.
  - Belirsizlikte zorla sınıflandırma yapılmaz.

- Haber Merkezi arayüzü
  - “Deterministik sınıflandırmayı önizle” akışı.
  - “Deterministik sınıflandırmayı kayıtta uygula” seçeneği.
  - Kullanıcının manuel seçimi fallback olarak korunur.
  - Mevcut olaya haber bağlanırken olay türü/kapsamı değiştirilmez; yalnız doğrulanmış
    kaynak seviyesi yeni haberin kaynak güvenilirliğine uygulanabilir.

## Değişmeyenler

- SQLite arşiv şeması
- Deterministik 0–100 önem formülü
- Olay/haber ilişki modeli
- Teknik analiz skoru
- AL/SAT karar motoru
- AI değerlendirme katmanı
- Otomatik internet/KAP/Reuters/Bloomberg veri çekme

## Güvenlik kararı

Kaynak güvenilirliği beyaz liste yaklaşımıyla yükseltilir. Kaynak adı bir güvenilir
kuruma benzediği için otomatik olarak resmî/güvenilir kabul edilmez. Belirsiz olay
metni `DIGER/OTHER` yönünde zorlanmaz; mevcut manuel seçim korunur.
