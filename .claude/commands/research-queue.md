---
description: Show the prioritized research queue — which company to research first and why
---
Use the equity-research-orchestrator skill, RESEARCH-QUEUE / PRIORITIZE intents (Level 4).
Run `python3 scripts/research_command_center.py prioritize` and then
`python3 scripts/research_command_center.py queue`. Explain in Traditional Chinese
(繁體中文) the order of companies, the explainable priority reasons, and for each open
item the workflow it needs (A → /update-stock TICKER; B → the owning skill; C →
market-reaction only, no full DCF unless state changed; D → log only). Mark items handled
with `python3 scripts/research_queue.py set EVENT_ID completed|dismissed --note "..."`.
Priority means "research first", never a trade.
