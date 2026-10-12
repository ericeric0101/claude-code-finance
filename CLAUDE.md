# Stock Deep Research — US Equity Continuous Research OS

This repo maintains persistent, versioned research state for US equities in
`research/<TICKER>/` and answers "what changed since the last review?" rather
than rewriting reports. Architecture: `docs/us-equity-research-os.md`.

Skills (`.claude/skills/`, shared with Codex via `.agents/skills/` symlinks):
- `equity-research-orchestrator`: entry point for init / update / deep / watch /
  monthly workflows (`/init-stock`, `/update-stock`, `/deep-stock`, `/watch-stock`,
  `/monthly-research`).
- `finance-skill` (data), `stock-analysis` (framework + QA scripts),
  `my-equity-research` (decision layer). Upstream packages stay unmodified;
  custom requirements go in project-owned skills and docs.
- `management-change`, `thesis-monitor`, `valuation-monitor`, `market-reaction`,
  `research-monitor`, `research-review`.

Rules:
- Primary sources first (`docs/data-source-policy.md`); aggregators never
  silently override filings. State basis, units, period, missing data.
- Label material statements Fact / Calculation / Assumption / Interpretation.
- Update prior state (`scripts/research_state.py`), don't rewrite blindly;
  keep dated reports; git history is research history.
- Prefer reverse DCF, expectation gap and the valuation map over target prices;
  never generate a mechanical DCF-haircut buy range (`docs/recommendation-policy.md`).
- Thesis changes require evidence; price action alone does not prove
  fundamentals changed. Alerts mean "reassess", never an order.
- Never fabricate consensus estimates or remembered numbers.
- Always refresh market prices before an analysis, update, watch or review
  (`uv run --project .claude/skills/finance-skill/scripts python scripts/price_reaction.py fetch <TICKER>`)
  and use the latest close; label an intraday quote as intraday. Filings stay local-first.
- Run stock-analysis verify_data, valuation, score, challenge and lint_report
  for full reports; a linter PASS is not source verification.
- Finance utilities: `uv run --project .claude/skills/finance-skill/scripts python ...`.
  Unknown tickers need a verified numeric CIK.
- Credentials live in ignored `.env`; never print, stage or commit them.
- Tests: `python3 -m unittest discover -s tests`.
