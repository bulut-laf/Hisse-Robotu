# Sprint-56 Rev1 — KAP Bilanço Entegrasyon Altyapısı

Eklenenler:
- Yapılandırılmış KAP finansal kayıt istemcisi
- KAP alan adlarını standart bilanço modeline eşleme
- Şirket kodu ve dönem doğrulaması
- Eksik/uyumsuz kayıtların reddedilmesi
- Kaynak, yayın tarihi ve veri kimliği
- Aynı dönem tekrarını önleyen JSON depo
- Güncel veri için analiz ve saklama zinciri
- Eski veya geçersiz veri için güvenlik kilidi

Önemli:
- Bu paket resmi KAP uç noktasını tahmin etmez.
- Canlı bağlantı, resmi/kurumsal sözleşmesi doğrulanmış bir fetcher
  sağlandığında KapFundamentalClient üzerinden etkinleşir.
- Manuel CSV/JSON yolu korunur.
- Teknik taramaya temel analiz filtresi bağlanmaz.
