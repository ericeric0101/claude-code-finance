---
name: valuation-monitor
description: Maintain valuation history, reverse-DCF market-implied expectations, the valuation map, earnings / revenue catch-up scenarios and the expectation gap for researched US companies using the repo's existing valuation scripts. Use when updating valuation, when asked whether a stock became more or less demanding, what the market is pricing in, or how expectations compare with the base and bull cases.
---

# Valuation Monitor

Engines (do not write a new DCF engine): `stock-analysis/scripts/valuation.py`
(DCF, reverse DCF, multiples), `scripts/recommendation.py` (valuation map,
reverse-DCF comparison, earnings and revenue catch-up), company-specific
normalization such as `scripts/normalize_aapl.py`. Validated arithmetic is not
changed to fit reports.

State: `valuation/latest.json` (current), `valuation/assumptions.json`,
`valuation/history.csv` (upserted by as_of × method). Dated inputs under
`research/<TICKER>/` remain authoritative for their date.

## Update procedure

1. Refresh prices first (`uv run --project .claude/skills/finance-skill/scripts python
   scripts/price_reaction.py fetch TICKER`) and value against the latest close
   (intraday quote only if labelled). Alpha Vantage before yfinance.
2. Re-run the existing method inputs with updated filings / assumptions; record
   each method's bear / base / bull in `latest.json["methods"]`.
3. Reverse DCF: solve the operating assumption the price requires; store in
   `reverse_dcf` with base / bull comparisons. If it cannot be solved
   credibly, set `status: not established` with the reason (see PL).
4. `python3 scripts/recommendation.py research/<T>/recommendation-input.json`
   → valuation map position and catch-up tables.
5. Expectation gap: put `expectations.market_implied`, `internal_base`, `bull`
   (same metric keys) in `latest.json`; move the prior `expectation_gap.metrics`
   to `expectation_gap.previous_metrics`; run
   `python3 scripts/research_state.py expectation-gap TICKER` for per-metric
   position and direction (widening / stable / narrowing). Do not collapse it
   into one arbitrary score.
6. `python3 scripts/research_state.py record-valuation TICKER`.

## Output: Valuation Map, not a buy price

Report: current price/date; each method's values; reverse-DCF implied
assumptions; valuation map zones from model values; valuation confidence and
dispersion; catch-up scenarios; previous → current for each.

**Catch-up (scenarios, not forecasts):**
- Profitable companies: price held constant, EPS or FCF/share grows at several
  rates → future P/E or P/FCF (`research_state.py catch-up`).
- Growth-stage companies: EV held constant, revenue grows at several rates →
  future EV/Sales, with the caveat that financing, SBC and ATM dilution can make
  per-share outcomes worse.

**Expectation gap example:** market-implied revenue CAGR ~30% / FCF margin ~22%
vs internal base 25% / 20% → "market expectations are moderately above the base
case"; then state whether the gap is widening, stable or narrowing.

Never output `buy_range`, `entry_price` or a DCF × 80–90% default; the state tool
rejects those fields. Any margin-of-safety reference follows the exact label in
`docs/recommendation-policy.md`.
