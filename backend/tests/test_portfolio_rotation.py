import pytest
from backend.app.funds.portfolio_rotation_engine import generate_rotation_plan

def test_generate_rotation_plan_basic():
    # Mevcut portföyde MAC ve IIH var. Hedef ise IIH'yi tutup NNF'ye geçmek (Rotasyon)
    current = {"MAC": 50000.0, "IIH": 50000.0}
    target = ["IIH", "NNF"] # Toplam 100k, iki fona 50'şer K dağıtılmalı
    
    df = generate_rotation_plan(current, target, total_capital=100000.0)
    
    assert not df.empty
    
    # MAC artık hedefte yok, tamamen SATILMALI
    mac_row = df[df["Fon Kodu"] == "MAC"].iloc[0]
    assert mac_row["Aksiyon"] == "SAT"
    assert mac_row["Fark ()"] == -50000.0
    
    # IIH hem mevcut hem hedefte aynı oranda, TUTULMALI
    iih_row = df[df["Fon Kodu"] == "IIH"].iloc[0]
    assert iih_row["Aksiyon"] == "TUT"
    
    # NNF yeni giriyor, ALINMALI
    nnf_row = df[df["Fon Kodu"] == "NNF"].iloc[0]
    assert nnf_row["Aksiyon"] == "AL"
    assert nnf_row["Fark ()"] == 50000.0