# Stock Deep Research

Project-level skills are under `.claude/skills/`:

- `finance-skill`: SEC EDGAR, Alpha Vantage and yfinance acquisition.
- `stock-analysis`: primary-document fundamental research and Python QA tools.
- `my-equity-research`: the project's thesis, scenarios and downside layer.

Read the selected skill and relevant references before using it. Preserve
upstream source folders; custom requirements belong in my-equity-research.
The user's current initial test is AAPL. PL is prepared, not scheduled or run.

Keep dated reports and reproducible inputs in `research/<TICKER>/`.
Use primary filings for financial facts and dated market sources for prices.
State reporting basis, units, period, missing data and assumptions explicitly.
Run stock-analysis verify_data, valuation, score, challenge and lint_report.
Never interpret a linter PASS as independent source verification.

Use `uv run --project .claude/skills/finance-skill/scripts python ...` for
finance utilities. Unknown tickers require a verified numeric CIK.
Credentials are in ignored `.env`; never print, stage or commit its contents.
Raw filings, cache, virtualenvs and local CLI installations are ignored.
See `docs/SETUP.md` for setup and the step-by-step completion record.
