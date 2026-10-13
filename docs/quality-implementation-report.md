# Research OS Quality Log 實作報告（2026-10-13）

分支 `claude/project-thread-iqcpc8`，建在 Level 4 commit `18b7f53` 之上，只 commit、未 push。
實作前確認：工作區乾淨、`.env` 未被 git 追蹤、75 個測試全部通過；研究中的公司為 PL、RKLB、AAPL（PLTR 只有舊報告，沒有 state）。

## 1. Quality framework 是否完成

完成。12 項完成條件逐一對應：

| # | 條件 | 狀態 | 證據 |
|---|---|---|---|
| 1 | quality events 自動產生 | ✓ | scan / update / init / monthly 掛接；`AutoCreateTests` |
| 2 | human review 可以修改 | ✓ | `quality_review.py review`；`test_human_review_update` |
| 3 | missed events 可手動加入 | ✓ | `add-missed-event`；`MissedEventTests` |
| 4 | corrections 永久保存 | ✓ | `corrections.jsonl` append-only；`test_correction_history` |
| 5 | FP / FN 可追 | ✓ | `test_false_positive_handling`、missed event 測試 |
| 6 | module-level 統計 | ✓ | summary「Module Quality」；`test_module_attribution` |
| 7 | ticker-level 統計 | ✓ | summary「Ticker Quality」；`test_ticker_attribution` |
| 8 | monthly quality summary | ✓ | `research/quality/summaries/2026-10-quality-summary.md` |
| 9 | dashboard 簡化品質 | ✓ | `research/dashboard/current.md`「Research OS Quality」 |
| 10 | hindsight bias rules | ✓ | `HindsightBiasError`、不讀價格；`test_no_hindsight_return_scoring` |
| 11 | Level 4 tests 全過 | ✓ | 原 75 個測試不變，全部通過 |
| 12 | sample events 建立且 pending | ✓ | 8 筆，全部 `review_status=pending` |

## 2. 新增 / 修改檔案

新增：
- `scripts/quality_log.py`：schema、驗證、建立、review、correction、missed event、CSV 產生
- `scripts/quality_review.py`：CLI（list / show / review / correct / add-missed-event / summary / seed）
- `scripts/quality_summary.py`：月度彙總與 metrics
- `research/quality/quality-events.jsonl`、`quality-log.csv`、`corrections.jsonl`、`summaries/README.md`、`reviews/README.md`
- `research/quality/summaries/2026-10-quality-summary.{md,json}`
- `docs/research-os-quality-framework.md`
- `.claude/commands/quality-review.md`、`.claude/commands/quality-summary.md`
- `tests/test_quality.py`（16 個測試）

修改（只加掛接點，沒有重寫）：
- `scripts/research_pipeline.py`：init / update 結束時建立 pending 品質事件（失敗也不會中斷 pipeline）
- `scripts/research_command_center.py`：scan 結束時為每個新 queue item 建品質事件
- `scripts/monthly_research_review.py`：第 23 段 Research OS Quality，並產生當月 summary
- `scripts/research_dashboard.py`：精簡品質區塊
- `docs/level4-operating-guide.md`、`CLAUDE.md`
- 重新產生 `research/dashboard/current.{md,json}` 與 `research/reviews/2026-10-monthly-review.md`（diff 只多了品質區段）

沒有修改任何 research state schema、thesis、valuation、rules 或 queue。

## 3. quality-log schema

`quality-log.csv` 包含要求的全部欄位：`date, ticker, event_id, event_type, workflow, source_reference,
event_detected_correctly, event_classification_correct, priority_correct, guidance_extracted_correctly,
management_change_correct, kpi_extraction_correct, promise_resolution_correct, thesis_update_useful,
valuation_update_useful, monitoring_trigger_correct, false_positive, false_negative, missed_information,
manual_correction_required, manual_correction_type, research_value, confidence, review_status, reviewed_by,
reviewed_at, notes`。

另加：最前面的 `quality_event_id`；最後面的 `origin, review_requirement, system_classification,
classification_verdict, system_priority, reviewed_priority, interpretation_verdict, monthly_review_useful,
extraction_errors, corrections`。

值一律是 `true` / `false` / `unknown` / `not_applicable`，不用空字串，schema 驗證會拒絕空字串。
`quality-events.jsonl` 是 source of truth，結構是 system_output / human_review / corrections / review_history / references；
CSV 每次寫入都由 JSONL 重新產生。只存 metadata 與檔案引用，不存 filing 或報告內容。

