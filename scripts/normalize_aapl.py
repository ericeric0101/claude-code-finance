#!/usr/bin/env python3
"""Dated AAPL accounting bridge and explicitly assumed, reinvestment-aware DCF.

No credentials or network calls. Inputs are the sourced financial-data.json,
cashflow-source-inputs.json and discount-rate-inputs.json plus labelled model
assumptions. This is not a generic XBRL parser or a forecast generator.
"""
import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/AAPL'
sys.path.insert(0, str(ROOT / '.agents/skills/stock-analysis/scripts'))
import valuation


def driver_dcf(inputs, growth=None, wacc=None, margin=None, terminal_growth=None):
    """NOPAT growth is funded by reinvestment; no SBC add-back or dilution twice."""
    a = inputs['assumptions']
    g1 = a['stage1_growth'] if growth is None else growth
    w = inputs['discount_rate']['wacc'] if wacc is None else wacc
    tg = a['terminal_growth'] if terminal_growth is None else terminal_growth
    if not w > tg or not 0 < a['terminal_roiic']:
        raise ValueError('Invalid terminal assumptions')
    revenue = inputs['reported']['revenue']
    m = inputs['normalized']['ebit_margin'] if margin is None else margin
    nopat = revenue * m * (1-a['operating_tax_rate'])
    schedule = []
    pv = 0.0
    for year in range(1, a['stage1_years']+a['fade_years']+1):
        k = max(0, year-a['stage1_years'])
        fraction = k/a['fade_years'] if k else 0.0
        g = g1 + (tg-g1)*fraction
        roiic = a['stage1_roiic'] + (a['terminal_roiic']-a['stage1_roiic'])*fraction
        revenue *= 1+g
        nopat = revenue*m*(1-a['operating_tax_rate'])
        growth_reinvestment = nopat*g/roiic
        # The full-capex/neutral-WC baseline is a minimum cash budget, not a
        # second growth charge. Avoid counting the same reinvestment twice.
        minimum_reinvestment = max(0, (a['normalized_capex']-a['normalized_ppe_depreciation']
                                      -a['normalized_working_capital_cash_credit'])
                                   *revenue/inputs['reported']['revenue'])
        reinvestment = max(growth_reinvestment, minimum_reinvestment)
        fcf = nopat-reinvestment
        discounted = fcf/(1+w)**(year-0.5)
        pv += discounted
        schedule.append({'year':year,'growth':g,'roiic_assumption':roiic,
                         'revenue':revenue,'nopat':nopat,'growth_reinvestment':growth_reinvestment,
                         'minimum_reinvestment':minimum_reinvestment,'reinvestment':reinvestment,
                         'fcff':fcf,'pv_fcff':discounted})
    terminal_nopat = nopat*(1+tg)
    terminal_reinvestment = max(terminal_nopat*tg/a['terminal_roiic'],
                               minimum_reinvestment*(1+tg))
    terminal_fcf = terminal_nopat-terminal_reinvestment
    terminal_value = terminal_fcf/(w-tg)
    # Cash flows occur at year midpoints; the terminal perpetuity starts in
    # year n+1 and receives the same half-year timing convention.
    pv_terminal = terminal_value/(1+w)**(len(schedule)-0.5)
    ev = pv+pv_terminal
    equity = ev+inputs['bridge']['surplus_liquidity']-inputs['bridge']['financing_debt']
    shares = inputs['bridge']['diluted_share_proxy']
    return {'enterprise_value':ev,'equity_value':equity,'per_share':equity/shares,
            'pv_explicit':pv,'pv_terminal':pv_terminal,'terminal_pct_of_ev':pv_terminal/ev,
            'terminal_nopat':terminal_nopat,'terminal_reinvestment':terminal_reinvestment,
            'terminal_fcff':terminal_fcf,'terminal_ev_ebit':terminal_value/(nopat/(1-a['operating_tax_rate'])),
            'terminal_revenue':revenue,'schedule':schedule,'wacc':w,'stage1_growth':g1,
            'terminal_growth':tg,'ebit_margin':m}


