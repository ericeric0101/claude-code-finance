---
description: Watchlist command-center dashboard (priority, thesis trend, valuation, expectation gap, triggers, catalysts)
---
Use the equity-research-orchestrator skill, COMMAND-CENTER intent (Level 4).
Refresh prices for each watchlist ticker first, then run
`python3 scripts/research_command_center.py dashboard` and summarize
research/dashboard/current.md in Traditional Chinese (繁體中文): the table, which thesis
improved / deteriorated most, whose expectation gap narrowed, whose valuation became
cheaper versus its own model, which rose without fundamentals following, which research is
stale, and the explainable research confidence. Never compare raw EV/Sales across sectors;
nothing here is a buy / sell instruction.
