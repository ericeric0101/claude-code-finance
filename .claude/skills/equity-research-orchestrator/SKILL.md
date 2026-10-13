---
name: equity-research-orchestrator
description: Coordinate this repo's continuous US equity research. Use when the user asks to initialize research on a new ticker, update an existing company, deep dive a company, show what changed since the last analysis, show the current thesis or monitoring rules, run the monthly watchlist review, scan for new research events, show the research queue or which company to research first, show the watchlist dashboard, or find stale research (including /init-stock, /update-stock, /deep-stock, /watch-stock, /monthly-research, /scan-research, /research-queue, /research-dashboard, /stale-research). Routes work to existing skills and updates research/<TICKER>/ state instead of writing another standalone report.
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
with `init`, `status`, `list`, `snapshot`, `snapshot-state`, `record-valuation`,
`record-gap`, `refresh-financials`, `change-report`, `check-rules`, `catch-up`,
`expectation-gap`.

Level 3 engine (see `docs/us-equity-research-os.md` §15):
`scripts/research_pipeline.py init|update TICKER --cik CIK` runs the whole INIT /
UPDATE sequence; `monthly_research_review.py` runs MONTHLY. Building blocks:
`build_fundamental_history.py`, `assumption_history_check.py`,
`build_management_history.py`, `build_valuation_history.py`, `state_diff.py`,
`backfill_state_snapshots.py`.

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

**INIT `<TICKER>`** — baseline state (never an empty shell).
1. Verify a numeric CIK (`finance-skill`; unknown tickers need a verified CIK).
2. `research_pipeline.py init TICKER --cik CIK`: state, SEC data, 5Y + 8Q history,
   prices since listing, earnings events, management history and promises,
   stock-analysis ratios / verify_data, auto-draft thesis / valuation / rules,
   assumption-vs-history check, historical valuation, snapshot, baseline report.
   Drafts are labelled `draft_auto`; existing analyst files are kept.
3. Review the drafts. For a full report, run a Standard analysis via `my-equity-research` / `stock-analysis`; save the
   dated report at `research/<TICKER>/<TICKER>-analysis-<date>.md` with its inputs.
4. Fill `thesis/current.yaml`, `thesis/invalidation-rules.yaml`,
   `valuation/latest.json` + `assumptions.json`, `financials/latest.json`,
   `management/*.json`, `monitoring/rules.yaml`, `evidence/sources.json`.
5. `snapshot`, `record-valuation`, then `change-report` (baseline).

**UPDATE `<TICKER>`** — incremental. `research_pipeline.py update TICKER --cik CIK`
performs steps 1-13 (previous snapshot → new SEC filings only → history merge →
management / promises → rules → re-price only changed inputs → valuation history →
snapshot → multi-domain change report). Then apply analyst judgment:
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

**MONTHLY** — `monthly_research_review.py` across `research_state.py list`, then
`research-review` for commentary.

## Level 4 intents (research command center)

Level 4 sits on top of the intents above; it never replaces INIT / UPDATE / MONTHLY and
adds no state system of its own beyond `research/queue/`, `research/calendar/`,
`research/dashboard/` and per-ticker `monitoring/scan-state.json`. Architecture and
operating guide: `docs/us-equity-research-os.md` §16, `docs/level4-operating-guide.md`.
CLI: `python3 scripts/research_command_center.py scan|queue|prioritize|dashboard|stale|calendar`.

**SCAN-EVENTS** (`/scan-research`) — refresh prices, then `scan --refresh --skip-prices`:
`research_event_detector.py` (incremental: SEC forms, issuer announcements, guidance
changes, market moves, rule / promise / gap / percentile state changes, thesis-linked
macro only) → `research_event_classifier.py` (A FULL_UPDATE_REQUIRED, B TARGETED_UPDATE,
C MARKET_REACTION_ONLY, D LOW_PRIORITY_INFORMATIONAL) → `research_queue.py` →
`research_priority.py`. Also refreshes `kpi_registry.py`, `guidance_tracker.py`,
`catalyst_calendar.py`, `stale_research.py`.

**RESEARCH-QUEUE / PRIORITIZE** (`/research-queue`) — `prioritize` then `queue`. Route
each open item: A → UPDATE (`/update-stock TICKER`, which completes the ticker's A / B
items); B → the owning skill named in `required_workflow`; C → `market-reaction` only
(no full DCF unless the state changed); D → log only. Close items with
`research_queue.py set EVENT_ID completed|dismissed --note`.

**COMMAND-CENTER** (`/research-dashboard`) — `dashboard` → `research/dashboard/current.md`.

**STALE-CHECK** (`/stale-research`) — `stale` → `research/dashboard/stale-research.md`.

Flow examples: new 10-Q → A → HIGH → `/update-stock PL`. Large price move with no filing →
C → MEDIUM → `price_reaction.py analyze` → no full DCF unless the state changed.

Level 4 building blocks used by UPDATE as well: `kpi_registry.py` (common + sector +
company KPIs → `financials/kpi-history.csv`), `management_semantic_diff.py`
(structured claims, FACT / CHANGE / INTERPRETATION / CONFIDENCE), `guidance_tracker.py`
(guidance vs actual; definition mismatch → `not_evaluable`). Optional P2:
`tradingview_alert_export.py`, `notebooklm_export.py`.

## Rules

- Report language: write all report prose (change reports, deep / full reports, monthly reviews, replies) in Traditional Chinese (繁體中文). Tickers, field names, YAML/JSON keys, section identifiers and code identifiers may stay English. Do not translate existing dated reports. `change-report` emits bilingual section headings; add any narrative in Traditional Chinese.
- Primary sources first (`docs/data-source-policy.md`); label Fact / Calculation /
  Assumption / Interpretation; never fabricate consensus estimates.
- Thesis status changes require evidence; price action alone is not evidence.
- No mechanical DCF haircut buy range; WATCH is not a wait-for-a-price instruction.
- Preserve prior state: upsert history by date, never delete prior snapshots or
  dated reports. Git history is the audit trail; commit after material updates.
- Research classifications are not personalized advice or orders.
- Automation is not trading: queue items, priorities and alerts mean "research / REASSESS";
  never emit BUY / SELL orders or execution instructions.
- Auto-generated thesis, valuation assumptions, KPI mappings, promise resolutions and
  semantic interpretations stay `draft_auto` with `review_required: true` until an
  analyst confirms them.