def solve_growth(inputs, target):
    low, high = -.02, .30
    if not driver_dcf(inputs, low)['enterprise_value'] <= target <= driver_dcf(inputs, high)['enterprise_value']:
        return None
    for _ in range(90):
        mid = (low+high)/2
        if driver_dcf(inputs, mid)['enterprise_value'] < target: low=mid
        else: high=mid
    return (low+high)/2


def solve_wacc(inputs, target):
    low, high = inputs['assumptions']['terminal_growth']+.001, .20
    if not driver_dcf(inputs,wacc=high)['enterprise_value'] <= target <= driver_dcf(inputs,wacc=low)['enterprise_value']:
        return None
    for _ in range(90):
        mid=(low+high)/2
        if driver_dcf(inputs,wacc=mid)['enterprise_value'] > target: low=mid
        else: high=mid
    return (low+high)/2


def build_inputs():
    f = json.loads((OUT/'financial-data.json').read_text())
    d = json.loads((OUT/'discount-rate-inputs.json').read_text())
    t = f['ttm']
    q = f['quarters'][-1]
    last = f['annual'][-1]
    a = {'classification':'Assumptions, not issuer guidance or observed sustainable cashflows',
         'operating_tax_rate':.18,'tariff_refund_margin_points':.02,
         'normalized_capex':last['capex'],'normalized_ppe_depreciation':8000,
         'normalized_working_capital_cash_credit':0,
         'operating_cash_reserve':10000,'stage1_growth':.08,'stage1_years':10,
         'fade_years':5,'terminal_growth':.03,'stage1_roiic':1.0,'terminal_roiic':.20,
         'sbc_policy':'EBIT includes SBC; no SBC add-back, no second subtraction. Future dilution assumed offset by cash-equivalent SBC cost.',
         'lease_policy':'Operating leases remain rental operating costs; financing-debt EV convention. Finance-lease debt-only FY25-sized stress quantified; latest principal/cashflow gap not quantified.',
         'share_policy':'Latest reported quarter weighted-average diluted shares, not verified October fully diluted outstanding count.',
         'capex_policy':'Full FY25 cash PP&E capex anchor; not maintenance-only. FY25 rounded PPE depreciation8000 is forward assumption, not exact TTM. Other amortization remains expensed in EBIT. Growth investment is max(g/ROIIC*NOPAT, scaled baseline netcapex/WC budget), not sum.',
         'working_capital_policy':'Remove all observed operating asset/liability cash timing; neutral normalized baseline. Future total reinvestment modeled through ROIIC, includes capex net of D&A and operating WC.'}
    refund = q['revenue']*a['tariff_refund_margin_points']
    ebit = t['ebit']-refund
    nopat = ebit*(1-a['operating_tax_rate'])
    fcff = nopat+a['normalized_ppe_depreciation']-a['normalized_capex']+a['normalized_working_capital_cash_credit']
    normalized = {'tariff_refund_approximation':refund,'ebit':ebit,'ebit_margin':ebit/t['revenue'],
                  'nopat':nopat,'fcff':fcff,'nopat_minus_reported_net_income':nopat-t['net_income']}
    price=json.loads((OUT/'alpha-vantage-check.json').read_text()).get('price',336.64)
    bridge={'common_shares':q['shares_outstanding'],'diluted_share_proxy':q['diluted_shares'],
            'price':price,'price_date':'2026-10-09','share_date':q['end'],
            'market_cap_estimate':price*q['shares_outstanding'],
            'financing_debt':q['commercial_paper']+q['current_term_debt']+q['long_term_debt'],
            'liquidity':q['cash']+q['current_investments']+q['noncurrent_investments']}
    bridge['surplus_liquidity']=bridge['liquidity']-a['operating_cash_reserve']
    bridge['market_operating_ev']=bridge['market_cap_estimate']+bridge['financing_debt']-bridge['surplus_liquidity']
    bridge['diluted_basis_target_ev']=price*bridge['diluted_share_proxy']+bridge['financing_debt']-bridge['surplus_liquidity']
    return {'as_of':'2026-10-11','currency':'USD','units':'millions except per-share USD and decimal rates',
            'reported':t,'normalized':normalized,'assumptions':a,'bridge':bridge,
            'discount_rate':{'wacc':d['central']['wacc_blume'],'ke':d['central']['ke_blume'],
                             'sources':'discount-rate-inputs.json; see discount-rate-review.md'},
            'sources':{'financials':'financial-data.json; exact SEC tag provenance',
                       'cashflow_components':'cashflow-source-inputs.json',
                       'tariff_refund':'https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/',
                       'price':'alpha-vantage-check.json; market-data.json cross-check'},
            'limitations':['Tariff uplift estimated from rounded approximately 2 margin points, not exact refund cash collection.',
                           '18% tax and neutral WC are normalization assumptions, not statutory or issuer-guided cash tax.',
                           'Future ROIIC is an explicit sensitivity assumption, not financing-distorted historical ROIC.',
                           'PPE depreciation uses rounded FY25 anchor because exact9M split unavailable; intangible amortization is not added back, but unmatched additional intangible cash investment remains a scenario risk.',
                           'No current fully diluted shares or exact October debt fair value; minimum operating cash reserve assumed.',
                           'Cashflow and valuation completion does not complete missing peer-rating/document coverage.']}


