# Research OS Quality Framework（品質評估層）

## 目的

Research OS 正式使用後，需要持續知道它「做對了沒有」：事件有沒有抓到、分類與 priority 是否合理、
guidance / KPI / management 抽取是否正確、thesis 更新有沒有研究價值、哪裡需要人工修正，以及品質是否隨時間改善。

這一層是 Level 4 之上的**附加評估層**：

- 不改 research state schema，不建立另一套 research state，不重寫 pipeline。
- 只保存評估 metadata 與檔案引用（references），不複製 SEC filing 或報告內容。
- 人工修正只記錄（feedback dataset），**不會自動改規則**（`applied_to_rules: false`）。
- 品質指標放在獨立區段，**不影響任何公司的 thesis、action 或 research priority**。

## 檔案

| 檔案 | 內容 |
|---|---|
| `research/quality/quality-events.jsonl` | 機器可讀的評估事件（source of truth，每行一筆） |
| `research/quality/quality-log.csv` | 人看的摘要，每次寫入時由 JSONL 重新產生 |
| `research/quality/corrections.jsonl` | 人工修正，append-only，永久保存 |
| `research/quality/summaries/YYYY-MM-quality-summary.{md,json}` | 月度品質報告 |
| `research/quality/reviews/` | 選用的自由格式 review 筆記 |
| `scripts/quality_log.py` | schema、建立、review、correction、missed event |
| `scripts/quality_review.py` | CLI：list / show / review / correct / add-missed-event / summary / seed |
| `scripts/quality_summary.py` | 月度彙總與 metrics |

## Schema

### quality-events.jsonl（每筆）

```json
{
  "quality_event_id": "QE-20261013-PL-8075b151",
  "schema_version": 1,
  "date": "2026-10-13",
  "ticker": "PL",
  "event_id": "PL-2026-10-13-standing_trigger-12d16898",
  "event_type": "standing_trigger",
  "workflow": "scan-research",
  "origin": "auto | seed | manual_missed",
  "source_reference": "monitoring/rules.yaml / ...",
  "review_requirement": "required | spot_check | sample",
  "modules": ["event_detector", "event_classifier", "priority_engine", "monitoring_rules"],
  "system_output": {"detected": true, "classification": "B", "priority": "HIGH", "triggered_rules": ["dilution_yoy"],
                    "relevant_review_fields": ["event_detected_correctly", "priority_correct", "..."]},
  "human_review": {"event_detected_correctly": "unknown", "priority_correct": "unknown", "reviewed_priority": "unknown",
                   "classification_verdict": "unknown", "interpretation_verdict": "unknown",
                   "extraction_errors": [], "research_value": "unknown", "notes": ""},
  "review_status": "pending | in_review | reviewed | dismissed",
  "reviewed_by": null,
  "reviewed_at": null,
  "corrections": [],
  "review_history": [],
  "references": ["research/queue/current.json", "research/PL/monitoring/rules.yaml"]
}
```

值一律明確：`true` / `false` / `"unknown"`（尚未判斷）/ `"not_applicable"`。不使用空字串。

### quality-log.csv 欄位

必要欄位：`date, ticker, event_id, event_type, workflow, source_reference, event_detected_correctly,
event_classification_correct, priority_correct, guidance_extracted_correctly, management_change_correct,
kpi_extraction_correct, promise_resolution_correct, thesis_update_useful, valuation_update_useful,
monitoring_trigger_correct, false_positive, false_negative, missed_information, manual_correction_required,
manual_correction_type, research_value, confidence, review_status, reviewed_by, reviewed_at, notes`。

附加欄位（放在最前與最後）：`quality_event_id`、`origin, review_requirement, system_classification,
classification_verdict, system_priority, reviewed_priority, interpretation_verdict, monthly_review_useful,
extraction_errors, corrections`。

### corrections.jsonl（每筆）

```json
{"correction_id": "QC-…", "quality_event_id": "QE-…", "module": "priority_engine", "ticker": "PL",
 "field": "priority", "system_value": "HIGH", "reviewed_value": "MEDIUM", "before": "HIGH", "after": "MEDIUM",
 "reason": "routine contract extension, no thesis impact", "reviewer": "CK", "timestamp": "…",
 "applied_to_rules": false}
```

## 七個品質面向與對應欄位

