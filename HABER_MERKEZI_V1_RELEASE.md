# Hisse Robotu — Haber Merkezi V1.0.0 Kararlı Sürüm

Haber Merkezi V1.0.0, Sprint-149–178 geliştirme zincirinin kararlı kapanışıdır.

## V1 kapsamı

- Manuel haber arşivi ve gelişmiş arşiv filtreleri
- Güvenilir kaynak sözlüğü
- Olay gruplama/birleştirme
- Deterministik önem ve etki katmanları
- Sektör Etki Haritası ve Portföy Etki Radarı
- Son Dakika, Bugünün Önemli Gelişmeleri, Ekonomik Takvim
- KAP Akışı, Hisse Haberleri, Gün Sonu Özeti
- Günlük Haber Merkezi Operasyon ekranı
- Kaynak operasyon audit geçmişi
- 49/49 yapısal resmî adapter sağlık kontrolü

## Kontrollü resmî kaynaklar

1. KAP
2. TCMB
3. TÜİK
4. SPK
5. Hazine ve Maliye Bakanlığı
6. Borsa İstanbul
7. Resmî Gazete

Ağ varsayılan kapalıdır. Her fetch tek resmî URL ve açık kullanıcı onayı ister.
Dry-run ve ayrıca açık arşivleme onayı korunur. Timeout 1–30 saniye,
varsayılan 10 saniye; yanıt sınırı 2 MB'tır.

## V1 güvenlik sınırları

- otomatik polling yapmaz
- toplu scraping yapmaz
- arka plan kaynak taraması yapmaz
- fiyat yönü üretmez
- AL/SAT üretmez
- haber nedeniyle teknik analiz skorunu doğrudan değiştirmez
- ağsız sağlık kontrolünü canlı erişilebilirlik göstergesi olarak kullanmaz
- audit günlüğünde haber gövdesi veya HTML yanıtı saklamaz

## V1 dışında bırakılanlar

- genel Şirket Yatırımcı İlişkileri adapteri
- otomatik Reuters/Bloomberg entegrasyonu
- otomatik PDF/Excel ek takibi
- sürekli internet taraması ve background poller
- haberden otomatik işlem kararı

## Sprint-178 kapanış doğrulaması

Kurulum sırasıyla Python compile, ağsız V1 sistem kontrolü, Streamlit API
uyumluluğu, Sprint-178 hedef testleri ve tam backend regresyonunu çalıştırır.
Tam regresyon kullanıcı bilgisayarında başarılı olmadan V1 kararlı kabul edilmez.
