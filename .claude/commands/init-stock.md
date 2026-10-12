---
description: Initialize persistent research state for a US ticker
argument-hint: TICKER
---
Use the equity-research-orchestrator skill, INIT intent, for ticker $ARGUMENTS.
Run `python3 scripts/research_pipeline.py init $ARGUMENTS --cik <verified CIK>` so the
baseline has SEC history, prices, management, drafts and a snapshot (never an empty
shell), then review the auto-drafts. Never overwrite existing analyst state.
