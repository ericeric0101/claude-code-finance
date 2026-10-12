# US Equity Research OS

A continuous research system: each company has persistent, versioned state, and
each update answers **"What changed since the previous research state?"**

## 1. Architecture

```
            user: /init-stock /update-stock /deep-stock /watch-stock /monthly-research
                                   │  (Codex: natural language)
                                   ▼
                    equity-research-orchestrator  (routing, state discipline)
      ┌──────────────┬─────────────┼──────────────┬───────────────┬──────────────┐
      ▼              ▼             ▼              ▼               ▼              ▼
 finance-skill  stock-analysis  my-equity-   management-   thesis-monitor  valuation-monitor
 (SEC, Alpha    (framework,     research     change        (components,    (methods, reverse
  Vantage,       QA scripts,    (actions,    (statements,   invalidation)   DCF, map, catch-up,
  yfinance)      challenge)     policy)      promises)                      expectation gap)
      │                                                                      │
      │            market-reaction (price_reaction.py)   research-monitor (rules.yaml)
      ▼                                   │                       │
 ┌───────────────────────── research/<TICKER>/ state ─────────────────────────┐
 │ evidence/ management/ financials/ thesis/ valuation/ market/ monitoring/   │
 │ reports/  + dated reports and input/output JSON (authoritative per date)   │
 └────────────────────────────────────────────────────────────────────────────┘
                                   │
                         research-review (monthly, all tickers) → research/reviews/
                                   │
                              git history (audit trail)
```

## 2. Data flow

SEC / IR (tier 1) and market data (tier 3, yfinance tier 4) → `finance-skill`
clients → dated inputs in `research/<TICKER>/` → `stock-analysis` scripts
(`verify_data`, `ratios`, `valuation`, `score`, `lint_report`) and
`scripts/recommendation.py` → state files via `scripts/research_state.py` →
change report → git commit.

## 3. Skills

| Skill | Role |
|---|---|
| `equity-research-orchestrator` | Intents: init, update, deep, watch, what-changed, monthly |
| `finance-skill` | Data acquisition (upstream, unmodified) |
| `stock-analysis` | Fundamental framework and QA tools (upstream, unmodified) |
| `my-equity-research` | Decision layer: BUY / ACCUMULATE / WATCH / HOLD EXISTING / AVOID |
| `management-change` | Eight-quarter wording comparison; promise tracker |
| `thesis-monitor` | Component status from evidence |
| `valuation-monitor` | Valuation history, reverse DCF, map, catch-up, expectation gap |
| `market-reaction` | Event price / volume reactions (observation vs interpretation) |
| `research-monitor` | Machine-readable rules; optional TradingView |
| `research-review` | Monthly cross-company review |

## 4. Company state

See `docs/research-state-schema.md` (files, authority, field contracts).

## 5. Initial research flow

verify CIK → `research_state.py init` → Standard analysis and dated report →
fill thesis / valuation / financials / management / monitoring →
`snapshot` → `record-valuation` → baseline `change-report` → commit.

## 6. Update flow

refresh prices (`price_reaction.py fetch`, always) → `status` → list filings newer than `as_of` → management-change →
thesis-monitor → valuation-monitor → `check-rules` → `snapshot` →
`record-valuation` → `change-report --out reports/<date>-change-report.md` → commit.

Change report sections: Positive, Negative, Unchanged, Management wording
changes, Promises, Thesis, Valuation (previous → current), Expectation gap,
Action, Confidence, Next catalysts.

## 7. Monthly review flow

`list` → per ticker `status` / `check-rules` / `change-report` (UPDATE only where
new filings exist) → ten-question review in `research/reviews/<YYYY-MM>-monthly-review.md`,
separating what was known then from what became known later.

## 8. Data-source hierarchy

Tier 1 SEC / IR → tier 2 official macro → tier 3 Alpha Vantage / exchange →
tier 4 yfinance / aggregators. Lower tiers never override higher tiers.
Details: `docs/data-source-policy.md`.

## 9. Valuation philosophy

Five separate outputs: (1) model valuation (forward DCF, earnings method,
scenarios), (2) market-implied expectations (reverse DCF as a primary decision
tool), (3) valuation map derived from model values, (4) earnings / revenue
catch-up scenarios, (5) investment action as an evidence-based judgment.
No default "forward DCF × 80–90% = buy range". WATCH never means "wait for the
stock to fall to X". Policy: `docs/recommendation-policy.md`.

## 10. Expectation Gap

Per metric, compare market-implied assumptions (solved from price) with the
internal base and bull cases: at/below base, above base within bull, or above
bull; then track whether the gap is widening, stable or narrowing between
reviews (`research_state.py expectation-gap`). It is not collapsed into one
score. Example (AAPL, 2026-10-11): implied ~14.8% ten-year growth vs 8% base and
12% bull → above the bull case. PL: not quantified because a unique reverse DCF
could not be supported; recorded qualitatively.

## 11. NotebookLM (optional)

Reading and Q&A layer only; the repo is canonical. `docs/notebooklm-optional-workflow.md`.

## 12. TradingView (optional)

`research-monitor` can emit alert text or Pine snippets from
`monitoring/rules.yaml` price levels. Alerts mean "reassess", never "trade".

## 13. Codex / Claude coexistence

Same `research/`, `scripts/`, `docs/`, skills. Codex enters via `AGENTS.md` and
`.agents/skills/` symlinks; Claude via `CLAUDE.md`, `.claude/skills/` and
`.claude/commands/`. `docs/dual-codex-claude-usage.md`.

## 14. Example commands

```text
/watch-stock PL
/update-stock PL
/init-stock PLTR
/deep-stock AAPL
/monthly-research
```

