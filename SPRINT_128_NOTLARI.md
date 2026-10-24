# Sprint-128 — Erken Radar Tarihsel Toplu Doğrulama

## Amaç
Sprint-127'de eklenen hareket yaşı / erken radar teşhisini çoklu tarihsel kesitlerde ölçmek.

## Ölçümler
- Sıra bantları: 1-10, 11-20, 21-30, 31+, izleme dışı
- Aşama bazlı sonuçlar
- Momentum bantları: <45, 45-54, 55-64, 65-74, 75+
- Başarı oranı (varsayılan ileri azami yükseliş >= %10)
- Ortalama / medyan ileri azami yükseliş
- Ortalama / medyan azami ters hareket
- Ham gözlem sayısı ve benzersiz hisse sayısı
- Aynı hissenin ardışık kesitlerde tekrar sayılmasını ayırmak için ilk görünme kayıtları
- Yakalanan Hareket Oranı:
  bir sıra bandına gelindiğinde toplam hareketin ne kadarının zaten gerçekleştiği

## Güvenlik
- Look-ahead yok: kesim tarihi özellikleri sadece özellik olarak kullanılır.
- İleri fiyatlar yalnız performans etiketi olarak değerlendirilir.
- Mevcut skor, PreBreakout eşiği, aday sıralaması ve üretim kararları değiştirilmez.
