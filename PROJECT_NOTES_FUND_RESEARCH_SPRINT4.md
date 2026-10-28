# Hisse Robotu — Fon Araştırma Sprint 4

## Amaç
Fon ağırlıklarını doğrulamak, yatırım tutarlarını hesaplamak ve kullanıcı tarafından sağlanan senaryo getirileriyle portföy stres testi yapmak.

## İçerik
- Fon ağırlıklarının %100'e toplam kontrolü.
- Aynı ISIN'in birden fazla kez yazılmasını engelleme.
- Yatırım tutarının ağırlıklara göre fonlara dağıtımı.
- Fon bazlı senaryo getirilerini ağırlıklı toplayarak portföy senaryo getirisi hesaplama.
- Senaryo verisi eksikse sonuç üretmeyip `comparable=False` ve eksik fon listesini döndürme.

## Sınırlamalar
- Bu sprint otomatik optimum portföy aramaz; kısıtlı, açıklanabilir hesaplama altyapısı sağlar.
- Senaryo getirileri kullanıcı/analist tarafından verilmelidir; piyasa tahmini değildir.
- Vergi, alım-satım maliyeti, kur etkisi, fon alım limitleri ve minimum işlem tutarları kapsam dışıdır.
- Sonuçlar yatırım tavsiyesi değildir ve %10–15 maksimum düşüş sınırını garanti etmez.

## Hedef test
`.\.venv\Scripts\python.exe -m pytest backend\tests\test_fund_research_sprint4.py -q`

## Tam regresyon
Hedef testler geçtikten sonra `.\.venv\Scripts\python.exe -m pytest` çalıştırılmalıdır.
