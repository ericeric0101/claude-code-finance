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

`status` → list filings newer than `as_of` (stop if none) → management-change →
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
python3 scripts/research_state.py status PL
python3 scripts/research_state.py change-report AAPL
python3 scripts/research_state.py check-rules PL
python3 scripts/research_state.py catch-up PL
python3 scripts/research_state.py expectation-gap AAPL
python3 scripts/price_reaction.py analyze PL events.csv
python3 -m unittest discover -s tests
```
