---
description: Refresh prices, then show thesis, monitoring rules, next catalysts and reassessment triggers
argument-hint: TICKER
---
Use the equity-research-orchestrator skill, WATCH intent, for ticker $ARGUMENTS.
First refresh prices with
`uv run --project .claude/skills/finance-skill/scripts python scripts/price_reaction.py fetch $ARGUMENTS`,
then run `python3 scripts/research_state.py status $ARGUMENTS` and compare
against the latest price. No other network calls unless needed.
