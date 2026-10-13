# Level 4 實作前基線（Pre-implementation baseline，2026-10-13）

本文件記錄開始 Level 4（Research Command Center）之前的 repo 狀態，作為 regression 的比較基準。所有內容來自本機實際執行的指令輸出。

## 1. Git 狀態

| 項目 | 值 |
|---|---|
| 起始分支 | `claude/project-thread-9aep52`（Level 4 改在新分支 `claude/project-thread-iqcpc8` 上開發，起點相同） |
| 目前 commit | `a1cc1d6 Implement Level 3 continuous equity research engine` |
| 前一個 commit | `f285180 Merge PL 2026-10-12 update branches (20vr29, q265zk)` |
| 未 push 的 commits | 4 個（相對 `origin/claude/project-thread-9aep52`）；本次也不 push |
| 工作樹 | 乾淨（`git status`：nothing to commit） |
| `git diff` | 空 |
| Remotes | `origin` = CK 的 fork；`upstream` = andrasp/claude-code-finance（不可推） |

## 2. Secrets 檢查

- `.env` 列在 `.gitignore`，`git ls-files` 只追蹤 `.env.example`；`.env` 未被追蹤。
- `research/**/raw/`（SEC companyfacts、submissions、新聞稿快取）為 git-ignored。
- 未印出任何 API key。

## 3. 測試

`python3 -m unittest discover -s tests` → **Ran 51 tests, OK**（`test_research_os.py`、`test_recommendation.py`、`test_level3.py`）。無 regression，因此可以直接往下做 Level 4。

## 4. 已研究公司（research state 可讀）

| Ticker | thesis/current.yaml | Snapshots | Action / 估值信心 | 備註 |
|---|---|---|---|---|
| AAPL | 分析師版 | 2026-10-11、2026-10-13 | WATCH / low | 成熟公司；reverse DCF quantified（implied NOPAT growth 14.8%）；promise tracker 2 筆（delivered 1、pending 1） |
| PL | 分析師版 | 2025-09-10（retrospective）、2026-06-08、2026-10-11、2026-10-12、2026-10-13 | WATCH / low | 多期 state；68 個承諾：delivered 44、superseded 8、pending 8、missed 6、partially_delivered 2 |
| RKLB | `draft_auto` | 2026-10-13 | WATCH / low | Level 3 INIT 建立；新聞稿無 guidance → promise tracker 為空（正常） |
| PLTR | 無 state | — | — | 只有 2026-10-11 報告與 recommendation I/O，未 migrate |

開始前已重新抓價（`price_reaction.py fetch`）：最新完整收盤 2026-10-12，PL 15.96、RKLB 65.71、AAPL 340.97（yfinance tier 4；`latest-quote.json` 為 10-12 盤中價，標示 intraday）。

## 5. Level 3 能力（必須保留）

- `research_state.py`：init / status / list / snapshot / snapshot-state / record-valuation / record-gap / refresh-financials / change-report / check-rules / catch-up / expectation-gap。
- `research_pipeline.py init|update`：INIT 15 步、UPDATE 13 步。
- `build_fundamental_history.py`（5Y + 8Q、provenance）、`build_management_history.py`（statements、guidance、promise lifecycle）、`build_valuation_history.py`（歷史倍數、百分位、基本面-股價時間線）、`assumption_history_check.py`、`state_diff.py`（多領域 snapshot diff）、`backfill_state_snapshots.py`、`baseline_draft.py`、`monthly_research_review.py`。
- `recommendation.py`：valuation map、reverse DCF 解讀、catch-up；禁止 buy range / entry price。
- `price_reaction.py fetch / analyze / fetch-benchmark`。
- 監控規則觸發只輸出 REASSESS。
- Codex 相容：`.agents/skills/*` 為指向 `.claude/skills/*` 的相對 symlink。
- Slash commands：`/init-stock`、`/update-stock`、`/deep-stock`、`/watch-stock`、`/monthly-research`。

## 6. 已知限制（Level 3）

1. 管理層主題 / 語氣分類是關鍵字 heuristic，信心低；沒有跨季的語意比較。
2. PL capex promise 用現金流量表口徑（PP&E + 資本化軟體）判斷，公司 guidance 的 capex 定義未確認一致 → 目前有 6 個 capex 承諾被判為 missed / 2 個 partially_delivered，這是錯誤風險。
3. Promise 狀態沒有 `delayed`、`not_evaluable`；沒有 `metric_definition`、`comparison_basis`、`resolution_confidence`、`actual_source` 欄位。
4. 沒有通用 KPI registry；backlog、RPO、ARR 等公司 KPI 依賴 `tag-overrides.json`，沒有產業層級定義。
5. 沒有事件偵測、事件分類、研究佇列、跨公司優先順序；monthly review 的優先順序只看 snapshot diff。
6. 沒有 stale research 偵測、catalyst calendar、command-center dashboard。
7. 每次 UPDATE 會重抓 SEC companyfacts；沒有 `last_checked` 之類的增量欄位。
8. 公司層級信心只有 low / medium / high 一個字，沒有可解釋的組成。
9. PLTR 尚未 migrate；2026-10-11 snapshot 是從 git 重建。
