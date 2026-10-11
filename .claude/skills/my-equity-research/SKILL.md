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

Every stock answer and report must begin with a compact decision summary:
**BUY / ACCUMULATE / WATCH / AVOID**, a one-line reason, the price/date used,
and a **reasonable buy observation range** (or state explicitly that no
defensible range can be set). Explain the inputs and conditions for that
range. It is an analytical watch range, never personalized investment advice,
an instruction to trade, a guarantee of fair value, or an implied position
size.

Use these consistent research labels:

- **BUY:** the thesis passes critical checks, data confidence is at least
  medium, and market price is at or below 80% of normalized base value.
- **ACCUMULATE:** the thesis passes critical checks, data confidence is at
  least medium, and price is above 80% but at or below 90% of normalized base
  value. This describes research valuation, not purchase frequency or size.
- **WATCH:** the thesis remains viable but price is above 90% of base value,
  evidence/confidence is insufficient, valuation methods disagree materially,
  or a material event needs resolution. Prefer WATCH when multiple conditions
  are uncertain.
- **AVOID:** a critical thesis-invalidating, solvency, governance, or accounting
  issue makes valuation unsafe to rely on. Cheapness cannot override it.

Unless company-specific evidence justifies another method, calculate the
observation range as **80%–90% of normalized base value per share**, lower to
upper. Label it conditional on the cited assumptions and share-count date;
state which operating evidence would invalidate it. If source quality,
normalized cashflow, peer checks, or valuation disagreement make the base value
too weak, provide the formula-derived interval only as a conditional model
reference and mark the actionable observation range `not established`.
Do not use bear-case liquidation levels or arbitrary entry prices as a buy
range. Never produce a range for AVOID.

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
11. Consider current macro/geopolitical event channels that are material to
    the named business, and show the explicit label and conditional buy
    observation range before the full report.

Label material statements as Fact, Calculation, Assumption or Interpretation.
An unavailable data source is a disclosed gap, not permission to substitute
remembered numbers. AAPL is the initial pipeline test; PL's Deep Dive prompt
is prepared in `docs/research-prompts.md` and is run when requested.