| 面向 | 欄位 / 值 | 模組 |
|---|---|---|
| A. Event detection | `event_detected_correctly`、`false_positive`、`false_negative`（含人工補登漏抓） | event_detector |
| B. Classification | `classification_verdict`：correct / too_high / too_low / wrong_type / unknown；`reviewed_classification` | event_classifier |
| C. Priority | `system_output.priority`、`reviewed_priority`、`priority_correct` | priority_engine |
| D. Extraction | `guidance_extracted_correctly`、`kpi_extraction_correct`、`management_change_correct`、`promise_resolution_correct`；`extraction_errors`：missing / wrong_value / wrong_unit / wrong_period / wrong_metric_definition / duplicate / unsupported_inference | guidance_tracker、kpi_registry、management_diff、promise_tracker |
| E. Interpretation | `interpretation_verdict`：correct / reasonable_but_uncertain / overinterpreted / underinterpreted / unsupported；`interpretation_module` | management_diff（預設）、thesis_monitor 等 |
| F. Valuation / monitoring | `valuation_update_useful`、`monitoring_trigger_correct`（只看輸入、zone、gap、規則是否正確套用） | valuation_monitor、monitoring_rules |
| G. Research value | `research_value`：HIGH / MEDIUM / LOW / NONE | （跨模組） |

另有 `thesis_update_useful`（thesis_monitor）與 `monthly_review_useful`（monthly_review）。

## Review workflow

1. **自動建立（pending）**：以下 workflow 完成後會自動建立 quality event，`review_status = pending`：
   - `/scan-research`：每個新進 research queue 的事件一筆；沒有新事件時建立一筆 `scan_run`。
   - `/update-stock TICKER`：每次 UPDATE 一筆（新 filing 數、thesis 是否改變、guidance counts、觸發規則、action、輸出檔）。
   - `/init-stock TICKER`：每次 INIT 一筆（歷史年度 / 季度數、management statements、guidance counts、draft_auto）。
   - `/monthly-research`：每月一筆。

   系統只填 `system_output`（偵測到的事件、分類、priority、產出、guidance 數、觸發規則）。
   人工判斷欄位一律 `unknown`；就算呼叫端把 `priority_correct` 之類放進 system output 也會被丟棄。
   **auto-created ≠ auto-approved。**
2. **人工 review**：只填相關欄位（`system_output.relevant_review_fields` 會提示）。
3. **Review 優先順序**：HIGH priority → `required`（必 review）；MEDIUM → `spot_check`（抽查，thesis 有改變時要 review）；
   LOW → `sample`（抽樣）。每月：review 漏抓事件 + 看 summary。

```bash
python3 scripts/quality_review.py list --status pending
python3 scripts/quality_review.py list --status pending --requirement required
python3 scripts/quality_review.py show QE-20261013-PL-8075b151
python3 scripts/quality_review.py review QE-20261013-PL-8075b151 \
  --event-detected-correctly true --classification-verdict correct \
  --reviewed-priority MEDIUM --reason "dilution already priced into the thesis; REASSESS confirmed no change" \
  --research-value MEDIUM --reviewer CK
python3 scripts/quality_review.py review QE-… --set kpi_extraction_correct=false \
  --extraction-error kpi_registry:wrong_unit --reason "RPO reported in USD thousands"
```

在終端機不帶欄位執行 `review <id>`，會只詢問該事件的相關欄位。

## 如何加入人工修正

- `review` 時的 `--reviewed-priority` / `--reviewed-classification` 與系統不同，或 `--extraction-error`，會自動寫一筆 correction（必須給 `--reason`）。
- 其他欄位用 `correct`：

```bash
python3 scripts/quality_review.py correct QE-… --field priority --reviewed-value MEDIUM \
  --reason "routine contract extension, no thesis impact" --module priority_engine
```

Correction 同時 append 到 `corrections.jsonl` 與事件的 `corrections`，之後的 review 不會讓它消失。

## False positive / false negative

- **False positive**：系統偵測到、但經 review 判定不是需要研究的事件（不相關、重複、門檻誤觸）。
  記 `false_positive=true`（`event_detected_correctly` 自動視為 false）。
- **False negative**：重大事件系統完全沒抓到、使用者後來發現。用：

```bash
python3 scripts/quality_review.py add-missed-event --ticker PL --event-date 2026-10-01 \
  --event-type product_launch --source "https://investors.planet.com/…" \
  --why-material "Tanager-2 launch relevant to the hyperspectral thesis component" \
  --expected-workflow targeted-update
```

