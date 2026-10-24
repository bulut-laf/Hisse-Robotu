# VBTS Hızlı Hazırlama

Bu betik yalnızca resmî KAP bildirimlerinden doğrulanan VBTS kayıtlarını
`data/vbts/vbts_guncel.csv` dosyasına eklemek için kullanılır.

## Yeni kayıt ekleme

Etkileşimli kullanım:

```powershell
.\VBTS-Hizli-Hazirla.ps1 -Islem Ekle
```

Tek komutla alanları verme:

```powershell
.\VBTS-Hizli-Hazirla.ps1 -Islem Ekle `
  -Symbol "HISSE" `
  -MeasureType "KAP bildirimindeki tedbir türü" `
  -StartDate "YYYY-MM-DD" `
  -EndDate "YYYY-MM-DD" `
  -SourceReference "Resmî KAP bildirim referansı"
```

## Kayıtları listeleme

```powershell
.\VBTS-Hizli-Hazirla.ps1 -Islem Listele
```

## Dosyayı doğrulama ve kaynağı etkinleştirme

```powershell
.\VBTS-Hizli-Hazirla.ps1 -Islem Dogrula
```

Boş dosya, eksik alan, geçersiz tarih veya yinelenen kayıt kabul edilmez.
Bu araç kişisel analiz amaçlıdır, yatırım tavsiyesi değildir.
