# Sprint-35 Rev2 — Live Session Persistence Hotfix

## Sorun

Tarihsel yeniden oynatma sonucu ekranda görünürken **Güncel seans verisini getir** düğmesine basılması Streamlit betiğini yeniden çalıştırıyordu. Yeniden oynatma sonucu yalnızca başlat düğmesinin aynı çalışmasında üretildiği için yeni çalışmada sonuç ekranı kayboluyor, canlı seans düğmesinin olayı işlenemiyordu.

## Düzeltme

- Son başarılı walk-forward sonucu `st.session_state` içinde korunur.
- Sonuç, sol menüdeki mevcut ayarların imzasıyla birlikte saklanır.
- Güncel seans düğmesinin başlattığı yeniden çalışmada aynı ayarlara ait sonuç tekrar gösterilir.
- Sol menü ayarları değişirse eski sonuç gösterilmez.
- Normal momentum taramasına geçildiğinde kayıtlı walk-forward sonucu temizlenir.

## Beklenen davranış

1. Tarihsel testi çalıştırın.
2. Aday ayrıntısında **Güncel seans verisini getir** düğmesine basın.
3. Tarihsel sonuç kaybolmadan canlı seans kartları yüklenir.
