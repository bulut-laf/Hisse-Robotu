import numpy as np
import pandas as pd

class FundRanker:
    @staticmethod
    def calculate_metrics(history_rows):
        if not history_rows or len(history_rows) < 2:
            return None
        df = pd.DataFrame(history_rows)
        df['tarih'] = pd.to_datetime(df['tarih'])
        df = df.sort_values('tarih').reset_index(drop=True)
        df['gunluk_getiri'] = df['fiyat'].pct_change()
        toplam_getiri = (df['fiyat'].iloc[-1] - df['fiyat'].iloc[0]) / df['fiyat'].iloc[0]
        volatilite = df['gunluk_getiri'].std() * np.sqrt(252)
        gun_sayisi = len(df)
        if gun_sayisi > 5 and volatilite > 0:
            yillik_getiri = (1 + toplam_getiri) ** (252 / gun_sayisi) - 1
            sharpe_orani = yillik_getiri / volatilite
        else:
            sharpe_orani = 0.0
        return {
            "toplam_getiri_yuzde": round(toplam_getiri * 100, 2),
            "volatilite": round(volatilite * 100, 2),
            "sharpe_orani": round(sharpe_orani, 2),
            "veri_nokta_sayisi": gun_sayisi
        }

    @classmethod
    def rank_funds(cls, fund_data_dict):
        results = []
        for code, rows in fund_data_dict.items():
            metrics = cls.calculate_metrics(rows)
            if metrics:
                metrics["fund_code"] = code
                results.append(metrics)
        results.sort(key=lambda x: x["sharpe_orani"], reverse=True)
        return results