# Level 4 操作指南（Research Command Center）

Level 4 回答的是「現在最該研究哪家公司、發生了什麼、要不要改 thesis、下一步做什麼」。
它不會自動交易，也不會自動跑完整研究：所有觸發都是 REASSESS，真正的更新仍由你下 `/update-stock`。

## 每天

```text
/scan-research
/research-queue
```

1. `/scan-research`：先抓最新股價，再跑
   `python3 scripts/research_command_center.py scan --refresh --skip-prices`。
   只看每家公司 `monitoring/scan-state.json` 之後的新事件（SEC 文件、公司公告、guidance 變化、
   價量事件、規則 / 承諾 / gap 的 state 變化），分類成 A / B / C / D 並放進 `research/queue/current.json`。
2. `/research-queue`：依優先順序列出公司與每個待辦事件需要的 workflow。

| 類別 | 意思 | 你要做的事 |
|---|---|---|
| A FULL_UPDATE_REQUIRED | 新 10-Q / 10-K、財報、guidance 下修、thesis invalidation | `/update-stock TICKER`（完成後自動關閉該公司 A / B 待辦） |
| B TARGETED_UPDATE | 合約、產品、經營層、增資、併購、監控觸發、承諾 missed / delayed | 只更新相關 state（`required_workflow` 寫明哪個 skill） |
| C MARKET_REACTION_ONLY | 沒有新文件的大漲跌 / 異常量 / 回檔 / 52 週新高低 | `price_reaction.py analyze`；state 沒變就不重跑 DCF |
| D LOW_PRIORITY_INFORMATIONAL | 例行 Form 4 / 144、proxy | 只記錄 |

處理完的 item：

```bash
python3 scripts/research_queue.py set EVENT_ID completed --note "REASSESS done: thesis unchanged (reason)"
```

不相關的用 `dismissed`，並寫理由。

## 需要時

```text
/update-stock TICKER
```

Level 3 UPDATE pipeline（只抓比 state 新的 SEC 文件），現在也會順便更新 KPI registry、
management semantic diff、guidance vs actual，最後把該公司的 A / B queue item 標成 completed。

## 每週

```text
/research-dashboard
```

輸出 `research/dashboard/current.md`：

| Ticker | Action | Priority | Thesis trend | Valuation | Expectation gap | Triggers | Next catalyst | Last review |

外加：thesis 改善 / 惡化最大、expectation gap 縮小最多、估值相對自身變便宜、股價漲但基本面沒跟上、
研究已 stale，以及每家公司可解釋的 research confidence（financial history、management history、
KPI coverage、valuation agreement、evidence quality、unresolved promises、stale data）。

`/stale-research` 可單獨檢查過期研究（門檻在 `config/research-policy.yaml`）。

## 每月

```text
/monthly-research
```

先跑 scan，再寫 `research/reviews/YYYY-MM-monthly-review.md`：Level 3 第 1–11 段（本月 snapshot diff）
＋ Level 4 第 12–22 段（Research Priority Changes、Thesis Improvements / Deteriorations、Expectation Gap
Changes、Guidance Delivered / Missed、New Monitoring Triggers、Valuation Re-Rating、Research Staleness、
Next Month Calendar、Top 5 Research Tasks、Deprioritized Names）＋ 第 23 段 Research OS Quality（品質評估層，獨立區段）。

## 設定檔

| 檔案 | 用途 |
|---|---|
| `config/watchlist.yaml` | 要掃描的公司、CIK、sector、research_role、`priority_override`、`enabled`、`macro_links`。不是持股清單。 |
| `config/research-policy.yaml` | 價量門檻、staleness 天數（依 research_role）、priority 門檻、queue 封存天數、首次掃描回看天數。 |
| `config/kpi-registry/*.yaml` | common 與 6 個產業的 KPI 定義。 |
| `research/<T>/config/kpis.yaml` | 公司 KPI、手動公司自訂數值（含原名、定義、來源）、`guidance_metrics`（guided metric 的公司定義與比較口徑）、`milestone_subjects`。 |
| `research/<T>/config/catalysts.yaml`（選用） | 公司已公告的日期（例如財報日），會以 exact date、高信心進 calendar。 |
| `research/queue/macro-inbox.json`（選用） | 手動加入的 macro 項目；只有 topic 在該公司 `macro_links` 內才會變成事件。 |

## Research OS 品質評估（Quality Log）

`/scan-research`、`/update-stock`、`/init-stock`、`/monthly-research` 完成後，系統會自動在
`research/quality/quality-events.jsonl` 建立 **pending** 的品質事件（auto-created ≠ auto-approved；
人工判斷欄位一律 `unknown`）。不需要每天全部人工 review：

| 系統 priority | review 要求 | 做法 |
|---|---|---|
| HIGH | `required`：必 review | `python3 scripts/quality_review.py list --status pending --requirement required` |
| MEDIUM | `spot_check`：抽查；thesis 有改變時一定 review | 每週挑幾筆 |
| LOW | `sample`：抽樣 | 偶爾看 |
| 每月 | 補登漏抓事件 + 看月度 summary | `add-missed-event`、`quality_summary.py` |

```bash
python3 scripts/quality_review.py list --status pending          # 查看待 review
python3 scripts/quality_review.py review <id>                    # review 一筆（終端機會只問相關欄位）
python3 scripts/quality_review.py add-missed-event               # 記錄漏抓事件（false negative）
python3 scripts/quality_review.py correct <id> --field priority --reviewed-value MEDIUM --reason "..."
python3 scripts/quality_summary.py --month 2026-10               # 月度品質報告
```

也可用 `/quality-review`、`/quality-summary`。品質評的是當時的流程、證據與推理：不要用股價後來的漲跌
評分（這類 review 文字會被拒絕）。人工修正存在 `research/quality/corrections.jsonl`，只記錄、不會自動改規則。
月報第 23 段與 dashboard 的「Research OS Quality」區塊是獨立區段，不影響任何公司的 thesis 或 priority。
完整說明：`docs/research-os-quality-framework.md`。

## 新增一家公司

1. `/init-stock TICKER`（需要已驗證的 CIK）。
2. 在 `config/watchlist.yaml` 加一筆（sector 要對應 `config/kpi-registry/` 的檔名）。
3. 建 `research/TICKER/config/kpis.yaml`：至少寫 `guidance_metrics`（每個 guided metric 的公司定義與
   `comparison_basis`）；沒有記錄定義的 guidance 一律 `not_evaluable`。
4. `/scan-research TICKER`。

## 原則

- 觸發 = REASSESS，從來不是 BUY / SELL；WATCH 不是「等價格」。
- 價格變動本身不是基本面證據；C 類事件不會改 thesis。
- 低信心的自動結果標 `draft_auto` / `review_required: true`，需要分析師確認。
- 估值只和公司自己的估值地圖與歷史比較，不跨產業比原始 EV/Sales。
- 未知日期不猜精確日：calendar 只給月份 / 季度 / 年，並標信心。
