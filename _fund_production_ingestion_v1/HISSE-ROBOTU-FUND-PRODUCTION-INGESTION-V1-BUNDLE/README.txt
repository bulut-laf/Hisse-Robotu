HISSE ROBOTU — FUND PRODUCTION INGESTION V1

Bu bundle exact-source paketinden uretilmistir.

Uygulanan davranis:
- Resmi KAP /tr/Bildirim/<id> URL'si yalniz acik kullanici butonu ile cekilir.
- Bildirimin aylik Portfoy Dagilim Raporu oldugu dogrulanir.
- Tek ve dogrulanmis KAP PDF eki secilir; birden fazla PDF varsa fail-closed.
- PDF metni pypdf ile okunur.
- 3- FON PORTFOY DEGERI TABLOSU > A) HISSE SENETLERI bolumu ayrisir.
- Sembol, nominal/adet, rayic deger ve portfoy yuzdesi mevcut FundPortfolioSnapshot'a map edilir.
- Portfoy tarihi KAP Yil + Periyot (Aylik) bilgisinden ay sonu olarak uretilir.
- Yayin tarihi KAP Gonderim Tarihi'nden gelir.
- Provider KAP; mevcut canonical fund kimligi (fund:tefas:<kod>) korunur.
- Mevcut append-only portfolio_snapshots.json store yeniden kullanilir.
- Tekrar ingestion idempotent; farkli icerik ayni fon/tarih/provider kimliginde conflict verir.
- Otomatik KAP tarama/polling yoktur.
- AL/SAT ve canonical ranking mutasyonu yoktur.

Calistirma:
PowerShell'de bu klasordeki APPLY-HISSE-ROBOTU-FUND-PRODUCTION-INGESTION-V1.ps1 dosyasini calistirin.

Basarili sonraki adim:
LIVE_KAP_PORTFOLIO_SMOKE
