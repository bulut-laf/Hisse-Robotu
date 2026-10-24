# Sprint-163 — Son Dakika Haber Akışı

Amaç: Haber Merkezi arşivindeki en yeni yayınları kronolojik ve hızlı okunabilir
bir Son Dakika görünümünde sunmak.

## Temel davranış

- Bir haber kaydı = bir akış satırı.
- Aynı olaya farklı zamanlarda gelen farklı kaynaklar ayrı satırlarda görünür.
- Exact duplicate engeli mevcut arşiv katmanında korunur.
- Akış yayın zamanına göre en yeniden eskiye sıralanır.
- Gelecek zaman damgalı haberler gösterilmez.
- 1 saat / 3 saat / 6 saat / 24 saat / 3 gün / tüm arşiv filtreleri vardır.
- Mevcut olay önem skoru yalnız gösterilir; yeni skor üretilmez.
- Kaynak, hisse, önem ve yalnız Gölge Portföy filtreleri vardır.
- Varsayılan görünüm yalnız güvenilir kaynak sözlüğünde doğrulanmış kaynakları
  gösterir; kullanıcı isterse tüm arşivi görebilir.
- KAP işareti yalnız kaynak sözlüğünde KAP olarak doğrulanan kayıtlarda görünür.
- Hisse/sektör yalnız bağlı MarketEvent kaydından gelir; haber metninden tahmin
  edilmez.
- Bağlı olay bulunamayan haber için önem/hisse/sektör uydurulmaz.

## Mimari sınırlar

- Otomatik internet/KAP entegrasyonu yok.
- Scraping yok.
- Yeni birleşik/gizli skor yok.
- Fiyat yönü yok.
- AL/SAT yok.
- Teknik skor değişikliği yok.
- AI yorumu yok.
