# Sprint-149 — Haber Merkezi Temel Veri Modeli ve Manuel Haber Arşivi

## Kapsam

Sprint-149, Piyasa Haber, Olay ve Etki Merkezi'nin güvenli temelini kurar.

Eklenenler:

- Haber kaydı ve piyasa olayı için ayrı veri modelleri.
- Kontrollü olay türü, piyasa kapsamı ve kaynak seviyesi sınıfları.
- Deterministik 0–100 önem skoru:
  - Kaynak güvenilirliği: 0–30
  - Piyasa kapsamı: 0–25
  - Olay önemi: 0–30
  - Olay-yayın zaman hassasiyeti: 0–15
- SQLite tabanlı manuel haber/olay arşivi.
- Varsayılan kullanıcı verisi konumu:
  `~/.hisse_robotu/news_center/news_center.sqlite3`
- SHA-256 tabanlı birebir haber tekrar engelleme.
- "Tek olay + çok kaynak" yapısı.
- Mevcut bir olaya ikinci/üçüncü haber kaynağını manuel bağlama.
- Hisse ve sektör etiketlerinin kalıcı saklanması.
- Streamlit içinde "Piyasa Haber, Olay ve Etki Merkezi" ekranı.

## Bilinçli olarak eklenmeyenler

- Otomatik internet/RSS/KAP/Reuters/Bloomberg veri çekme
- Web scraping
- AI özetleme veya AI etki yorumu
- Otomatik semantik olay eşleştirme
- Portföy Etki Radarı
- Sektör Etki Haritası
- Ekonomik Takvim otomasyonu
- Teknik skor veya işlem karar motoru entegrasyonu

## Güvenlik ilkesi

Haber Merkezi teknik analiz skorunu veya AL/SAT kararını doğrudan değiştirmez.
Sprint-149 bağımsız bir karar-destek veri katmanıdır.

## Doğrulama

Kurulum betiği sırasıyla:

1. Etkilenecek mevcut dosyaları yedekler.
2. Sprint-149 dosyalarını kurar.
3. Dashboard bağlantısını kontrollü ve doğrulanabilir üç ankordan ekler.
4. Hedef testleri çalıştırır.
5. Tam `backend/tests` regresyonunu çalıştırır.
6. Herhangi bir aşama başarısızsa Sprint-149 değişikliklerini otomatik geri alır.
