# What Changed Since Last Review — PL

> Price-only update on 2026-10-12. SEC submissions for CIK 0001836833 since the stored 2026-09-03 10-Q/8-K contain only ownership filings (Forms 4 and 144); no new 10-Q, 10-K or 8-K. Thesis component statuses, valuation inputs and action are unchanged; an illustrative reverse DCF now quantifies the expectation gap (see below).

## Positive
- none

## Negative
- none

## Unchanged
- sovereign_defense_demand: supported
- revenue_growth_durability: supported
- backlog_visibility: weakening
- margin_and_cash_conversion: uncertain
- per_share_value_vs_dilution: weakening
- commercial_diversification: uncertain
- constellation_execution: uncertain
- liquidity: supported

## Management wording changes
- See management/changes.md (6 statements recorded)

## Promises
- pending: 6

## Thesis
- weakest component status: weakening

## Valuation (bear/base/bull)
- five-year scenario DCF: 3/12/25 (unchanged)

## Expectation gap
- Calculation: at the 2026-10-09 close the price implies about 36% five-year revenue CAGR if mature FCF margin is 20% at 25x, vs 25% internal base and 35% bull. Market expectations sit at or slightly above the bull growth case unless margins/multiples are also bull-level (then ~24.5%, near base). Direction: first quantified 2026-10-12; the prior state was qualitative only (about 43% above base value). This is not a change in fundamentals.

## Action
- WATCH (unchanged)

## Confidence
- low (unchanged)

## Next catalysts
- Q3 FY2027 results: guidance revenue $101-105m, adjusted EBITDA -$6m to -$1m, capex $30-37m (earnings 8-K 2026-09-03).
- Convertible note conversion window 2026-08-01 to 2026-10-31 (SEC 10-Q).
- Commissioning of satellites launched 2026-10-01 (issuer release).
- ATM usage and share count in the next 10-Q.

Price movement alone is not treated as evidence that fundamentals changed.

## Price since last review
- Fact: Latest completed close is $17.18 on 2026-10-09 (Alpha Vantage TIME_SERIES_DAILY, cross-checked with yfinance). That is the same close used for the 2026-10-11 state, so there is no change on a closing basis.
- Fact (intraday, session not closed): $16.45 at 2026-10-12 11:53 ET (yfinance), -4.2% vs the 2026-10-09 close. Not used for valuation state.
- Calculation: Valuation map vs 3/12/25. The $17.18 close sits between base and bull, 43% above base and 31% below bull. The intraday $16.45 sits in the same zone, 37% above base. No reassessment level (3 / 12 / 25) was crossed.
- Calculation: Catch-up is unchanged because EV is held at $5.9bn on the same close. At 25%/yr revenue growth, EV/sales falls from about 13.5x to 6.9x in three years. This is a scenario, not a forecast, and it excludes dilution.

## New SEC filings since 2026-09-03 (ownership only)
- Fact: Form 4 (filed 2026-10-02): director Ita M. Brennan sold 11,500 shares at $16.30 under a 10b5-1 plan. Form 144 filed 2026-10-01.
- Fact: Forms 4 (filed 2026-09-17/18): the CEO had 134,642 shares withheld for tax at $16.02 and gifted 80,000 shares. The President & CFO sold 55,663 shares at about $16.96 (10b5-1). The co-founder/CSO sold 52,240 shares at about $16.96 (10b5-1). Both also had tax-withholding (F) and trust-transfer (J) entries. Two Forms 144 were filed 2026-09-17.
- Interpretation: These are routine vest-related withholding and planned sales. They do not count as evidence on any thesis component, and they are not company share issuance, so per_share_value_vs_dilution stays weakening on the 10-Q evidence. Sources are listed in evidence/sources.json.

## Monitoring rules
- No new financial data, so the rule evaluation is unchanged. rpo_vs_fiscal_year_end is still triggered (reassess, not trade). backlog_yoy, dilution_yoy and fy27_revenue are still missing data until the Q3 FY2027 10-Q.

## Reverse DCF (new, illustrative)
- Calculation from Assumptions: holding the base-case structure (FY27 start $435.5m guidance midpoint, FCF margin −6% → 20% by year 5, 25x terminal EV/FCF, 10.5% discount rate, $375m net liquid assets, 410m diluted shares), the $17.18 close implies about 36.1% five-year revenue CAGR (34.8% at the $16.45 intraday quote). With bull-case margin (25%), multiple (30x) and discount rate (9.5%), the implied CAGR is about 24.5%.
- Check: the same simplified model reproduces the stored scenario values within about $0.6 (2.4 / 11.6 / 25.2 vs 3 / 12 / 25).
- Interpretation: the price needs bull-level growth at base margins, or base-level growth with bull-level margins and multiples. The solution is not unique, so valuation confidence stays low. Inputs are in valuation/latest.json → reverse_dcf.

## Other context checked (not used as evidence)
- An aggregator headline describing a "2026-10-01 8-K" with weaker guidance did not match EDGAR (no 8-K after 2026-09-03), so it was not used.
- Barclays Equal Weight/Hold and Goldman Hold were reported 2026-10-08/09 (MarketBeat/CNN; dates differ by source). Aggregator price targets were not adopted.
- The Oct 8 close (−3.2% on 19.1m shares) coincided with a sector-wide aerospace/defense selloff, not company news. The Oct 1 launch and the Berlin factory were already in the baseline.
