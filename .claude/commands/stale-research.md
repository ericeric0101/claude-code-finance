---
description: Find stale research (old reviews, unabsorbed filings, stale valuation prices, past-due catalysts)
---
Use the equity-research-orchestrator skill, STALE-CHECK intent (Level 4).
Run `python3 scripts/research_command_center.py stale` (thresholds in
config/research-policy.yaml, per research_role). Report in Traditional Chinese (繁體中文)
which companies are stale, why, and the workflow that would refresh them (usually
/update-stock TICKER when a new 10-Q / 10-K is not in state).
