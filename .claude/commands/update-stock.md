---
description: Update a researched ticker with only new evidence and produce a change report
argument-hint: TICKER
---
Use the equity-research-orchestrator skill, UPDATE intent, for ticker $ARGUMENTS.
Run `python3 scripts/research_pipeline.py update $ARGUMENTS --cik <CIK>` (only
evidence newer than the stored state); the primary output is the
"What Changed Since Last Review" report it writes to research/<T>/reports/.
Write the report prose in Traditional Chinese (繁體中文); tickers, field names
and code identifiers may stay English.
