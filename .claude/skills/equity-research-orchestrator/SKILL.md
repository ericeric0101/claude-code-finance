---
name: equity-research-orchestrator
description: Coordinate this repo's continuous US equity research. Use when the user asks to initialize research on a new ticker, update an existing company, deep dive a company, show what changed since the last analysis, show the current thesis or monitoring rules, or run the monthly watchlist review (including /init-stock, /update-stock, /deep-stock, /watch-stock, /monthly-research). Routes work to existing skills and updates research/<TICKER>/ state instead of writing another standalone report.
---

# Equity Research Orchestrator

The question this system answers is **"What changed since the previous research
state?"**, not "write another stock analysis." Every workflow reads the stored
state first, gathers only new evidence, and writes changes back to
`research/<TICKER>/` (schema: `docs/research-state-schema.md`).

Do not duplicate other skills. Delegate:

| Need | Skill |
|---|---|
| SEC EDGAR, Alpha Vantage, yfinance data | `finance-skill` |
| Fundamental framework, QA scripts (verify_data, ratios, valuation, score, lint_report), challenge pass | `stock-analysis` |
| Action labels, report shape, valuation decision layer, events screen | `my-equity-research` + `docs/recommendation-policy.md` |
| Management commentary and promises | `management-change` |
| Thesis component status | `thesis-monitor` |
| Valuation history, reverse DCF, map, catch-up, expectation gap | `valuation-monitor` |
| Price / volume reaction to events | `market-reaction` |
| Monitoring rules and alerts | `research-monitor` |
| Cross-company monthly review | `research-review` |

State tool (local only, no network): `python3 scripts/research_state.py <cmd> TICKER`
with `init`, `status`, `list`, `snapshot`, `record-valuation`, `change-report`,
`check-rules`, `catch-up`, `expectation-gap`.

## Always refresh prices first

Every intent that touches a ticker starts by refreshing prices (network):
`uv run --project .claude/skills/finance-skill/scripts python scripts/price_reaction.py fetch TICKER`
(Alpha Vantage for recent sessions, yfinance only to backfill older dates).
Use the latest completed close; if the US session is open, also cite
`market/latest-quote.json` and label it intraday. Valuation-map position,
catch-up tables and any price comparison use that latest price, not the
price stored at the last research date. Filings and other evidence stay
local-first: only fetch what is newer than the stored state.

## Intents

**INIT `<TICKER>`** — baseline state.
1. Verify a numeric CIK (`finance-skill`; unknown tickers need a verified CIK).
2. `research_state.py init TICKER --company ... --cik ...` (never overwrites).
3. Run a Standard analysis via `my-equity-research` / `stock-analysis`; save the
   dated report at `research/<TICKER>/<TICKER>-analysis-<date>.md` with its inputs.
4. Fill `thesis/current.yaml`, `thesis/invalidation-rules.yaml`,
   `valuation/latest.json` + `assumptions.json`, `financials/latest.json`,
   `management/*.json`, `monitoring/rules.yaml`, `evidence/sources.json`.
5. `snapshot`, `record-valuation`, then `change-report` (baseline).

**UPDATE `<TICKER>`** — incremental.
1. `status TICKER`; note `as_of`, latest reported period and `evidence/sources.json`.
2. Retrieve only filings / releases dated after the stored state (SEC
   submissions list first). If no new filings, still refresh prices and
   report the price-only change (valuation-map position, catch-up), without
   changing thesis status.
3. `management-change` → statements, wording changes, promise status.
4. `thesis-monitor` → update component status only on evidence.
5. `valuation-monitor` → re-run existing scripts with new inputs; update
   `valuation/latest.json`, then `record-valuation`.
6. `research-monitor` → `check-rules`; adjust rules only with a stated reason.
7. `snapshot` and `change-report --out research/<T>/reports/<date>-change-report.md`.
   The change report is the primary output; a long-form report is optional.

**DEEP `<TICKER>`** — full current deep dive (`my-equity-research` Deep Dive
depth), then the UPDATE state steps so the state reflects it.

**WATCH `<TICKER>`** — refresh prices, then read-only `status`, `check-rules`,
next catalysts, reassessment triggers and open promises against the latest price.

**WHAT CHANGED** — `change-report TICKER`; add context from `management/changes.md`.

**MONTHLY** — `research-review` across `research_state.py list`.

## Rules

- Primary sources first (`docs/data-source-policy.md`); label Fact / Calculation /
  Assumption / Interpretation; never fabricate consensus estimates.
- Thesis status changes require evidence; price action alone is not evidence.
- No mechanical DCF haircut buy range; WATCH is not a wait-for-a-price instruction.
- Preserve prior state: upsert history by date, never delete prior snapshots or
  dated reports. Git history is the audit trail; commit after material updates.
- Research classifications are not personalized advice or orders.