會建立 `origin=manual_missed`、`false_negative=true`、`system_output.detected=false` 的事件，並寫一筆 event_detector correction。
`event_date` 不能晚於今天（漏抓必須是當時就可得的資訊）。缺的參數在終端機會互動詢問。

## Metrics

全部是透明的計數與比率，分子 / 分母都會顯示；只計已判斷的值（`unknown`、`not_applicable` 不計）。

| Metric | 定義 |
|---|---|
| Event precision | 正確偵測的重大事件 / 已 review 的系統偵測事件 |
| Event recall | 正確偵測的重大事件 /（正確偵測 + 漏抓事件） |
| Priority agreement | reviewed priority 與系統一致的數量 / 已 review 的 priority |
| Priority disagreement rate | 1 − agreement（同樣顯示分子分母）；另列 system_too_high / system_too_low |
| Guidance extraction accuracy | 正確 guidance 項目 / 已 review guidance 項目（有 `guidance_items_reviewed` 時用項目數，否則用事件層級） |
| Module agreement | 模組判斷正確數 /（正確 + 錯誤 + extraction 錯誤） |

**分母 < 5 時不算百分比**，顯示 `insufficient_sample（分子/分母，n < 5）`。樣本不足時，「Weakest module」改用錯誤筆數排序並註明不是比率。

月報 `python3 scripts/quality_summary.py --month 2026-10` 產生
`research/quality/summaries/2026-10-quality-summary.md`，包含：Coverage、Event Detection、Classification、Priority、
Extraction、Interpretation、Research Value、Manual Corrections、Module Quality、Ticker Quality、Most Problematic Tickers、
Most Reliable Modules、Weakest Modules、Actions for Next Month。

模組：`event_detector, event_classifier, priority_engine, kpi_registry, management_diff, guidance_tracker,
promise_tracker, thesis_monitor, valuation_monitor, monitoring_rules, monthly_review`。
Ticker 層級可看出哪家公司 extraction 最容易錯、KPI mapping 不完整、guidance 最難追、semantic 解讀最不可靠。

## Hindsight bias rules（已實作）

- 品質評的是**當時可得**的證據、流程與推理，不是短期報酬預測。
- 禁止：用股價後來漲跌評 thesis 對錯、用未來結果倒推當時判斷、把 WATCH 後來上漲當 failure、把 BUY 後來下跌當 extraction failure。
- 實作：
  - `quality_log.py` / `quality_summary.py` 不讀任何價格資料（測試會確認改價格不影響 summary）。
  - review notes、missed_information、correction reason、missed event 的 why_material 若以「股價後來上漲 / 下跌、
    returns since…、in hindsight」等論證，會被 `HindsightBiasError` 拒絕。
  - `return_after`、`forward_return`、`price_outcome`、`outcome_correct`、`hit_rate`、`pnl` 等欄位不得出現在品質事件。
  - 漏抓事件的 `event_date` 不能晚於登錄日（`information_available_at = event_date`）。

## Monthly quality review

`/monthly-research` 會在月報加入獨立的「## 23. Research OS Quality」：reviewed events、pending、false positives、
false negatives、priority disagreements、manual corrections、weakest module、next quality improvement，
並同時寫出當月 quality summary。這一段明確標示不影響任何公司的 thesis。

`research/dashboard/current.md` 加入精簡的「Research OS Quality」區塊（reviewed、pending、FP、FN、priority agreement
分子/分母、manual corrections、largest weakness），細節仍在月度 summary。

## 品質資料該怎麼用

- 每月看 Weakest module 與 Top correction categories，決定下個月抽查哪個模組。
- `corrections.jsonl` 是未來 rule refinement 的 feedback dataset：例如 priority 一再被下修的事件類型，
  可以**人工**調整 `config/research-policy.yaml` 或 classifier 規則，並在 commit message 引用 correction_id。
- 系統不會自我修改；任何規則變更都要人工決定、測試、commit。
- 樣本不足時不要依百分比下結論。

## 初始 sample events

`python3 scripts/quality_review.py seed` 從既有 regression case 建立 8 筆 pending 事件（全部未經人工驗證）：
PL Q2 FY2027 earnings、PL German 聯邦合約、PL 2026-06-05 價格事件、PL dilution standing trigger、
RKLB INIT baseline、RKLB Neutron 首飛延期、AAPL Q3 FY2026 earnings、2026-10 monthly review。
不在 queue 裡的歷史事件，其分類與 priority 是把真實的 Level 4 classifier / priority engine 套在該事件上重播得到的
（`system_output.replay = true`），以便 review。
