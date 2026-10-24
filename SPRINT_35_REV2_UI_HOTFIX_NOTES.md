# Sprint-35 Rev2 — Tarih Alanı Arayüz Düzeltmesi

## Düzeltilen sorun

Momentum Keşif ekranında “Tarihsel yeniden oynatma (walk-forward)” kutusu işaretli görünmesine rağmen “Kesim tarihi” alanı pasif kalıyordu.

## Kök neden

Onay kutusu ve tarih alanı bir Streamlit formunun içindeydi. Form içindeki değişiklikler form gönderilmeden yeniden çalıştırılmadığı için tarih alanının `disabled` durumu anında güncellenmiyordu.

## Çözüm

Momentum Keşif kontrolleri form dışına taşındı ve başlatma işlemi normal Streamlit düğmesine bağlandı. Artık:

- Walk-forward kutusu işaretlenince tarih alanı hemen aktifleşir.
- Keşif evreni değişince ilgili alanlar hemen güncellenir.
- Başlat düğmesinin metni anında “Tarihsel testi başlat” olarak değişir.

Bir regresyon testi eklenmiştir.
