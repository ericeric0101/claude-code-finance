---
name: my-equity-research
description: Coordinate this project's finance-skill and stock-analysis for equity research with short and long term theses, scenario valuation, downside and observable invalidation conditions. Use for this project's stock research reports and follow-up updates.
---

# My Equity Research

Read `../finance-skill/SKILL.md` for data acquisition and
`../stock-analysis/SKILL.md` for the document-first research framework.
Keep upstream skills unchanged; put personal research requirements here.

Default to Standard analysis unless the user chooses another depth. Prioritize
SEC filings and issuer materials, preserve source dates, units and periods,
then run stock-analysis intake verification, calculations, challenge pass and
report linting. Save outputs under `research/<TICKER>/` with a dated report.
Use the user's research date and Asia/Taipei timezone; market prices carry
their own trading date and exchange timezone. Never describe a test or a
partially sourced report as a completed live research workflow.

Every stock answer and report begins with an evidence-based action, a one-line
reason, dated market price, and valuation confidence. Do not default to a buy
price or mechanically convert one DCF output to an entry threshold.

Use BUY, ACCUMULATE, WATCH, HOLD EXISTING, or AVOID. Choose the action from
business quality, balance sheet, valuation dispersion, reverse-DCF expectations,
earnings / FCF growth, confidence, catalysts / risks, and thesis status. WATCH
means that current price requires aggressive assumptions or evidence remains
incomplete; it does not mean “wait for a crash.” HOLD EXISTING is only available
when the user has disclosed a current holding. Never infer holdings or provide
personalized position sizing.

Every valuation section separates: (1) model values and bear/base/bull cases,
(2) market-implied expectations from reverse DCF, (3) a price map derived from
available method values, and (4) the investment action. State valuation
confidence and method dispersion. When methods materially disagree, say:
“Valuation dispersion is high; confidence in a single fair-value estimate is
low.” Do not conceal disagreement by averaging unlike methods.

A margin-of-safety haircut is optional scenario analysis only. If shown, label
it exactly **“Optional margin-of-safety reference based on one valuation
method”**, name the method and haircut, and check whether WACC, terminal
normalization, reinvestment, ROIIC, margins, SBC, cash-flow normalization,
scenario weighting or multiple normalization already contain conservative
assumptions. Warn if another haircut may double-count risk. It must never be
called fair value, a recommended buy price, or a required entry price.

When current price is far from modeled values, quantify the gap, explain
reverse-DCF expectations, show cross-checks, and add an earnings / FCF catch-up
scenario when supportable. State that valuation zones are not forecasts and do
not require staying in cash until reached. Follow `docs/recommendation-policy.md` and the project-owned `docs/research-report-template.md`; preserve the upstream stock-analysis package unchanged.

Before assigning a label, check current-period company filings and recent
events through the report date. In addition to company catalysts, screen
macro and geopolitical events that can plausibly affect this issuer: central
bank decisions and yield moves, inflation/growth and FX, wars/sanctions/export
controls/shipping disruption, oil/energy and other material inputs, tariffs,
and relevant regulation. Select factors by the company's actual revenue,
cost, financing, suppliers, geography, and sector. For each material event,
record date/status, primary source, exposure channel, direction, evidence or
uncertainty, and where it enters scenarios/discount rate. Size its possible
cashflow or capital-cost effect when sourced inputs permit. Otherwise call it
a watch item, never a fabricated adjustment. Avoid double-counting one risk
in both bear cashflows and WACC. Treat headlines as discovery leads; verify
material facts with the issuer, regulator, central bank, government, or
reputable primary data source.

Put the event check in the recency section and summarize only price-relevant
events in the verdict. If nothing material is found, say which exposure areas
were checked and through what date; do not imply an exhaustive global scan.

Each report should additionally:

1. Separate short term catalysts and thesis from the long term business thesis.
2. Define observable thesis invalidation conditions, including whether any
   condition has already occurred.
3. Show bear, base and bull valuations with explicit growth, margins, cash
   conversion, discount rates, share counts and valuation horizons.
4. Quantify fundamental downside under a severe scenario. Explain that this
   is a scenario, not a guaranteed maximum loss; equity can lose its full value.
5. Compare common business and macro risk exposures with existing holdings
   only when holdings are provided. Do not invent a portfolio or a statistical
   correlation; numeric correlations require aligned return data and a window.
6. Classify the business's research role as Core, Growth, Speculative or
   Tactical, with reasoning. This classification is not position sizing.
7. Cross-check valuation with at least two suitable methods. Explain which
   methods are unsuitable for the business and why.
8. State what price decline and operating evidence would make valuation
   attractive, including cases where falling price reflects a broken thesis.
9. Compare expectations embedded in the current price with realistic operating
   assumptions; label reverse DCF inputs as assumptions.
10. End with **What must go right**, **What can go wrong**, and
    **What would change my mind**.
11. Consider current macro/geopolitical event channels material to the business.
12. Start with the action, current price/date, valuation confidence and the key
    reverse-DCF conclusion; do not require a fixed buy-range output.

Label material statements as Fact, Calculation, Assumption or Interpretation.
An unavailable data source is a disclosed gap, not permission to substitute
remembered numbers. AAPL is the initial pipeline test; PL's Deep Dive prompt
is prepared in `docs/research-prompts.md` and is run when requested.
