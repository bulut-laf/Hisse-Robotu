# Sprint-162 — Gün Sonu Haber ve Olay Özeti

Amaç: Haber Merkezi'nde gün içinde oluşan karar destek verilerini tek bir
kapanış görünümünde birleştirmek.

## Kapsam

- seçilen günün toplam piyasa olayı
- önem >=80 olay sayısı
- birincil kaynaklı olay sayısı
- çok kaynaklı olay sayısı
- o gün yayımlanan haber sayısı
- doğrulanmış KAP bildirim sayısı
- hisse bazlı olay ve benzersiz hisse sayısı
- deterministik sektör etki kapsamı
- açık Gölge Portföy'e temas eden hisseler
- ekonomik takvim toplam / yüksek-kritik / açıklanan / sonuç beklenen
- mevcut 0-100 önem skoruna göre günün başlıca gelişmeleri
- en yoğun ilk 5 sektör

## Tarihsel güvenlik

Geçmiş bir gün seçildiğinde, olay değerlendirmelerinde yalnız o günün
23:59:59'una kadar yayımlanmış haberler kullanılır. Daha sonra yayımlanan haberler
geçmiş günün kaynak/etki görünümünü geriye dönük değiştirmez.

## Mimari sınırlar

- Yeni birleşik/gizli skor üretilmez.
- Fiyat yönü çıkarılmaz.
- AL/SAT kararı üretilmez.
- Teknik skor değiştirilmez.
- AI yorumu kullanılmaz.
- Otomatik internet/KAP entegrasyonu eklenmez.
