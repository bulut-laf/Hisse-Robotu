# Veri Tazeliği Rev2 — Seans kapanışı sonrası bugünkü barı koruma

Doğrulanan ikinci sorun:
- Toplu yfinance sorgusu artık `end=2026-08-01` kullanıyordu.
- Buna rağmen `fiyat_verisini_duzelt(..., yalnizca_tamamlanmis_gunler=True)`
  bugünün satırını saatten bağımsız olarak siliyordu.
- Bu nedenle 31 Temmuz kapanış barı 20:00 sonrasında bile analizden çıkarılıyor
  ve son tarih 30 Temmuz görünüyordu.

Düzeltme:
- Bugünkü günlük bar İstanbul saati 18:30 öncesinde çıkarılır.
- İstanbul saati 18:30 ve sonrasında günlük kapanış barı korunur.
- Rev1 toplu `end` tarihi düzeltmesi aynen korunmuştur.
- Veri tazeliği kilidi kaldırılmamış veya gevşetilmemiştir.
