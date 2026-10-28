# Hisse Robotu — Fon Araştırma Sprint 3

## Amaç
Güncel ve kaynaklı fon portföyü verileri üzerinden fonlar arası örtüşmeyi ve varlık/ülke/sektör/para birimi dağılımını ölçmek.

## İçerik
- CSV holdings importer; zorunlu alanlar `fund_isin`, `asset_id`, `weight_pct`.
- İki fon arasındaki örtüşme, ortak varlıklarda iki fondaki ağırlıkların minimumlarının toplamı olarak hesaplanır.
- Sektör, ülke, para birimi ve varlık türü dağılımları.
- Sınıflandırılmayan ağırlık ayrıca raporlanır.
- Holdings verisi yoksa örtüşme `0` değil `None` olarak işaretlenir.
- Kaynak URL'si satır bazında saklanabilir; veri tarihi için mevcut şemada ayrı alan bulunmadığından CSV'nin kendisi tarihli bir kanıt dosyası olarak arşivlenmelidir.

## Önemli sınırlama
Bu modül otomatik olarak web'den güncel holdings indirmez ve portföy tavsiyesi üretmez. Önce sağlayıcı/fon factsheet verileri temin edilip doğrulanmalıdır. Farklı tarihlerden holdings karşılaştırması anlamlı olmayabileceğinden veri tarihleri dışarıda kontrol edilmelidir.

## Hedef test
`.\.venv\Scripts\python.exe -m pytest backend\tests\test_fund_research_sprint3.py -q`

## Tam regresyon
Hedef testler geçtikten sonra `.\.venv\Scripts\python.exe -m pytest` çalıştırılmalıdır.
