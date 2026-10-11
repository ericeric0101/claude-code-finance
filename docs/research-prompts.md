# Research prompts

Use these prompts directly in the Codex desktop project. Read `AGENTS.md`
and the full skills under `.agents/skills/`. No Claude login is needed.

## Skill discovery (step 10)

```text
Read AGENTS.md and the SKILL.md files under .agents/skills/.
What finance-skill, stock-analysis and my-equity-research skills are available?
Briefly describe when you would use each. Do not perform stock analysis yet.
```

## AAPL Standard (step 11)

```text
Run a Standard stock analysis on NASDAQ:AAPL.
Use finance-skill for SEC filings, financial statements and dated market data.
Use stock-analysis for document diligence, sector-relative analysis,
data verification, calculations, valuation, scorecard, challenge and report QA.
Distinguish Fact, Calculation, Assumption and Interpretation.
Save the report and its reproducible inputs under research/AAPL/.
State the actual newest reported period and any missing documents.
```

## PL Deep Dive (step 12 — prepared, not run)

```text
Perform a Deep Dive equity analysis of Planet Labs (NYSE:PL).
Use my-equity-research to coordinate finance-skill and stock-analysis.
Prioritize latest 10-K, 10-Q, recent 8-K, issuer earnings releases,
call materials and investor presentations. Resolve the numeric CIK before
calling the SEC scripts; PL is absent from finance-skill's built-in CIK list.
Cover business/revenue mix, moat, government vs commercial exposure,
growth/backlog, gross margins, operating leverage, FCF, SBC/dilution,
cash runway, capital intensity and ROIC where meaningful.
Justify the peer set. Use EV/Sales, EV/Gross Profit, reverse DCF and
bear/base/bull scenarios; do not apply P/E to a loss-making business.
Show source dates and filing references, distinguish Fact/Calculation/
Assumption/Interpretation, and define catalysts and observable invalidation.
Run data verification, an independent challenge pass and report linting.
Save research/PL/PL-analysis-YYYY-MM-DD.md plus inputs and source register.
```
