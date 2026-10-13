# Research OS Quality Summary（2026-10）

> 評估的是研究流程品質（偵測、分類、優先順序、抽取、解讀、研究價值），不是報酬預測。不讀取股價；比率分母 < 5 時顯示 insufficient_sample。auto 建立的事件預設 pending，未經人工確認。

## Coverage
- Events processed：8（系統事件 8；來源 {'seed': 8}）
- Events reviewed：0
- Pending reviews：8（其中 required 3）
- 依 workflow：{'update-stock': 2, 'targeted-update': 1, 'market-reaction': 1, 'scan-research': 2, 'init-stock': 1, 'monthly-research': 1}

## Event Detection
- Correct detections：0（已 review 0）
- False positives：0
- False negatives：0
- Missed events（人工補登）：0
- Event precision：insufficient_sample（0/0，n < 5）
- Event recall：insufficient_sample（0/0，n < 5）

## Classification
- correct：0
- too_high：0
- too_low：0
- wrong_type：0

## Priority
- HIGH reviewed：0
- MEDIUM reviewed：0
- LOW reviewed：0
- Priority agreement：insufficient_sample（0/0，n < 5）
- Priority disagreement rate：insufficient_sample（0/0，n < 5）
- 分歧方向：無

## Extraction
- Guidance errors：0
- KPI errors：0
- Management extraction errors：0
- Promise errors：0
- Metric-definition errors：0
- 錯誤類型：無
- Guidance extraction accuracy：insufficient_sample（0/0，n < 5）

## Interpretation
- Overinterpretation：0
- Underinterpretation：0
- Unsupported inference：0
- Correct / reasonable_but_uncertain：0 / 0

## Research Value
- HIGH：0
- MEDIUM：0
- LOW：0
- NONE：0

## Manual Corrections
- Total：0（永久保存在 research/quality/corrections.jsonl；不會自動改規則）
- Top correction categories：無

## Module Quality

| Module | Reviewed | Correct | Errors | Extraction errors | Corrections | Agreement |
|---|---|---|---|---|---|---|
| event_detector | 0 | 0 | 0 | 0 | 0 | insufficient_sample（0/0，n < 5） |
| event_classifier | 0 | 0 | 0 | 0 | 0 | insufficient_sample（0/0，n < 5） |
| priority_engine | 0 | 0 | 0 | 0 | 0 | insufficient_sample（0/0，n < 5） |
| kpi_registry | 0 | 0 | 0 | 0 | 0 | insufficient_sample（0/0，n < 5） |
| management_diff | 0 | 0 | 0 | 0 | 0 | insufficient_sample（0/0，n < 5） |
| guidance_tracker | 0 | 0 | 0 | 0 | 0 | insufficient_sample（0/0，n < 5） |
| promise_tracker | 0 | 0 | 0 | 0 | 0 | insufficient_sample（0/0，n < 5） |
| thesis_monitor | 0 | 0 | 0 | 0 | 0 | insufficient_sample（0/0，n < 5） |
| valuation_monitor | 0 | 0 | 0 | 0 | 0 | insufficient_sample（0/0，n < 5） |
| monitoring_rules | 0 | 0 | 0 | 0 | 0 | insufficient_sample（0/0，n < 5） |
| monthly_review | 0 | 0 | 0 | 0 | 0 | insufficient_sample（0/0，n < 5） |

## Ticker Quality

| Ticker | Events | Reviewed | Pending | FP | FN | Events with issues | Extraction errors by module | Corrections |
|---|---|---|---|---|---|---|---|---|
| AAPL | 1 | 0 | 1 | 0 | 0 | 0 | — | 0 |
| ALL | 1 | 0 | 1 | 0 | 0 | 0 | — | 0 |
| PL | 4 | 0 | 4 | 0 | 0 | 0 | — | 0 |
| RKLB | 2 | 0 | 2 | 0 | 0 | 0 | — | 0 |

## Most Problematic Tickers
- 尚無（沒有已 review 的錯誤）

## Most Reliable Modules
- insufficient_sample（沒有模組達到 n ≥ 5）

## Weakest Modules
- insufficient_sample（沒有模組達到 n ≥ 5）

## Actions for Next Month
1. 完成 3 筆 HIGH / required 的待 review 事件（QE-20261013-PL-7f82c17e, QE-20261013-PL-8075b151, QE-20261013-AAPL-8f051ca8）
2. 目前尚無人工 review；先從 required 事件開始，累積樣本後 metrics 才有意義

## Hindsight-bias rule
- 不用股價後來的漲跌評斷 thesis、valuation 或 extraction；WATCH 後來上漲不算 failure，BUY 後來下跌不算 extraction failure。
- 只評估當時可得的證據、流程與推理。
