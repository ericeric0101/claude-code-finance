#!/usr/bin/env python3
"""Acquire dated SEC records using the unmodified finance-skill client.

Run with the finance-skill uv environment. Raw payloads are ignored by Git.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.claude/skills/finance-skill/scripts'))
import sec_edgar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ticker')
    parser.add_argument('--cik', help='Required for tickers absent from upstream CIKS')
    args = parser.parse_args()
    ticker = args.ticker.upper()
    cik = args.cik or sec_edgar.CIKS.get(ticker)
    if not cik or not cik.isdigit():
        parser.error('Supply a numeric --cik; do not pass an unknown ticker as a CIK')
    dest = ROOT / 'research' / ticker / 'raw'
    dest.mkdir(parents=True, exist_ok=True)
    submissions = sec_edgar.get_submissions(cik)
    (dest / 'submissions.json').write_text(json.dumps(submissions, indent=2))
    time.sleep(0.15)
    facts = sec_edgar.get_company_facts(cik)
    (dest / 'companyfacts.json').write_text(json.dumps(facts, indent=2))
    recent = submissions['filings']['recent']
    records = []
    counts = {'10-K': 0, '10-Q': 0, '8-K': 0, 'DEF 14A': 0}
    for i, form in enumerate(recent['form']):
        if form not in counts or counts[form] >= {'10-K': 5, '10-Q': 8, '8-K': 8, 'DEF 14A': 1}[form]:
            continue
        counts[form] += 1
        records.append({
            'form': form, 'filed': recent['filingDate'][i],
            'period_end': recent['reportDate'][i],
            'accession': recent['accessionNumber'][i],
            'url': sec_edgar.get_filing_url(cik, recent['accessionNumber'][i], recent['primaryDocument'][i]),
        })
    manifest = {'ticker': ticker, 'cik': cik, 'company': submissions['name'],
                'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                'records': records}
    (dest.parent / 'filing-manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