## 4. 哪些 workflow 會自動建立 quality event

| Workflow | 建立方式 | 系統自動填的內容 |
|---|---|---|
| `/scan-research` | 每個新 queue item 一筆；沒有新事件時一筆 `scan_run` | 分類、priority、severity、required_workflow、觸發規則 |
| `/update-stock` | 每次一筆 | 新 filing 數、最新季度、thesis 是否改變、guidance counts、觸發規則、action、完成的 queue 數、輸出檔 |
| `/init-stock` | 每次一筆 | 歷史年度 / 季度數、management statements、guidance counts、draft_auto、觸發規則 |
| `/monthly-research` | 每月一筆 | 檢視公司、各公司 priority、輸出檔 |

全部都是 `review_status=pending`，人工判斷欄位都是 `unknown`。就算呼叫端在 system output 裡放了 `priority_correct`
或 `thesis_update_useful`，也會被丟棄。HIGH priority 事件標 `required`，MEDIUM 標 `spot_check`，LOW 標 `sample`。

## 5. 如何人工 review

```bash
python3 scripts/quality_review.py list --status pending
python3 scripts/quality_review.py list --status pending --requirement required
python3 scripts/quality_review.py review <id>          # 在終端機會只問該事件的相關欄位
python3 scripts/quality_review.py review <id> --event-detected-correctly true \
  --reviewed-priority MEDIUM --reason "routine contract extension, no thesis impact" --research-value MEDIUM
```

也可以用 `--set field=value` 或 `--extraction-error guidance_tracker:wrong_period`，或在 Claude Code 用 `/quality-review`。
只需要填相關欄位；沒填的仍是 `unknown`，不會計入 metrics。

## 6. 如何記錄 missed event

```bash
python3 scripts/quality_review.py add-missed-event --ticker PL --event-date 2026-10-01 \
  --event-type product_launch --source "<URL>" --why-material "..." --expected-workflow targeted-update
```

缺參數時在終端機會互動詢問。這會建立 `origin=manual_missed`、`false_negative=true`、`system_output.detected=false` 的事件，
並寫一筆 event_detector correction。`event_date` 不可晚於登錄日。

## 7. 如何保存 correction

- review 時 reviewed priority 或 classification 和系統不同，或指定 extraction error，會自動寫 correction，而且必須附 `--reason`。
- 也可以直接寫：`python3 scripts/quality_review.py correct <id> --field priority --reviewed-value MEDIUM --reason "..."`。
- 每筆記錄 `field, system_value, reviewed_value, before, after, reason, module, ticker, reviewer, timestamp`，
  append 到 `research/quality/corrections.jsonl`，同時也存在該事件的 `corrections`，之後的 review 不會把它蓋掉。
- `applied_to_rules: false`：這是 feedback dataset，程式不會自動修改規則。

## 8. summary 有哪些 metrics

Coverage（processed / reviewed / pending / required pending）、Event Detection（正確偵測、FP、FN、漏抓、
**precision**、**recall**）、Classification（correct / too_high / too_low / wrong_type）、Priority（依 reviewed priority 分的 HIGH / MEDIUM / LOW、
**agreement**、**disagreement rate**、分歧方向）、Extraction（guidance / KPI / management / promise / metric-definition 錯誤、
錯誤類型、**guidance extraction accuracy**）、Interpretation（over / under / unsupported）、Research Value（HIGH / MEDIUM / LOW / NONE）、
Manual Corrections（總數、top categories）、11 個模組的 Module Quality、Ticker Quality、Most Problematic Tickers、
Most Reliable / Weakest Modules、Actions for Next Month。

每個比率都會顯示分子 / 分母；分母 < 5 時顯示 `insufficient_sample`，不算百分比。樣本不足時，Weakest module 改用錯誤筆數排序，並註明不是比率。

## 9. 如何避免 hindsight bias

- `quality_log.py` 與 `quality_summary.py` 完全不讀價格資料。測試會修改 prices.csv，確認 summary 不受影響。
- review notes、missed_information、correction reason、why_material 若用「股價後來上漲 / 下跌」「returns since」
  「in hindsight」之類（中英文）來論證，會被 `HindsightBiasError` 拒絕。
