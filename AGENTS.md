# Stock Deep Research

Project-level skills are under `.agents/skills/`:

- `finance-skill`: SEC EDGAR, Alpha Vantage and yfinance acquisition.
- `stock-analysis`: primary-document fundamental research and Python QA tools.
- `my-equity-research`: the project's thesis, scenarios and downside layer.
- `equity-research-orchestrator`: persistent-state workflows (init, update,
  deep dive, watch, monthly review) over `research/<TICKER>/`; it routes to
  `management-change`, `thesis-monitor`, `valuation-monitor`,
  `market-reaction`, `research-monitor` and `research-review`.
  See `docs/us-equity-research-os.md` and `docs/dual-codex-claude-usage.md`.

Read the selected skill and relevant references before using it. Preserve
upstream source folders; custom requirements belong in my-equity-research.
The user's current initial test is AAPL. PL is prepared, not scheduled or run.

Keep dated reports and reproducible inputs in `research/<TICKER>/`.
Use primary filings for financial facts and dated market sources for prices.
State reporting basis, units, period, missing data and assumptions explicitly.
Run stock-analysis verify_data, valuation, score, challenge and lint_report.
Never interpret a linter PASS as independent source verification.

Every stock deliverable starts with an evidence-based BUY / ACCUMULATE / WATCH /
HOLD EXISTING / AVOID action, brief reason, price/date and valuation confidence.
Separate method values, reverse-DCF expectations, a model-derived valuation map,
earnings catch-up scenarios and the investment action. Do not generate a default
buy range from one DCF. Follow `.agents/skills/my-equity-research/SKILL.md`,
`docs/recommendation-policy.md` and `docs/research-report-template.md`. This is a
research classification, not a personalized trade instruction. Tie events to the company's disclosed
exposures, primary sources, and explicit scenarios; do not apply generic
headline premiums or double-count risk in cashflows and WACC.

Use `uv run --project .agents/skills/finance-skill/scripts python ...` for
finance utilities. Unknown tickers require a verified numeric CIK.
Credentials are in ignored `.env`; never print, stage or commit its contents.
Raw filings, cache, virtualenvs and local CLI installations are ignored.
See `docs/SETUP.md` for setup and the step-by-step completion record.

## Codex host compatibility

Codex is the project's default research host. Read
`.agents/skills/my-equity-research/SKILL.md` for stock research requests.
All Codex skill directories are relative symlinks to the complete,
versioned packages in `.claude/skills/`; do not duplicate or edit upstream files.
Claude-specific tool names in imported instructions describe operations:
use Codex shell tools for Bash, file tools for Read/Write/Glob/Grep,
available browsing tools for WebFetch/WebSearch, and user clarification for
AskUserQuestion. `allowed-tools` is upstream metadata, not a Codex permission
configuration. Use collaboration subagents when the selected research skill
explicitly requires delegation or an independent challenge. If unavailable,
state the limitation rather than claim an independent review.
Do not launch Claude, install a second agent, or require Claude authentication.
This Codex desktop conversation can run the workflow directly. The optional
local legacy Claude launcher is retained only for compatibility.
