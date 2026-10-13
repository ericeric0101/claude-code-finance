---
description: Scan the watchlist for new research events, classify them and update the research queue
argument-hint: "[TICKER ...]"
---
Use the equity-research-orchestrator skill, SCAN-EVENTS intent (Level 4), for the
watchlist in config/watchlist.yaml (or only $ARGUMENTS if given).
1. Refresh prices first for each ticker (`uv run --project .claude/skills/finance-skill/scripts python scripts/price_reaction.py fetch <TICKER>`).
2. Run `python3 scripts/research_command_center.py scan --refresh --skip-prices` (add `--tickers $ARGUMENTS` when given).
   This detects only events newer than each ticker's scan-state, classifies them
   (A full update / B targeted / C market reaction only / D informational), updates
   research/queue/current.json, recomputes priorities, the catalyst calendar and staleness.
3. Report in Traditional Chinese (繁體中文): new events per ticker, their category and
   required workflow, and the resulting priority order. Triggers mean REASSESS; never
   present anything as a buy / sell instruction. Do not run /update-stock automatically.
