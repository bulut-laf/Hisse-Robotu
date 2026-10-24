# Manuel VBTS CSV Kullanımı

Bu özellik, resmî KAP bildirimlerinden elle doğrulanmış VBTS tedbirlerini
Hisse Robotu toplu taramasına güvenli biçimde aktarmak için hazırlanmıştır.

## Güvenlik ilkesi

- Yalnızca resmî KAP bildirimleri kullanılmalıdır.
- Tahmin, sosyal medya paylaşımı veya aracı kurum yorumu VBTS kaydı sayılmaz.
- Bu araç kişisel analiz amaçlıdır, yatırım tavsiyesi değildir.
- Eski, eksik veya boş dosya toplu tarama kilidini açmaz.

## Dosyalar

- `data/vbts/vbts_sablon.csv`: yalnızca başlık içeren güvenli şablondur.
- `data/vbts/vbts_guncel.csv`: doğrulanmış aktif kayıtların bulunduğu çalışma dosyasıdır.
- `VBTS-Manuel-Kaynak-Ayarla.ps1`: ortam değişkenlerini güvenli biçimde tanımlar.

## CSV sütunları

```text
symbol,measure_type,start_date,end_date,source_reference
```

Alan açıklamaları:

- `symbol`: BIST işlem kodu. Örnek biçim: `THYAO` veya `THYAO.IS`
- `measure_type`: KAP bildirimindeki tedbir türü
- `start_date`: başlangıç tarihi, `YYYY-MM-DD`
- `end_date`: bitiş tarihi, `YYYY-MM-DD`
- `source_reference`: resmî KAP bildirim numarası veya doğrulanabilir referansı

## Kurulum

1. `data/vbts/vbts_sablon.csv` dosyasını kopyalayın.
2. Kopyanın adını `vbts_guncel.csv` yapın.
3. Resmî KAP bildirimlerindeki aktif tedbirleri satır satır girin.
4. PowerShell'de proje kökünde şu komutu çalıştırın:

```powershell
.\VBTS-Manuel-Kaynak-Ayarla.ps1
```

5. Hisse Robotu'nu kapatıp yeniden açın.
6. Toplu Tarama ekranında `Manuel VBTS koruması aktif.` mesajını doğrulayın.

## Önemli

Yalnızca başlık satırı bulunan boş `vbts_guncel.csv` reddedilir. Güncel aktif
tedbir bulunmadığı günlerde de sıfır kayıtlı dosya güvenlik nedeniyle otomatik
olarak kabul edilmez; resmî doğrulama süreci ayrıca kayıt altına alınmadan
tarama kilidi açılmaz.
