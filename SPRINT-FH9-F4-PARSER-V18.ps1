param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)
$ErrorActionPreference = 'Stop'
$py = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $py)) { throw "PROJECT_PYTHON_NOT_FOUND: $py" }
$disc = Join-Path $ProjectRoot '_discovery\erste_hungary'
New-Item -ItemType Directory -Force -Path $disc | Out-Null
$scriptPath = Join-Path $disc 'fh9_f4_parser_v18.py'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$source = @'
from __future__ import annotations
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from decimal import Decimal, InvalidOperation
from pathlib import Path
from datetime import date
import json, re, sys, time

ROOT = Path(r"D:\Projects\Hisse-Robotu")
DISC = ROOT / "_discovery" / "erste_hungary"
OUT = DISC / "fh9_f4_target_funds_v18.json"
ISINS = [
    "AT0000627476", "AT0000A00G88", "AT0000A00GA2", "AT0000A00G96",
    "AT0000A00GC8", "AT0000A00GE4", "AT0000A00GF1",
]

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.tables=[]; self.table_depth=0
        self.in_row=False; self.in_cell=False; self.row=[]; self.buf=[]; self.rows=[]
    def handle_starttag(self, tag, attrs):
        tag=tag.lower()
        if tag=='table':
            self.table_depth += 1
            if self.table_depth == 1: self.rows=[]
        elif self.table_depth and tag=='tr': self.in_row=True; self.row=[]
        elif self.in_row and tag in ('td','th'): self.in_cell=True; self.buf=[]
    def handle_data(self, data):
        if self.in_cell: self.buf.append(data)
    def handle_endtag(self, tag):
        tag=tag.lower()
        if self.in_cell and tag in ('td','th'):
            self.row.append(re.sub(r'\s+',' ',''.join(self.buf)).strip()); self.in_cell=False; self.buf=[]
        elif self.in_row and tag=='tr':
            if self.row: self.rows.append(self.row)
            self.in_row=False; self.row=[]
        elif tag=='table' and self.table_depth:
            self.table_depth-=1
            if self.table_depth==0: self.tables.append(self.rows)

def norm_header(x):
    x=str(x or '').lower().replace('\xa0',' ')
    return re.sub(r'\s+',' ',x).strip()

def parse_date(raw):
    # BAMOSZ uses Hungarian dates such as "2026. 10. 22."; normalize spaces first.
    s=re.sub(r'\s+','',str(raw or '')).strip().rstrip('.')
    m=re.fullmatch(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})',s)
    if not m: return None
    try: return date(int(m.group(1)),int(m.group(2)),int(m.group(3))).isoformat()
    except ValueError: return None

def parse_decimal(raw):
    s=str(raw or '').replace('\xa0','').replace('\u202f','').replace(' ','').strip()
    if not s or s in {'-','—','–'}: return None
    # Hungarian thousands separator is dot, decimal separator comma.
    if ',' in s: s=s.replace('.','').replace(',','.')
    else:
        # preserve ordinary decimal point; remove spaces already handled
        pass
    s=re.sub(r'[^0-9+\-.]','',s)
    try: return Decimal(s)
    except (InvalidOperation, ValueError): return None

