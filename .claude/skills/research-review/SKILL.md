---
name: research-review
description: Run the monthly review across every company with research state in research/<TICKER>/ — what new information changed prior judgments, which theses strengthened or weakened, valuation and expectation changes, promises delivered or missed, research priorities and next month's tasks. Use for /monthly-research or any request to review the whole watchlist.
---

# Monthly Research Review

1. `python3 scripts/research_state.py list` → tracked tickers.
2. For each: refresh prices (`price_reaction.py fetch`), then `status`,
   `check-rules`, `change-report`. Run an
   UPDATE via `equity-research-orchestrator` first only for companies with new
   filings since their `as_of` (check SEC submissions dates; skip API calls when
   nothing new was filed).
3. `python3 scripts/monthly_research_review.py [--month YYYY-MM]` writes
   `research/reviews/<YYYY-MM>-monthly-review.md` from state snapshots (rule-based
   High / Medium / Low priority; no price-outcome grading). Add commentary on top.

## Required sections

Write the review in Traditional Chinese (繁體中文); tickers, field names and code
identifiers may stay English.

1. New information that changed prior judgments (cite source and date).
2. Theses that strengthened.
3. Theses that weakened.
4. Components that remain unsupported (`uncertain` with no new evidence).
5. Valuations that became more or less demanding (price vs map, expectation-gap direction).
6. Management promises delivered / partially delivered / missed / superseded.
7. Companies deserving higher research priority, and why.
8. Companies that can be deprioritized, and why.
9. Previous judgments that were incomplete.
10. The five most important research tasks for next month.

## Hindsight discipline

For each judgment, separate **what was known at the prior `as_of`** (from
`thesis/history.json`, dated reports and git history) from **what became known
later**. A judgment that was reasonable on available evidence is "incomplete",
not "wrong". Price moves alone do not count as information about fundamentals.
Priorities are research priorities, not portfolio actions.
