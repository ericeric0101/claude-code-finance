---
description: Monthly review across all tracked companies
---
Use the research-review skill (via equity-research-orchestrator, MONTHLY intent)
for every ticker listed by `python3 scripts/research_state.py list`:
refresh prices, run `python3 scripts/research_command_center.py scan --refresh --skip-prices`
(Level 4 queue, priorities, calendar, staleness), then
`python3 scripts/monthly_research_review.py` (writes
research/reviews/YYYY-MM-monthly-review.md: Level 3 sections 1-11 plus Level 4
command-center sections 12-22), then add analyst commentary.
Write the report prose in Traditional Chinese (繁體中文); tickers, field names
and code identifiers may stay English.