```bash
uv run --project .claude/skills/finance-skill/scripts python scripts/price_reaction.py fetch PL
python3 scripts/research_state.py status PL
python3 scripts/research_state.py change-report AAPL
python3 scripts/research_state.py check-rules PL
python3 scripts/research_state.py catch-up PL
python3 scripts/research_state.py expectation-gap AAPL
python3 scripts/price_reaction.py analyze PL research/PL/market/events.csv --write
python3 -m unittest discover -s tests
```

## 15. Level 3 implementation (2026-10-13)

The engine below turns the state containers into a continuously accumulating
research record. Every script is local-first; network calls are limited to SEC
(finance-skill client, `.env` user agent) and price refreshes.

| Capability | Script | Output (`research/<TICKER>/…`) |
|---|---|---|
| Baseline builder | `build_fundamental_history.py` | `financials/history.json`, `coverage.json`, merged `historical.csv` |
| Assumption vs history | `assumption_history_check.py` | `valuation/assumption-check.{json,md}` |
| Management history | `build_management_history.py` | `management/statements.json`, `guidance.json`, `reported-kpis.json`, `changes.md`, `market/events.csv` |
| Promise lifecycle | `build_management_history.py` | `management/promises.json` |
| State snapshots + diff | `state_diff.py`, `research_state.py snapshot-state / change-report` | `snapshots/<date>.json`, `reports/<date>-change-report.md` |
| Valuation history | `build_valuation_history.py` | `valuation/historical-multiples.csv`, `historical-percentiles.json`, `market/fundamental-price-timeline.csv` |
| Expectation-gap history | `research_state.py record-gap` | `valuation/expectation-gap-history.csv` |
| Benchmark-adjusted reactions | `price_reaction.py analyze` / `fetch-benchmark` | `market/event-reactions.csv`, `research/benchmarks/SPY/prices.csv` |
| INIT / UPDATE | `research_pipeline.py init|update` | everything above + baseline / change report |
| Monthly review | `monthly_research_review.py` | `research/reviews/YYYY-MM-monthly-review.md` |
| Past state without hindsight | `backfill_state_snapshots.py` | `snapshots/<date>.json` (`retrospective: true` or from git) |

**Baseline builder.** A mapping layer lists candidate us-gaap tags per metric
(e.g. revenue: `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`,
`SalesRevenueNet`); the tag used is stored per period and a fallback is flagged.
Only 10-K / 10-Q (and amendments) count; duplicates resolve to the latest filed
fact (amendments and restated comparatives win); an `as_of` cutoff hides later
filings. Durations are classified by length so YTD values are never stored as
quarters; a standalone quarter is derived (YTD minus prior YTD, or cumulative
minus contiguous standalone quarters, same fiscal-year start) only when valid,
with the derivation recorded. Missing values stay null; nothing is zero-filled
or interpolated. Company KPIs (backlog, ARR, bookings, units, subscribers) are
filled only from a configured extension tag (`financials/tag-overrides.json`).
On AAPL it reproduces all values of the AAPL-specific `extract_aapl.py`
(kept, not deleted).

**Management history.** EX-99.1 earnings releases (8-K Item 2.02) are quoted
verbatim by topic (demand, customers, backlog/RPO, guidance, capex, margins,
product launch, customer qualification, constraints, cash flow, dilution); the
Outlook section is parsed into guidance ranges; `changes.md` compares guidance
raised / maintained / lowered and wording per topic over up to eight quarters.
Wording changes are labelled low-confidence heuristics, never fundamentals.

**Promise lifecycle.** Each guided metric becomes a promise (`pending`); once the
period is reported it is resolved against SEC actuals (revenue, capex, GAAP
margin) or company-reported non-GAAP figures (`delivered`,
`partially_delivered`, `missed`; capex is judged as a spending plan, under or
over), or `superseded` by later guidance. Counts carry a caveat; no credibility
score.

**State diff.** A snapshot freezes financials (latest quarter, TTM), management
(guidance, tone, promises), thesis (status + evidence fingerprint), valuation
(price, scenarios, zone, historical percentiles), expectation gap, rule states,
action / confidence and catalysts. `change-report` diffs the last two snapshots
across Financials, Management, Promises, Thesis, Valuation, Expectation gap and
Monitoring; thesis transitions use an explicit mapping (e.g. supported →
improving is neutral). Monitoring evaluates fundamental, market (price crossed a
reassessment level since the last reviewed price) and thesis-invalidation rules;
a trigger only means REASSESS.

**Valuation history.** Month-end and pre/post-earnings price × cover-page shares,
EV = market cap + debt − cash/investments, TTM revenue / EBIT / net income /
FCF from facts filed on or before each date (no look-ahead). EV/Sales,
EV/EBIT, P/E, P/FCF (null when not meaningful) and 1Y / 3Y / since-listing
percentiles, flagged when data is thin. The fundamental-price timeline aligns
each earnings release with price before / after, SPY-adjusted moves and the
quarter's fundamentals.

**Monthly review.** Compares each company's latest snapshot with its last one
before the month: thesis moves, gap widening / narrowing, promises, newly
triggered rules; High / Medium / Low priority by transparent rules; five tasks.

**Level assessment (2026-10-13): LEVEL 3** — generic baseline works (PL, AAPL,
RKLB), PL has multi-period state (2 retrospective + 3 recorded snapshots), UPDATE
produces a multi-domain diff, valuation / expectation-gap / thesis / promise
histories persist, and tests pass. Not LEVEL 4: thesis judgment and long-form
reports still need an analyst, management extraction is heuristic, transcripts
and company KPIs outside XBRL are not automated.
