# Sprint-164 — Haber Arşivi Gelişmiş Filtreleme ve Geçmişe Erişim

Amaç: Haber Merkezi arşivini tarihsel inceleme ve olay/hisse/sektör bazlı
araştırma için hızlı ve güvenli biçimde filtrelenebilir hale getirmek.

## Filtreler

- başlangıç / bitiş tarihi
- kaynak
- hisse
- sektör
- olay türü
- piyasa kapsamı
- asgari mevcut önem skoru
- başlık / haber metni / olay başlığında serbest metin arama
- yalnız güvenilir kaynaklar
- gösterilecek sonuç limiti

## Güvenlik ve mimari sınırlar

- Arşiv en fazla 10.000 haber / 5.000 olay okuyabilir.
- Hisse, sektör, olay türü, kapsam ve önem yalnız bağlı MarketEvent kaydından gelir.
- Haber metninden hisse/sektör/önem tahmin edilmez.
- Bağlı olayı bulunamayan haberler filtresiz görünümde korunur.
- KAP doğrulaması güvenilir kaynak sözlüğünden gelir.
- Yeni birleşik/gizli skor yok.
- Fiyat yönü yok.
- AL/SAT yok.
- Teknik skor değişikliği yok.
- AI yorumu yok.
- Otomatik internet/KAP entegrasyonu yok.
