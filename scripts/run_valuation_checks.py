#!/usr/bin/env python3
"""Reproduce AAPL sensitivity checks with the upstream valuation engine."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.agents/skills/stock-analysis/scripts'))
import valuation


def solve(doc, field, low, high, target, increasing=True):
    for _ in range(80):
        mid=(low+high)/2
        candidate=copy.deepcopy(doc)
        candidate['dcf'][field]=mid
        ev=valuation.run(candidate)['dcf']['enterprise_value']
        if (ev<target)==increasing: low=mid
        else: high=mid
    return (low+high)/2


def main():
    out=ROOT/'research/AAPL'
    doc=json.loads((out/'valuation-input.json').read_text())
    result=valuation.run(doc)
    target=result['ev_bridge']['enterprise_value']
    matched={'model':'same as forward DCF: 10 years stage1 + 5 year linear fade; other inputs unchanged',
             'target_enterprise_value':target,
             'implied_stage1_growth':solve(doc,'stage1_growth',0,.5,target),
             'original_reverse_model_implied_growth':result['reverse_dcf']['implied_growth']}
    rows=[]
    for base in [90000,110000,130000]:
        for wacc in [.08,.09,.10]:
            d=copy.deepcopy(doc)
            d['dcf'].update(base_fcf=base,wacc=wacc)
            d['reverse_dcf'].update(base_fcf=base,wacc=wacc)
            r=valuation.run(d)
            rows.append({'base_fcf_millions':base,'wacc':wacc,'dcf':r['dcf'],'reverse_dcf':r['reverse_dcf']})
    alternate=copy.deepcopy(doc)
    alternate['dcf'].update(base_fcf=130000,wacc=.08)
    breaks={'matched_model':matched,
            'break_even_base_fcf_millions':solve(doc,'base_fcf',1000,500000,target),
            'break_even_wacc':solve(doc,'wacc',.031,.15,target,increasing=False),
            'alternate_base_fcf':130000,'alternate_wacc':.08,
            'alternate_break_even_stage1_growth':solve(alternate,'stage1_growth',0,.5,target)}
    for name,value in [('valuation-sensitivity.json',rows),('valuation-matched-reverse.json',matched),('valuation-break-even.json',breaks)]:
        (out/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(breaks,indent=2))


if __name__=='__main__':main()