- `forward_return`、`return_after`、`price_outcome`、`outcome_correct`、`hit_rate`、`pnl` 等欄位不允許出現。
- 漏抓事件必須是當時就可得的資訊（`event_date` ≤ 登錄日）。
- 文件明定：WATCH 後來上漲不算 failure；BUY 後來下跌不算 extraction failure。

## 10. dashboard 加了什麼

`research/dashboard/current.md` 新增「Research OS Quality」區塊，共 8 行：Reviewed events、Pending review（required 數）、
False positives、False negatives、Priority agreement（分子 / 分母，樣本不足時標 insufficient_sample）、Manual corrections、
Largest weakness，以及完整 summary 的指令。`current.json` 多了 `quality` 物件。區塊標明不影響 thesis 或 priority。

## 11. monthly review 加了什麼

`research/reviews/YYYY-MM-monthly-review.md` 新增獨立的「## 23. Research OS Quality」：reviewed / pending、FP / FN（含人工補登）、
priority disagreements、manual corrections、weakest module、next quality improvement，以及當月 summary 的路徑。
`/monthly-research` 會同時寫出 `research/quality/summaries/YYYY-MM-quality-summary.md`，並把這次 monthly run 記成一筆 pending 品質事件。

## 12. initial sample events

用 `python3 scripts/quality_review.py seed` 建立 8 筆，全部是 `pending`，沒有任何人工判斷：

| quality_event_id | Ticker | 事件 | 系統分類 / priority |
|---|---|---|---|
| QE-20261013-PL-7f82c17e | PL | Q2 FY2027 earnings（8-K 2.02，2026-09-03）→ update | A / HIGH（replay） |
| QE-20261013-PL-917e90b6 | PL | 德國聯邦衛星服務合約（2026-09-15） | B / MEDIUM（replay） |
| QE-20261013-PL-afb811a0 | PL | 2026-06-05 單日 −26% 價格事件 | C / MEDIUM（replay） |
| QE-20261013-PL-8075b151 | PL | dilution_yoy standing trigger（真實 queue item） | B / HIGH |
| QE-20261013-RKLB-8edd7cbb | RKLB | INIT baseline | — |
| QE-20261013-RKLB-62cc0759 | RKLB | Neutron 首飛延期（真實 queue item） | B / MEDIUM |
| QE-20261013-AAPL-8f051ca8 | AAPL | Q3 FY2026 earnings（8-K 2.02，2026-07-30）→ update | A / HIGH（replay） |
| QE-20261013-ALL-3f3e09db | ALL | 2026-10 monthly review | — |

標 replay 的事件早於第一次 Level 4 scan，所以它們的分類與 priority 是把真實的 classifier 和 priority engine 套在今天的 state 上算出來的
（`system_output.replay=true`），不是當時的系統輸出。目前有 3 筆 required 待 review。

## 13. tests 數量與結果

91 個測試全部通過（原 75 + 新 16）：`python3 -m unittest discover -s tests`。
新測試涵蓋要求的 15 項：schema、auto-create pending、human review、missed event、correction history、false positive、
false negative、summary aggregation、insufficient sample、module attribution、ticker attribution、no hindsight-return scoring、
Level 4 regression、monthly quality section、dashboard quality summary；另外多一個 scan / monthly 實際建立事件的整合測試。

## 14. Remaining limitations

- 目前 0 筆人工 review，所以所有比率都是 `insufficient_sample`。要先累積 review，metrics 才有意義。
- 5 筆 sample 的分類 / priority 是 replay 結果，不是當時真正的系統輸出。
- Recall 只能涵蓋使用者有補登的漏抓事件，沒被發現的漏抓本來就量不到。
- `/update-stock` 與 `/init-stock` 每次只建一筆事件，沒有拆到每個 guidance 項目；guidance 項目準確率要靠 reviewer 填
  `guidance_items_reviewed` / `guidance_items_correct`。
- Hindsight 偵測是規則式文字比對，可能漏掉換句話說的情況，也可能誤擋。被擋時改寫成流程或證據的論證即可。
- `quality-events.jsonl` 是整檔改寫（atomic write）；如果兩個 workflow 同時寫入，後寫的會蓋過先寫的。
  單人依序使用沒問題，corrections 則是 append-only。
- 有 `/quality-review`、`/quality-summary` 兩個 Claude command；Codex 端可以直接執行同樣的 Python 指令。

## 15. Commit

`Add Research OS quality evaluation framework`（單一 commit，包含本報告；hash 用 `git log -1 --oneline` 查看）。未 push。
