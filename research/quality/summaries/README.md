# Research OS quality summaries

`YYYY-MM-quality-summary.md`（+ `.json`）由 `python3 scripts/quality_summary.py --month YYYY-MM` 產生，
`/monthly-research` 也會自動產生當月份。只讀 `../quality-events.jsonl` 與 `../corrections.jsonl`，不讀股價。
分母 < 5 的比率顯示 `insufficient_sample`。定義見 `docs/research-os-quality-framework.md`。
