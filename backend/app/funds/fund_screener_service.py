import json
import os
from app.funds.fund_ranker import FundRanker
from app.funds.fund_adapter import FundAdapter

class FundScreenerService:
    def __init__(self, watchlist_path="backend/data/fund_watchlist.json"):
        self.watchlist_path = watchlist_path

    def load_watchlist(self):
        if not os.path.exists(self.watchlist_path):
            return {"categories": {}}
        with open(self.watchlist_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_ranked_funds_for_category(self, category_name, mock_data_provider=None, months: int = 6):
        """
        Belirtilen kategori için fonları izleme listesinden okur, 
        adaptör aracılığıyla geçmiş verilerini çeker ve Sharpe oranına göre sıralar.
        """
        watchlist = self.load_watchlist()
        categories = watchlist.get("categories", {})
        funds = categories.get(category_name, [])
        
        fund_dict = {}
        for fund in funds:
            code = fund["code"]
            if mock_data_provider:
                rows = mock_data_provider(code)
            else:
                rows = FundAdapter.fetch_fund_history(code, months=months)
                
            if rows:
                fund_dict[code] = rows
                    
        return FundRanker.rank_funds(fund_dict)