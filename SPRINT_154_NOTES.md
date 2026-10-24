# Sprint-154 — Portföy Etki Radarı

## Amaç

Haber Merkezi'ndeki deterministik olay/etki bağlantılarını açık Gölge Portföy
pozisyonlarıyla kesiştirerek hangi olayın hangi portföy hissesine hangi açık
ilişki üzerinden temas ettiğini göstermek.

## Eklenenler

- `portfolio_impact.py` bağımsız radar motoru.
- Açık portföy üyesi için sembol ve sektör normalizasyonu.
- Aynı olay-hisse çifti için tek kayıt.
- Eşleşme önceliği:
  1. `DIRECT_SYMBOL`
  2. `SECTOR`
  3. `MARKET`
- Portföy kapsama özeti.
- Olay–portföy kesişim tablosu.
- Açık pozisyon, olayla kesişen pozisyon, doğrudan hisse eşleşmesi ve önem ≥80
  olay sayaçları.
- Haber Merkezi içinde `Portföy Etki Radarı` sekmesi.

## Güvenlik sınırları

- Yalnız açık Gölge Portföy pozisyonları kullanılır.
- Fiyat yönü tahmini yapılmaz.
- AL/SAT kararı üretilmez.
- Teknik analiz skoru değiştirilmez.
- Bir olay aynı hisseye piyasa, sektör ve hisse yollarından temas ederse sayılar
  şişirilmez; en güçlü deterministik bağlantı tek satırda korunur.
- Hisse veya sektör uydurulmaz; Sprint-153 etki bağlantıları yeniden kullanılır.

## Değişmeyenler

- SQLite arşiv şeması
- Deterministik 0–100 önem formülü
- Sprint-151 kaynak/sınıflandırma kuralları
- Sprint-152 olay gruplama motoru
- Sprint-153 etki motorunun yönsüz bağlantı ilkesi
- AI katmanı
- Teknik karar motoru
