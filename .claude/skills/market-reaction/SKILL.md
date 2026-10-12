---
name: market-reaction
description: Analyze US stock price and volume reactions around earnings, SEC filings, 8-K guidance changes and other thesis-relevant events (gaps, volume anomalies, event-window returns, post-event drift, drawdowns). Use when asked how the market reacted to an event or whether price action confirms or contradicts the research thesis. Replaces the Taiwan FinMind workflow for US equities.
---

# Market Reaction Analyzer

Tool: `scripts/price_reaction.py` (stdlib; reads local CSVs).

- Prices: `research/<TICKER>/market/prices.csv`
  (`date,open,high,low,close,volume,source,retrieved_at`).
  Always refresh before analyzing (network; Alpha Vantage compact for recent
  sessions, yfinance backfill for older dates, today's open session stored
  separately in `market/latest-quote.json`):
  `uv run --project .claude/skills/finance-skill/scripts python scripts/price_reaction.py fetch TICKER`
- Events CSV (`market/events.csv`): `event_date,event_type,description,source,timing`
  (`timing: amc` moves t0 to the next session; unverified timing stays `unknown`), built from SEC filing
  dates (`evidence/sources.json`, `finance-skill` submissions), earnings 8-K
  dates and guidance changes.
- Run: `python3 scripts/price_reaction.py analyze TICKER events.csv [--write]`
  → `market/event-reactions.csv`.

Measures per event (t0 = first session on/after the event): overnight gap,
day return, volume vs 20-session median, return t-1→t+1, drift t+2→t+20,
max drawdown within 20 sessions. Flags: |gap| ≥ 3%, volume ≥ 2× median.

## Reporting rules

- Two separate columns: **Observation** (the numbers) and **Interpretation**
  (analyst, with evidence). The tool never fills Interpretation.
- Do not infer "smart money", accumulation or insider knowledge from volume.
- A drawdown after an event is a prompt to check the thesis, not proof the thesis
  broke; route conclusions to `thesis-monitor` with filing evidence.
- Note confounders (market-wide moves, index events, other same-day news) when
  known; unadjusted returns are not abnormal returns unless a benchmark is used.
