---
name: thesis-monitor
description: Maintain each researched company's investment thesis components (importance, status, evidence, next check, invalidation condition) in research/<TICKER>/thesis/. Use when updating a company, when asked whether the thesis still holds, which thesis parts strengthened or weakened, or whether an invalidation condition has occurred.
---

# Thesis Monitor

Authoritative file: `research/<TICKER>/thesis/current.yaml`. History:
`thesis/history.json` (upserted by `as_of`). Observable conditions:
`thesis/invalidation-rules.yaml`.

Each component:

```yaml
components:
  sovereign_demand:
    importance: high          # high | medium | low
    status: supported         # supported | improving | uncertain | weakening | invalidated
    evidence: ["Fact: ... (source)", "Calculation: ..."]
    last_updated: '2026-10-11'
    next_check: Q3 FY2027 10-Q
    invalidation_condition: ...
```

Use only these five statuses. Something "unproven" is `uncertain`; a risk that is
playing out (e.g. dilution) is `weakening` on the relevant value-creation
component.

## Update procedure

1. Read `current.yaml`, `invalidation-rules.yaml`, and new evidence from
   `management-change`, filings and `financials/latest.json`.
2. For each component decide: no new evidence → keep status, refresh
   `next_check` only; new evidence → change status with the cited evidence line
   and update `last_updated`.
3. Mark invalidation rules `triggered` only when the observable condition is met
   in reported data; record whether it already happened.
4. Update `action` / `valuation_confidence` only through the
   `my-equity-research` decision layer.
5. `python3 scripts/research_state.py snapshot TICKER --note "<what changed>"`
   (validates fields; same-date snapshots replace, older snapshots are kept).

## Guardrails

- Status changes require evidence. A price move alone never changes status.
- Separate what was known at the prior `as_of` from what became known later.
- Never delete components; retire one by setting a note and keeping history.
