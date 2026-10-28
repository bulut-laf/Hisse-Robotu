import json, tempfile, unittest
from pathlib import Path
from backend.app.funds.models import FundRecord, FundSource, FundType, VerificationStatus
from backend.app.funds.universe import FundUniverse, UniverseValidationError

def sample(isin="IE00BK5BQT80", name="Global Equity ETF", sources=()):
    return FundRecord(isin=isin,name=name,fund_type=FundType.UCITS_ETF,base_currency="USD",provider="Example Provider",verification_status=VerificationStatus.PARTIALLY_VERIFIED,sources=tuple(sources))

class FundModelTests(unittest.TestCase):
    def test_isin_normalized(self): self.assertEqual(sample("ie00bk5bqt80").isin,"IE00BK5BQT80")
    def test_rejects_bad_isin_shape(self):
        with self.assertRaises(ValueError): sample("BAD")
    def test_source_requires_http_url(self):
        with self.assertRaises(ValueError): FundSource("file:///tmp/evidence","provider")
    def test_cost_range(self):
        with self.assertRaises(ValueError): FundRecord(isin="IE00BK5BQT80",name="X",fund_type=FundType.UCITS_ETF,ongoing_charge_pct=101)
    def test_risk_range(self):
        with self.assertRaises(ValueError): FundRecord(isin="IE00BK5BQT80",name="X",fund_type=FundType.UCITS_ETF,risk_indicator=8)

class FundUniverseTests(unittest.TestCase):
    def test_deduplicates_and_preserves_multiple_sources(self):
        a=FundSource("https://provider.example/fund","provider"); b=FundSource("https://factsheet.example/fund","factsheet")
        u=FundUniverse.from_records([sample(sources=(a,)),sample(sources=(b,))])
        self.assertEqual(len(u.records),1); self.assertEqual({s.url for s in u.get("IE00BK5BQT80").sources},{a.url,b.url})
    def test_conflicting_name_requires_reconciliation(self):
        u=FundUniverse.from_records([sample(name="Name A")])
        with self.assertRaises(UniverseValidationError): u.upsert(sample(name="Name B"))
    def test_json_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"universe.json"; u=FundUniverse.from_records([sample(sources=(FundSource("https://provider.example/fund","provider"),))]); u.save(path)
            loaded=FundUniverse.load(path); self.assertEqual(loaded.get("IE00BK5BQT80").name,"Global Equity ETF"); self.assertEqual(len(loaded.get("IE00BK5BQT80").sources),1)
    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp: self.assertEqual(len(FundUniverse.load(Path(tmp)/"missing.json").records),0)
    def test_unsupported_schema_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"universe.json"; path.write_text(json.dumps({"schema_version":99,"records":[]}),encoding="utf-8")
            with self.assertRaises(UniverseValidationError): FundUniverse.load(path)
if __name__=="__main__": unittest.main()
