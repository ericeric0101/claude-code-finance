---
name: research-monitor
description: Create and evaluate machine-readable monitoring rules (fundamental warnings and price reassessment levels) for researched US companies, with optional TradingView alert text or Pine Script. Use when asked for monitoring rules, alerts, reassessment triggers, or whether any watch condition has fired.
---

# Research Monitor

File: `research/<TICKER>/monitoring/rules.yaml`. Evaluate with
`python3 scripts/research_state.py check-rules TICKER` against
`financials/latest.json` metrics (states: triggered / not_triggered / missing_data).

```yaml
monitoring:
  fundamental:
    revenue_growth: {metric: revenue_growth_yoy_pct, warning: "<20%", basis: "..."}
    gross_margin:   {metric: gaap_gross_margin_pct,  warning: "<52%", basis: "..."}
    dilution_yoy:   {metric: diluted_shares_yoy_pct, warning: ">5%",  basis: "..."}
    backlog_yoy:    {metric: rpo_yoy_pct,            warning: "<0%",  basis: "..."}
  market:
    reassess_price: [12, 15, 20]
    basis: valuation-map boundaries ...
    meaning: reassess thesis and valuation; not an entry price, exit price or order
```

## Rules for writing rules

- Derive thresholds from the thesis invalidation conditions, guidance or the
  valuation map; record `basis`, and label analyst choices as assumptions.
- A metric the state does not have yields `missing_data`; add the metric to
  `financials/latest.json` from a primary source rather than guessing.
- Alerts mean **reassess**. Never convert a rule into a buy/sell order, position
  size or required entry price. Price levels come from model values, not from a
  fixed percentage haircut of one DCF.

## TradingView (optional)

TradingView is never required. On request, generate alert descriptions or a
Pine snippet from `market.reassess_price`, e.g.:

```pine
//@version=5
indicator("PL reassessment levels", overlay=true)
for lvl in array.from(3.0, 12.0, 25.0)
    line.new(bar_index - 1, lvl, bar_index, lvl, extend=extend.both, color=color.gray)
alertcondition(ta.cross(close, 12.0), "PL crosses 12", "Reassess PL vs DCF base value (research note, not an order)")
```
