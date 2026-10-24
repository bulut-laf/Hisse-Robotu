# Hisse Robotu — Sprint-34

## Hedef

BIST hisselerini tek tek yazıp analiz etmek yerine, seçilen hisse evrenini topluca taramak ve teknik araştırma adaylarını sıralamak.

## Yeni analiz modu

Streamlit sol menüsüne **BIST Toplu Tarama** seçeneği eklenmiştir.

Desteklenen evrenler:

- Kayıtlı İzleme Listesi
- BIST 30
- BIST 100
- BIST 500
- BIST Tüm
- Özel Liste

## Tarama profilleri

- **Gevşek:** Geniş ön eleme.
- **Dengeli:** Skor, hacim, risk/getiri ve pozitif/nötr teknik görünüm.
- **Sıkı:** Güçlü, hacim destekli, risk filtresini geçen pozitif görünüm.

## Sonuç tablosu

Her aday için şu alanlar gösterilir:

- Teknik skor
- Durum
- Teknik görünüm
- Son kapanış
- Giriş
- Stop
- Hedef
- Risk/Getiri
- Hacim oranı
- RSI14
- ATR yüzdesi
- Risk notu
- Analiz tarihi

Sonuçlar kesin alım tavsiyesi değildir. Adaylar, ayrıntılı **Güncel Teknik Analiz** ekranında doğrulanmalıdır.

## Veri evreni

BIST 30/100/500/Tüm bileşenleri Borsa İstanbul'un resmi endeks bileşenleri CSV kaynağından alınır. Güncel indirme başarısız olursa yerel önbellek veya paketlenmiş resmi anlık görüntü kullanılır.

Paketlenmiş anlık görüntü tarihi: **27/07/2026**

## Performans yaklaşımı

Geniş evrenlerde her sembol için ayrı indirme yapmak yerine, fiyat verileri parçalar hâlinde toplu indirilir. Bir semboldeki veri hatası taramanın kalanını durdurmaz.

## Doğrulama

- 555/555 otomatik test başarılı
- 16/16 sistem kontrolü başarılı
- 159 Python dosyası sözdizimi kontrolünden geçti

## Kurulum sonrası kontrol

1. Programı başlatın.
2. Sol menüden **BIST Toplu Tarama** seçin.
3. İlk doğrulama için **Kayıtlı İzleme Listesi + Dengeli** profilini çalıştırın.
4. Sonra **BIST 30 + Dengeli** profilini deneyin.
5. Sonuç doğrulanınca BIST 100/500/Tüm evrenlerine geçin.
