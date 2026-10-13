---
description: Review pending Research OS quality events, record corrections or a missed event
argument-hint: "[quality_event_id | missed]"
---
Research OS quality evaluation layer (docs/research-os-quality-framework.md).
1. With no argument: run `python3 scripts/quality_review.py list --status pending` and show the
   `required` (HIGH priority) items first, then `spot_check` / `sample`.
2. With a quality_event_id: run `python3 scripts/quality_review.py show <id>`, read the referenced
   state files, and ask the user for the relevant review fields only (true / false / unknown /
   not_applicable, reviewed priority / classification, extraction errors, research value, notes).
   Record their answers with `python3 scripts/quality_review.py review <id> ...`; a disagreement
   needs `--reason`. Never fill a human judgment yourself.
3. With `missed`: collect ticker, event_date, event_type, source, why_material, expected_workflow
   and run `python3 scripts/quality_review.py add-missed-event ...`.
Grade process, evidence and reasoning available at the time — never later price moves (hindsight
bias). Corrections are recorded only; never edit rules or research state from them.
Reply in Traditional Chinese (繁體中文).
