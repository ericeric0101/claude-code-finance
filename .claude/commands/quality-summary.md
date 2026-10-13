---
description: Generate the monthly Research OS quality summary
argument-hint: "[YYYY-MM]"
---
Run `python3 scripts/quality_summary.py --month $ARGUMENTS` (default: current month) and summarize
research/quality/summaries/YYYY-MM-quality-summary.md in Traditional Chinese (繁體中文): coverage,
false positives / negatives, priority agreement, extraction and interpretation errors, research
value, top corrections, weakest module and next month's actions. Ratios with n < 5 are
insufficient_sample — do not turn them into percentages. Quality metrics never change a company's
thesis or priority, and never use later returns.
