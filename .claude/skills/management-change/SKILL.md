---
name: management-change
description: Track how a US company's management commentary and promises change across roughly the last eight quarters, and maintain the persistent promise tracker. Use when updating a researched company, when asked how management's wording on demand, backlog/RPO, capacity, capex, margins, guidance, cash flow, dilution or strategy has changed, or whether management delivered on prior guidance.
---

# Management Change and Promise Tracker

Files: `research/<TICKER>/management/statements.json`, `promises.json`, `changes.md`.
Sources in priority order: SEC 8-K Item 2.02 exhibits, 10-Q/10-K MD&A, issuer
earnings materials and transcripts published by the issuer. Use `finance-skill`
(`sec_edgar.py`) to list filings; never quote from memory.

## Statement records

Append one record per period × topic (do not rewrite prior periods):

```json
{"period": "Q2 FY2027", "topic": "backlog / RPO", "statement": "...",
 "verbatim": true, "source": "<URL>", "date": "2026-09-03",
 "guidance": "FY2027", "classification": "Fact",
 "interpretation": "...", "evidence_strength": "primary filing"}
```

`verbatim: true` only when `statement` is an exact quotation from the source;
otherwise it is a paraphrase and must say so. Topics: demand, customer ordering,
backlog / RPO, capacity, capex, gross margin, operating margin, product launches,
customer qualification, constraints, guidance, cash flow, dilution, strategic
priorities.

## Wording-change output (`changes.md`)

For each topic with at least two periods, a table with columns:
**Fact** (reported figure) | **Exact statement** (quote + source) |
**Change in wording** (prior → current) | **Interpretation** | **Evidence strength**.

- A tone change is a wording change, not proof of business deterioration. Pair
  it with reported numbers before it can move a thesis component.
- Note dropped topics (something management stopped mentioning) separately.
- With fewer than two periods, record the baseline and say no comparison exists.

## Promise tracker (`promises.json`)

Schema: `promise_id`, `topic`, `statement_date`, `management_claim`,
`target_date`, `expected_result`, `status` (pending | delivered |
partially_delivered | missed | superseded), `source`, `evidence[]`, `last_checked`.

- Only quantifiable or dated commitments (guidance ranges, launch dates,
  margin targets). Update status when the period is reported; cite the filing.
- A revised guidance range supersedes the earlier one (`superseded`), it is not a miss.
- Do not compute a credibility percentage unless the denominator is meaningful,
  claims are comparable, and the method is disclosed. Label any score heuristic.

Hand thesis-relevant changes to `thesis-monitor`; never change thesis status here.
