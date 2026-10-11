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

Label material statements as Fact, Calculation, Assumption or Interpretation.
An unavailable data source is a disclosed gap, not permission to substitute
remembered numbers. AAPL is the initial pipeline test; PL's Deep Dive prompt
is prepared in `docs/research-prompts.md` and is run when requested.
