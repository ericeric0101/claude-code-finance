#!/usr/bin/env python3
"""Extract AAPL consolidated facts by exact period; retain filing provenance.

This is a company-specific intake adapter, not a generic XBRL parser.
Missing tags remain absent. No annualization or silent zero substitution.
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/AAPL'
AS_OF = '2026-10-11'
TAGS = {
    'revenue': 'RevenueFromContractWithCustomerExcludingAssessedTax',
    'cogs': 'CostOfGoodsAndServicesSold', 'ebit': 'OperatingIncomeLoss',
    'net_income': 'NetIncomeLoss', 'tax': 'IncomeTaxExpenseBenefit',
    'pbt': 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
    'cfo': 'NetCashProvidedByUsedInOperatingActivities',
    'capex': 'PaymentsToAcquirePropertyPlantAndEquipment',
    'sbc': 'ShareBasedCompensation', 'depreciation': 'DepreciationDepletionAndAmortization',
    'eps': 'EarningsPerShareDiluted', 'diluted_shares': 'WeightedAverageNumberOfDilutedSharesOutstanding',
    'buybacks': 'PaymentsForRepurchaseOfCommonStock', 'dividends_paid': 'PaymentsOfDividends',
    'equity': 'StockholdersEquity', 'total_assets': 'Assets',
    'current_assets': 'AssetsCurrent', 'current_liabilities': 'LiabilitiesCurrent',
    'inventory': 'InventoryNet', 'receivables': 'AccountsReceivableNetCurrent',
    'cash': 'CashAndCashEquivalentsAtCarryingValue',
    'current_investments': 'MarketableSecuritiesCurrent',
    'noncurrent_investments': 'MarketableSecuritiesNoncurrent',
    'current_term_debt': 'LongTermDebtCurrent', 'long_term_debt': 'LongTermDebtNoncurrent',
    'commercial_paper': 'CommercialPaper', 'shares_outstanding': 'CommonStockSharesOutstanding',
    'operating_leases': 'OperatingLeaseLiability', 'finance_leases': 'FinanceLeaseLiability',
}
DURATION = {'revenue','cogs','ebit','net_income','tax','pbt','cfo','capex','sbc',
            'depreciation','eps','diluted_shares','buybacks','dividends_paid'}


def main():
    facts = json.loads((OUT/'raw/companyfacts.json').read_text())['facts']['us-gaap']
    manifest = json.loads((OUT/'filing-manifest.json').read_text())
    links = {r['accession']: r['url'] for r in manifest['records']}
    intake = {'company':'Apple Inc.', 'ticker':'AAPL', 'as_of':AS_OF,
              'reporting_basis':'consolidated', 'currency':'USD', 'units':'millions',
              'fiscal_year_end':'September',
              'latest_reported_period':{'period':'Q3 FY2026','published':'2026-07-31'},
              'datapoints':[], 'not_available':[]}

    def extract(label, end, min_days=None, max_days=None):
        values = {'label':label,'end':end,'provenance':{}}
        for metric,tag in TAGS.items():
            unit = 'USD/shares' if metric=='eps' else 'shares' if 'shares' in metric else 'USD'
            entries = facts.get(tag,{}).get('units',{}).get(unit,[])
            candidates=[]
            for x in entries:
                if x['end']!=end or x['filed']>AS_OF: continue
                if metric in DURATION:
                    if min_days is None or 'start' not in x: continue
                    days=(date.fromisoformat(x['end'])-date.fromisoformat(x['start'])).days+1
                    if not min_days<=days<=max_days: continue
                elif 'start' in x: continue
                candidates.append(x)
            if not candidates: continue
            x=max(candidates,key=lambda a:a['filed'])
            values[metric]=x['val'] if metric=='eps' else x['val']/1e6
            source=f"SEC {x['form']} filed {x['filed']}, accession {x['accn']}, US GAAP {tag}"
            source_url=links.get(x['accn'],f"https://www.sec.gov/Archives/edgar/data/320193/{x['accn'].replace('-','')}/")
            values['provenance'][metric]={**x,'tag':tag,'unit':unit,'source':source,'url':source_url}
            intake['datapoints'].append({'metric':metric,'value':values[metric],
                'period':label,'basis':'consolidated','unit':'USD/share' if metric=='eps' else 'million shares' if 'shares' in metric else 'USD millions',
                'source':source+' '+source_url,'source_tier':1})
        if 'cfo' in values and 'capex' in values: values['fcf']=values['cfo']-values['capex']
        return values

    annual = [extract('FY'+str(y),end,350,380) for y,end in [
        (2021,'2021-09-25'),(2022,'2022-09-24'),(2023,'2023-09-30'),
        (2024,'2024-09-28'),(2025,'2025-09-27')]]
    quarters=[]
    for rec in reversed(manifest['records']):
        if rec['form']=='10-Q': quarters.append(extract(f"Quarter ended {rec['period_end']}",rec['period_end'],80,100))
    ytd26=extract('9M FY2026','2026-06-27',260,285)
    ytd25=extract('9M FY2025','2025-06-28',260,285)
    ytd24=extract('9M FY2024','2024-06-29',260,285)
    q4=[]
    for full,partial in [(annual[-2],ytd24),(annual[-1],ytd25)]:
        q4.append({'label':'Q4 '+full['label'],'end':full['end'],
            'calculation':'full fiscal year minus first nine months; source records in data-intake.json',
            **{k:full[k]-partial[k] for k in DURATION-{'eps','diluted_shares'} if k in full and k in partial}})
    quarter_trend=sorted(quarters+q4,key=lambda x:x['end'])[-8:]
    ttm={k:annual[-1][k]+ytd26[k]-ytd25[k] for k in DURATION-{'eps','diluted_shares'} if k in annual[-1] and k in ytd26 and k in ytd25}
    if 'cfo' in ttm and 'capex' in ttm: ttm['fcf']=ttm['cfo']-ttm['capex']
    result={'as_of':AS_OF,'units':'USD millions; shares in millions; EPS in USD',
            'annual':annual,'quarters':quarters,'quarter_trend':quarter_trend,'ytd26':ytd26,'ytd25':ytd25,'ttm':ttm,
            'ttm_formula':'FY2025 + 9M FY2026 - 9M FY2025; EPS not summed'}
    (OUT/'financial-data.json').write_text(json.dumps(result,indent=2))
    (OUT/'data-intake.json').write_text(json.dumps(intake,indent=2))
    periods=[]
    for p in annual:
        v={k:p[k] for k in ['label','revenue','cogs','depreciation','tax','equity','total_assets','current_assets','current_liabilities','inventory','receivables','cash','current_investments','cfo','capex','dividends_paid','shares_outstanding','diluted_shares'] if k in p}
        # The ratios utility accepts explicit EBIT/PAT, avoiding invented interest/other-income.
        v['ebit']=p['ebit'];v['pat']=p['net_income'];v['pbt']=p['pbt']
        if 'depreciation' in p:v['ebitda']=p['ebit']+p['depreciation']
        if 'commercial_paper' in p:v['short_term_debt']=p['commercial_paper']
        if 'current_term_debt' in p:v['current_maturities']=p['current_term_debt']
        if 'long_term_debt' in p:v['long_term_debt']=p['long_term_debt']
        periods.append(v)
    (OUT/'ratios-input.json').write_text(json.dumps({'company':'Apple Inc.','currency':'USD millions','basis':'consolidated','sector':'generic','periods_order':'oldest_first','periods':periods,'source':'SEC annual filing provenance in financial-data.json; explicit EBIT/PAT inputs'},indent=2))
    print(json.dumps({'annual':[{k:v for k,v in p.items() if k!='provenance'} for p in annual], 'ytd26':{k:v for k,v in ytd26.items() if k!='provenance'},'ttm':ttm},indent=2))


if __name__=='__main__': main()