def main():
    inputs=build_inputs()
    base=driver_dcf(inputs)
    b=inputs['bridge']; a=inputs['assumptions']; n=inputs['normalized']
    sensitivities=[]
    for w in [.085,.09,inputs['discount_rate']['wacc'],.10,.105,.11,.115]:
        for g in [.02,.025,.03,.035,.04]:
            r=driver_dcf(inputs,wacc=w,terminal_growth=g)
            sensitivities.append({'wacc':w,'terminal_growth':g,'per_share':r['per_share']})
    margin_grid=[]
    for margin in [.29,.31,n['ebit_margin'],.35,.37]:
        for g in [.04,.08,.12]:
            margin_grid.append({'ebit_margin':margin,'growth':g,'per_share':driver_dcf(inputs,growth=g,margin=margin)['per_share']})
    scenarios=[]
    for label,margin,g,tax,roiic,terminal_roiic in [('Bear',.29,.04,.20,.50,.15),
                                                 ('Base',n['ebit_margin'],.08,.18,1.0,.20),
                                                 ('Bull',.35,.12,.17,1.0,.25)]:
        i=copy.deepcopy(inputs)
        i['assumptions'].update(operating_tax_rate=tax,stage1_roiic=roiic,terminal_roiic=terminal_roiic)
        r=driver_dcf(i,growth=g,margin=margin)
        scenarios.append({'label':label,'growth':g,'ebit_margin':margin,'tax':tax,
                          'stage1_roiic':roiic,'terminal_roiic':terminal_roiic,
                          'per_share':r['per_share'],'terminal_pct_of_ev':r['terminal_pct_of_ev'],
                          'difference_to_price':r['per_share']/b['price']-1})
    # Separate earnings-method cross-check. Approximate normalized EBIT is
    # converted back to equity earnings using reported net nonoperating income;
    # tax normalized uniformly, therefore no additional Ireland add-back.
    normalized_net_income=(n['ebit']+inputs['reported']['pbt']-inputs['reported']['ebit'])*(1-a['operating_tax_rate'])
    normalized_eps=normalized_net_income/b['diluted_share_proxy']
    horizon=(__import__('datetime').date(2027,9,25)-__import__('datetime').date(2026,10,11)).days/365.25
    earnings=[]
    for label,growth,pe in [('Bear',.00,22),('Base',.10,28),('Bull',.20,34)]:
        future_eps=normalized_eps*(1+growth)**horizon
        price=future_eps*pe
        dividends=.27*4*horizon  # assumption: current quarterly rate maintained
        present=(price+dividends)/(1+inputs['discount_rate']['ke'])**horizon
        earnings.append({'label':label,'annual_earnings_growth':growth,'exit_pe':pe,
                         'future_eps':future_eps,'future_price_ex_dividends':price,
                         'horizon_years':horizon,'dividend_assumption':dividends,
                         'present_value_including_assumed_dividends':present})
    normalized_grid=[]
    for tax in [.16,.18,.20]:
        for capex in [10041,12715,16000,20000]:
            for wc in [-5000,0,5000]:
                normalized_grid.append({'tax':tax,'capex':capex,'wc_cash_credit':wc,
                                        'normalized_fcff':n['ebit']*(1-tax)+a['normalized_ppe_depreciation']-capex+wc})
    checks=[]
    cf=json.loads((OUT/'cashflow-source-inputs.json').read_text())
    ct=cf['derived_TTM_end_2026_06_27']
    for label, row in [*cf['reported'].items(), ('TTM',ct)]:
        total=sum(row[k] for k in ['net_income','da','sbc','other_noncash','ar','vendor_ar','inventory','other_assets','ap','other_liabilities'])
        checks.append({'name':f'{label} exact CFO component reconciliation','pass':abs(total-row['cfo'])<1e-8})
    for label,key in [('NI','net_income'),('CFO','cfo'),('SBC','sbc'),('D&A','da')]:
        financial_key='depreciation' if key=='da' else key
        checks.append({'name':f'TTM {label} independently extracted sources agree','pass':abs(ct[key]-inputs['reported'][financial_key])<1e-8})
    value=ct['cfo']
    accounting_bridge=[{'operation':'Reported TTM CFO','change':value,'running_total':value,'classification':'Fact/Calculation'}]
    for label,change,kind in [('Retain economic SBC cost; reverse CFO addback',-ct['sbc'],'Calculation'),
                              ('Reverse other noncash adjustments',-ct['other_noncash'],'Calculation'),
                              ('Remove actual asset/liability cash timing',-ct['all_operating_assets_liabilities_cash_effect'],'Calculation'),
                              ('Replace reported NI with normalized operating NOPAT',n['nopat']-ct['net_income'],'Assumption/Calculation'),
                              ('Replace total D&A with PPE-only assumed depreciation',a['normalized_ppe_depreciation']-ct['da'],'Assumption/Calculation'),
                              ('Subtract normalized full cash PPE capex',-a['normalized_capex'],'Assumption'),
                              ('Insert normalized working-capital cash credit',a['normalized_working_capital_cash_credit'],'Assumption')]:
        value+=change
        accounting_bridge.append({'operation':label,'change':change,'running_total':value,'classification':kind})
    checks.append({'name':'Reported-to-normalized cashflow bridge','pass':abs(value-n['fcff'])<1e-7})
    checks.append({'name':'FCFF formula','pass':abs(n['fcff']-(n['nopat']+a['normalized_ppe_depreciation']-a['normalized_capex']))<1e-8})
    checks.append({'name':'Operating cash removed once','pass':b['liquidity']-b['surplus_liquidity']==a['operating_cash_reserve']})
    checks.append({'name':'Finite terminal value','pass':math.isfinite(base['enterprise_value']) and base['wacc']>base['terminal_growth']})
    for year in base['schedule']:
        checks.append({'name':f'Year {year["year"]} growth reinvestment identity',
                       'pass':abs(year['fcff']+year['reinvestment']-year['nopat'])<1e-7})
    reverse=solve_growth(inputs,b['diluted_basis_target_ev'])
    checks.append({'name':'Matched reverse per-share target',
                   'pass':reverse is not None and abs(driver_dcf(inputs,reverse)['per_share']-b['price'])<1e-6})
    reinvestment_sensitivity=[]
    for stage_roiic in [.5,.75,1.0]:
        for terminal_roiic in [inputs['discount_rate']['wacc'],.10,.15,.20,.25]:
            i=copy.deepcopy(inputs)
            i['assumptions'].update(stage1_roiic=stage_roiic,terminal_roiic=terminal_roiic)
            reinvestment_sensitivity.append({'stage1_roiic':stage_roiic,'terminal_roiic':terminal_roiic,
                                            'per_share':driver_dcf(i)['per_share']})
    capex_wc_sensitivity=[]
    for capex in [12715,16000,20000,25000]:
        for wc in [-5000,0,5000]:
            i=copy.deepcopy(inputs)
            i['assumptions'].update(normalized_capex=capex,normalized_working_capital_cash_credit=wc)
            capex_wc_sensitivity.append({'capex':capex,'wc_cash_credit':wc,'per_share':driver_dcf(i)['per_share']})
    bullish=copy.deepcopy(inputs)
    bullish['assumptions'].update(operating_tax_rate=.17,stage1_roiic=1.,terminal_roiic=.25)
    bullish_result=driver_dcf(bullish,growth=.12,wacc=.085,margin=.35)
    conclusion_flip={'base_break_even_wacc':solve_wacc(inputs,b['diluted_basis_target_ev']),
                     'joint_bullish_case':{'growth':.12,'margin':.35,'tax':.17,'terminal_roiic':.25,
                                          'wacc':.085,'per_share':bullish_result['per_share']}}
    checks.append({'name':'Lower discount rate raises value',
                   'pass':driver_dcf(inputs,wacc=.085)['per_share'] > base['per_share'] > driver_dcf(inputs,wacc=.115)['per_share']})
    checks.append({'name':'High capex and WC burden reduces value',
                   'pass':next(row['per_share'] for row in capex_wc_sensitivity if row['capex']==25000 and row['wc_cash_credit']==-5000)<base['per_share']})
    control=copy.deepcopy(inputs)
    control['assumptions'].update(stage1_roiic=1e12,terminal_roiic=1e12,
                                  normalized_capex=8000,normalized_ppe_depreciation=8000)
    legacy=valuation.forward_dcf(n['nopat'],a['stage1_growth'],10,5,.03,
                                inputs['discount_rate']['wacc'],0,0,None)
    control_ev=driver_dcf(control)['enterprise_value']
    expected_midyear=legacy['enterprise_value']*math.sqrt(1+inputs['discount_rate']['wacc'])
    checks.append({'name':'Zero reinvestment control matches independent upstream DCF with midyear timing',
                   'pass':abs(control_ev-expected_midyear)<1e-4})
    comparison={'company':'Apple Inc.','market':{'price':b['price'],'shares_out':b['diluted_share_proxy']},
                'dcf':{'base_fcf':n['fcff'],'stage1_growth':a['stage1_growth'],'stage1_years':10,'fade_years':5,
                       'terminal_growth':.03,'wacc':inputs['discount_rate']['wacc'],
                       'net_debt':b['financing_debt']-b['surplus_liquidity'],'shares_out':b['diluted_share_proxy']}}
    conventional=valuation.run(comparison)
    results={'status':'Accounting/model arithmetic checked; forecast assumptions not facts',
             'driver_dcf':base,'matched_reverse_growth':reverse,'market_operating_ev':b['market_operating_ev'],
             'diluted_basis_target_ev':b['diluted_basis_target_ev'],
             'reported_to_normalized_bridge':accounting_bridge,
             'conclusion_flip_tests':conclusion_flip,
             'finance_lease_debt_only_stress':{'assumed_additional_debt':1230,'source_period':'FY2025',
                                             'per_share_reduction':1230/b['diluted_share_proxy'],
                                             'limitation':'Debt-only size illustration; not latest exact liability or a lease cashflow reconstruction.'},
             'growth_terminal_roiic_sensitivity':reinvestment_sensitivity,
             'capex_wc_valuation_sensitivity':capex_wc_sensitivity,
             'dcf_scenarios':scenarios,'wacc_terminal_sensitivity':sensitivities,
             'margin_growth_sensitivity':margin_grid,'normalized_fcff_sensitivity':normalized_grid,
             'normalized_equity_earnings':normalized_net_income,'normalized_eps_proxy':normalized_eps,
             'earnings_method_crosscheck':earnings,'conventional_upstream_dcf':conventional,
             'checks':checks,'all_checks_pass':all(x['pass'] for x in checks)}
    for name,data in [('normalized-valuation-input.json',inputs),('normalized-valuation-output.json',results),
                      ('normalized-upstream-valuation-input.json',comparison),('normalized-upstream-valuation-output.json',conventional)]:
        (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    if not results['all_checks_pass']:
        raise ValueError('Accounting or model validation failed; inspect check results')
    print(json.dumps({'normalized_fcff':n['fcff'],'nopat':n['nopat'],'wacc':base['wacc'],
                      'driver_dcf_per_share':base['per_share'],'matched_reverse_growth':reverse,
                      'scenarios':scenarios,'checks_pass':results['all_checks_pass']},indent=2))


if __name__=='__main__': main()