def parse_page(html):
    parser=Tables(); parser.feed(html)
    candidates=[]
    for rows in parser.tables:
        for i,row in enumerate(rows):
            h=[norm_header(c) for c in row]
            def idx(pred):
                return next((j for j,v in enumerate(h) if pred(v)),None)
            dc=idx(lambda x:'dátum' in x or x=='date')
            pc=idx(lambda x:'árfolyam' in x or 'unit price' in x)
            nc=idx(lambda x:('nettó' in x and 'eszközérték' in x) or ('net' in x and 'asset' in x))
            tc=idx(lambda x:('forgalom' in x and ('bef.' in x or 'befjegy' in x)) or 'daily turnover' in x)
            if None in (dc,pc,nc,tc): continue
            records=[]
            for r in rows[i+1:]:
                if max(dc,pc,nc,tc)>=len(r): continue
                d=parse_date(r[dc]); p=parse_decimal(r[pc]); nav=parse_decimal(r[nc]); turnover=parse_decimal(r[tc])
                if d and p is not None and nav is not None and turnover is not None and p>0 and nav>0:
                    records.append({'date':d,'unit_price':str(p),'net_asset_value':str(nav),'daily_turnover':str(turnover)})
            if records:
                candidates.extend(records)
    # Deduplicate same-date rows; retain last occurrence and sort chronologically.
    by_date={r['date']:r for r in candidates}
    records=[by_date[k] for k in sorted(by_date)]
    if len(records)<2:
        return {'status':'INSUFFICIENT_VALID_DAILY_ROWS','valid_row_count':len(records),'records':records}
    prev, latest=records[-2],records[-1]
    prev_nav=Decimal(prev['net_asset_value']); latest_nav=Decimal(latest['net_asset_value'])
    turnover=Decimal(latest['daily_turnover'])
    # Source-backed fields only. Fund size is not derived from unit NAV changes.
    # Turnover / previous NAV is a turnover ratio, not asserted as net flow.
    turnover_ratio=(turnover/prev_nav) if prev_nav>0 else None
    return {'status':'SOURCE_ROWS_PARSED','valid_row_count':len(records),'previous':prev,'latest':latest,
            'daily_turnover_ratio':str(turnover_ratio) if turnover_ratio is not None else None,
            'net_flow_ratio':None,'fund_size_change':None,
            'f4_state':'UNAVAILABLE','reason':'BAMOSZ_DAILY_TURNOVER_IS_NOT_CONFIRMED_NET_FLOW_OR_AUM_CHANGE'}

def main():
    out=[]
    for i,isin in enumerate(ISINS):
        url='https://www.bamosz.hu/alapoldal?isin='+isin
        rec={'isin':isin,'url':url,'source':'BAMOSZ','semantic_proxy':False}
        try:
            req=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; FH9-F4-audit/18)','Accept-Language':'hu-HU,hu;q=0.9,en;q=0.8'})
            with urlopen(req,timeout=35) as resp:
                html=resp.read().decode('utf-8','replace'); rec['http_status']=resp.status
            rec.update(parse_page(html))
        except Exception as e:
            rec.update({'status':'FETCH_ERROR','error':type(e).__name__+': '+str(e)[:240]})
        out.append(rec)
        print(f"{isin} {rec.get('status')} rows={rec.get('valid_row_count',0)}")
        if i<len(ISINS)-1: time.sleep(0.35)
    payload={'version':'FH9-F4-PARSER-V18','fund_count':len(out),'parsed_count':sum(x.get('status')=='SOURCE_ROWS_PARSED' for x in out),
             'f4_positive_or_caution_count':0,'production_mutation':False,'trade_authority':'NONE','forced_fill':False,
             'semantic_proxy':False,'results':out}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print('REPORT='+str(OUT)); print('PRODUCTION_MUTATION=NO'); print('TRADE_AUTHORITY=NONE'); print('STATUS=REPORT_WRITTEN')
if __name__=='__main__': main()
'@
# Root path in embedded code is aligned with the supplied parameter.
$source = $source.Replace('ROOT = Path(r"D:\Projects\Hisse-Robotu")', ('ROOT = Path(r"' + $ProjectRoot.Replace("'","''") + '")'))
[System.IO.File]::WriteAllText($scriptPath, $source, $utf8)
Write-Host '=== FH9 F4 PARSER V18: TARGET VALIDATION ==='
& $py -c "from datetime import date; import runpy; p=runpy.run_path(r'$scriptPath'); assert p['parse_date']('2026. 10. 22.') == '2026-10-22'; assert p['parse_date']('2026-10-22') == '2026-10-22'; assert str(p['parse_decimal']('1.234,56')) == '1234.56'; assert p['parse_date']('not-a-date') is None; print('PARSER_UNIT_TESTS=4_PASS')"
if ($LASTEXITCODE -ne 0) { throw 'PARSER_UNIT_TESTS_FAILED' }
Write-Host '=== FETCH AND PARSE 7 TARGET FUNDS ==='
& $py $scriptPath
if ($LASTEXITCODE -ne 0) { throw "F4_TARGET_RUN_FAILED:$LASTEXITCODE" }
