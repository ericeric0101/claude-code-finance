# Research OS Level 4 實作報告（2026-10-13）

本文件回覆「把 Research OS 從 LEVEL 3 升級到 LEVEL 4」的要求。數字都來自本機實際執行的輸出（股價最新完整收盤 2026-10-12、SEC 快取、cached 財報新聞稿）；沒有使用記憶中的數字。實作前基線見 `docs/level4-preimplementation-baseline.md`；架構見 `docs/us-equity-research-os.md` §16；操作見 `docs/level4-operating-guide.md`。

## 1. 結論

**LEVEL 4 — Research Command Center：大致成立（13 項條件逐項見第 9 節）。** 有兩個重要但不推翻結論的限制：語意分析是規則式（不是 LLM），以及本次首次掃描是在剛完成 Level 3 更新的當天執行，所以「真實」佇列裡主要是仍未處理的 REASSESS，A 類事件的展示靠 `--since 2026-08-29` 重播（不寫 state）。

## 2. 新增的核心功能

| # | 元件 | Script | 主要輸出 |
|---|---|---|---|
| 1 | KPI Registry | `kpi_registry.py` + `config/kpi-registry/*.yaml` + `research/<T>/config/kpis.yaml` | `financials/kpi-history.csv`、`kpi-coverage.json` |
| 2 | Management Semantic Intelligence | `management_semantic_diff.py` | `management/claims.json`、`semantic-diff.{json,md}` |
| 3 | Guidance-vs-Actual Engine | `guidance_tracker.py` | `promises.json` lifecycle 欄位、`guidance-vs-actual.{json,md}` |
| 4 | Research Event Queue | `research_event_detector.py`、`research_queue.py` | `research/queue/current.json` |
| 5 | Event Classifier | `research_event_classifier.py` | A / B / C / D + workflow |
| 6 | Priority Engine | `research_priority.py` | `research/queue/priorities.json`、`priority-history.csv` |
| 7 | Catalyst Calendar | `catalyst_calendar.py` | `research/calendar/upcoming.csv` |
| 8 | Stale Research Detector | `stale_research.py` | `research/dashboard/stale-research.{md,json}` |
| 9 | Research Command Center | `research_dashboard.py`、`research_command_center.py`、`research_confidence.py` | `research/dashboard/current.{md,json}` |
| 10 | Enhanced Monthly Review | `monthly_research_review.py`（第 12–22 段） | `research/reviews/2026-10-monthly-review.md` |
| P2 | TradingView / NotebookLM | `tradingview_alert_export.py`、`notebooklm_export.py` | `monitoring/tradingview-alerts.md`、`exports/notebooklm-sources.md` |

新 slash commands：`/scan-research`、`/research-queue`、`/research-dashboard`、`/stale-research`（原本五個保留）。新設定：`config/watchlist.yaml`（不是持股清單）、`config/research-policy.yaml`。

## 3. Level 3 保持不變的部分

- INIT / UPDATE pipeline 的步驟與編號不變（INIT 仍 15 步、UPDATE 13 步）；Level 4 的步驟以 step 0 附加，失敗也不會讓 Level 3 pipeline 失敗。
- state schema 沒有被取代：只新增欄位與檔案。`PROMISE_STATUSES` 只「加」`delayed`、`not_evaluable`。
- Level 3 tests 一個都沒刪（51 個仍通過）。
- 對 Level 3 程式碼的修改只有 4 處，都是小幅、向下相容：
  1. `build_management_history.promise_id`：GAAP 毛利率改用 `gaapgm`，避免與 non-GAAP 毛利率（`gm`）同 id 互相覆蓋（RKLB 兩者都有 guidance 時才會發生；PL 的既有 id 不變）。
  2. `research_state.PROMISE_STATUSES` 新增兩個狀態。
  3. `state_diff` 把 `delayed` 視為負面轉換。
  4. `research_pipeline`：UPDATE / INIT 在管理層步驟後呼叫 KPI registry + guidance tracker；UPDATE 結束時關閉該公司 A / B queue items。
- Codex / Claude 相容：沒有動 `.agents/skills` symlink；`AGENTS.md` 加一段 Level 4 指令；所有功能都是 Codex 也能直接跑的 Python script。

## 4. KPI registry

支援 common + 6 個產業：software、semiconductors、space、biotech、banks、consumer（AAPL 用 consumer + 公司覆寫）。

| Ticker | Sector | Required 可用 | Optional 可用 | Optional unavailable |
|---|---|---|---|---|
| PL | space | 12 / 12 | backlog、government_mix、commercial_mix、satellites_deployed、satellite_commissioning、rpo_12m_conversion、non-GAAP GM、adjusted EBITDA | launch_cadence |
| RKLB | space | 12 / 12 | backlog、launch_cadence | government_mix、commercial_mix、satellites_deployed、satellite_commissioning |
| AAPL | consumer | 11 / 11（含 Services） | buybacks、dividends、capex、net_margin、services_mix | same_store_sales |

缺資料一律寫 `unavailable`；PL backlog 814.9 與 RPO 753.1 分開存（concept guard 禁止用 RPO 填 backlog）；RKLB 的 FY2024「16 launches for Electron」和 FY2025「21 missions across Electron and HASTE」保留原名並註明定義不同、不可直接比較。

## 5. 重要發現（對既有 state 的修正）

1. **PL capex 定義其實一致。** 10 份 cached 財報新聞稿的 KPI 定義段都寫 capex = 「purchases of property and equipment plus capitalized internally developed software development costs」，與 repo 的會計口徑相同。所以 PL capex 承諾不是 `not_evaluable`，而是 `comparison_basis: definition_match`，並逐筆標 `resolution_confidence`：用 YTD 差分推出的季度（可能來自後來重編的比較欄）為 medium、`review_required: true`。超出區間的改寫成「spending-plan deviation，本身不是負面訊號」。PL 承諾計數與 Level 3 相同（delivered 44、missed 6、partially 2、superseded 8、pending 8），但每筆都多了定義、口徑與信心。
2. **RKLB 新聞稿其實有量化 guidance。** Level 3 的 prose parser 抓不到 RKLB 條列式「Guidance … expects: •」。Level 4 補進 83 筆（9 季）：營收 8/8 delivered、GAAP 毛利率 8/8 delivered、GAAP opex（以毛利 − 營業利益計算，medium 信心）3 delivered / 5 partially；non-GAAP、Adjusted EBITDA、利息、SBC、分部營收共 50 筆 `not_evaluable`（actual 不在 local state 或口徑未驗證）；基本股數 guidance 含 ~41–51m 特別股、XBRL 基本股數不含 → `definition_mismatch` → `not_evaluable`。專案記憶裡「RKLB 沒有 guidance」需要更正。
3. **RKLB Neutron 首飛時程延後。** 2025-02-27 新聞稿「planned debut launch in the second half of 2025」→ 2026-02-26「first launch now targeted for Q4 2026」：舊承諾標 `delayed`，新目標 Q4 2026 為 `pending`（進 catalyst calendar，quarter 精度）。

## 6. 實際輸出（2026-10-13）

首次 `/scan-research`（以上次研究檢視日 2026-10-13 為起點）：

| 排名 | Ticker | Priority | 理由 |
|---|---|---|---|
| 1 | PL | HIGH | 3 個不同條件的監控規則仍觸發未處理（RPO 低於年度末、capex 強度、稀釋），含 2 條 invalidation |
| 2 | AAPL | HIGH | 應收帳款規則與 invalidation 仍未處理，對應 high importance 的 earnings_quality_working_capital |
| 3 | RKLB | MEDIUM | Neutron 首飛延後（promise delayed）；稀釋規則仍觸發（per_share_dilution 為 medium importance） |

Dashboard（`research/dashboard/current.md`）：PL Demanding（介於 base 與 bull）、AAPL / RKLB Expensive（高於所有 bull 值）；三家 expectation gap 都 Wide；本期沒有 thesis 狀態變化；相對研究價格，PL −7.1%、RKLB −3.7%；沒有 stale。Research confidence：PL medium、AAPL medium、RKLB low（auto-draft thesis 與估值）。

Catalyst calendar：15 筆。財報日只給月份（PL 2026-12、RKLB 2026-11、AAPL 2026-11，low 信心，依各自 8 次財報的發布間隔中位數），法規申報期限標 upper bound；PL 可轉債轉換窗結束 2026-10-31、AAPL iPhone Duo 上市 2026-10-23 取自 thesis 內有來源的日期；引用日期（例如「earnings 8-K 2026-09-03」）不會被誤當成事件日。

事件分類重播（`research_event_classifier.py TICKER --since 2026-08-29`，dry run，不寫 state）：

#### PL
| Date | Event | Cat | Severity | Priority | Workflow | Reason |
|---|---|---|---|---|---|---|
| 2026-09-03 | earnings_release | A | high | HIGH | /update-stock PL (Level 3 UPDATE pipeline: research_pipeline | earnings release (8-K Item 2.02) |
| 2026-09-03 | guidance_update | B | medium | MEDIUM | management-change + valuation-monitor: compare new range wit | guidance raised: adjusted_ebitda FY2027 [0.0, 10.0] → [3.0, 10.0] |
| 2026-09-03 | guidance_update | B | medium | HIGH | management-change + valuation-monitor: compare new range wit | spending plan changed: capex FY2027 [80.0, 95.0] → [100.0, 115.0] |
| 2026-09-03 | guidance_update | B | medium | HIGH | management-change + valuation-monitor: compare new range wit | guidance raised: non_gaap_gross_margin FY2027 [52.0, 54.0] → [55.0, 57.0] |
| 2026-09-03 | guidance_update | B | medium | HIGH | management-change + valuation-monitor: compare new range wit | guidance raised: revenue FY2027 [425.0, 441.0] → [430.0, 441.0] |
| 2026-09-15 | major_contract | B | medium | MEDIUM | thesis-monitor: update demand / backlog components with the  | German federal satellite-services tender award (max EUR 25m incl. options) |
| 2026-09-15 | major_drawdown | C | medium | MEDIUM | market-reaction: price_reaction.py analyze PL (event window, | drawdown -68.83% from 52-week high 51.4; no new filing — price action alone is not evidence of a fundamental c |
| 2026-10-01 | product_launch | B | medium | MEDIUM | thesis-monitor: update the product / execution component; KP | Launch of 20 satellites (Suncatcher demo; Tanager-2; 18 SuperDoves) |
| 2026-10-02 | insider_filings | D | low | LOW | log only (no research action) | routine insider filings: 5 Form 4, 3 Form 144 (2026-09-17..2026-10-02) |
| 2026-10-02 | major_price_move | C | low | LOW | market-reaction: price_reaction.py analyze PL (event window, | 1-day move 8.43%; coincides with a filing on 2026-10-01 (covered by that event) |
| 2026-10-13 | standing_trigger | B | medium | HIGH | thesis-monitor / research-monitor: the REASSESS is still ope | fundamental rule 'rpo_vs_fiscal_year_end' still triggered since 2026-10-13 → REASSESS still open |
| 2026-10-13 | standing_trigger | B | medium | HIGH | thesis-monitor / research-monitor: the REASSESS is still ope | fundamental rule 'capex_intensity' still triggered since 2026-10-13 → REASSESS still open |
| 2026-10-13 | standing_trigger | B | medium | HIGH | thesis-monitor / research-monitor: the REASSESS is still ope | fundamental rule 'dilution_yoy' still triggered since 2026-10-13 → REASSESS still open |
| 2026-10-13 | standing_trigger | B | medium | HIGH | thesis-monitor / research-monitor: the REASSESS is still ope | invalidation rule 'capex_heavy_with_negative_fcf' still triggered since 2026-10-13 → REASSESS still open |
| 2026-10-13 | standing_trigger | B | medium | HIGH | thesis-monitor / research-monitor: the REASSESS is still ope | invalidation rule 'dilution_above_5pct' still triggered since 2026-10-13 → REASSESS still open |
#### RKLB
| Date | Event | Cat | Severity | Priority | Workflow | Reason |
|---|---|---|---|---|---|---|
| 2026-09-15 | acquisition | B | medium | MEDIUM | thesis-monitor + valuation-monitor: deal terms, dilution and | acquisition / merger filing (425) |
| 2026-09-15 | investor_presentation | B | low | LOW | management-change: compare new targets / wording with manage | investor presentation |
| 2026-09-15 | major_drawdown | C | medium | MEDIUM | market-reaction: price_reaction.py analyze RKLB (event windo | drawdown -57.7% from 52-week high 150.23; no new filing — price action alone is not evidence of a fundamental  |
| 2026-09-21 | major_price_move | C | low | LOW | market-reaction: price_reaction.py analyze RKLB (event windo | 1-day move 8.24%; no new filing — price action alone is not evidence of a fundamental change |
| 2026-10-02 | insider_filings | D | low | LOW | log only (no research action) | routine insider filings: 3 Form 4, 2 Form 144 (2026-09-02..2026-10-02) |
| 2026-10-13 | promise_delayed | B | medium | MEDIUM | management-change: timing slip; thesis-monitor for the affec | promise RKLB-milestone-neutron-first_launch-2025-02-27 delayed (target moved H2 2025 → Q4 2026 (2026-02-26)) |
| 2026-10-13 | standing_trigger | B | medium | MEDIUM | thesis-monitor / research-monitor: the REASSESS is still ope | fundamental rule 'dilution_yoy' still triggered since 2026-10-13 → REASSESS still open |
| 2026-10-13 | standing_trigger | B | medium | MEDIUM | thesis-monitor / research-monitor: the REASSESS is still ope | invalidation rule 'dilution_above_5pct' still triggered since 2026-10-13 → REASSESS still open |
#### AAPL
| Date | Event | Cat | Severity | Priority | Workflow | Reason |
|---|---|---|---|---|---|---|
| 2026-09-01 | management_change | B | medium | MEDIUM | management-change: record the change; thesis-monitor if a co | management change |
| 2026-09-09 | company_announcement | B | low | LOW | thesis-monitor: read and decide relevance | iPhone Duo announced |
| 2026-09-25 | new_52w_high | C | low | LOW | market-reaction: price_reaction.py analyze AAPL (event windo | new 52-week closing high 341.07; no new filing — price action alone is not evidence of a fundamental change |
| 2026-10-08 | insider_filings | D | low | LOW | log only (no research action) | routine insider filings: 17 Form 4, 4 Form 144 (2026-09-01..2026-10-08) |
| 2026-10-13 | standing_trigger | B | medium | HIGH | thesis-monitor / research-monitor: the REASSESS is still ope | fundamental rule 'receivables_gap' still triggered since 2026-10-13 → REASSESS still open |
| 2026-10-13 | standing_trigger | B | medium | HIGH | thesis-monitor / research-monitor: the REASSESS is still ope | invalidation rule 'receivables_inventory_build' still triggered since 2026-10-13 → REASSESS still open |


## 7. Tests

`python3 -m unittest discover -s tests` → **75 tests, OK**（Level 3 原有 51 + Level 4 新增 24，覆蓋要求的 19 類：KPI registry loading、company override、semantic diff、guidance normalization、guidance-vs-actual、metric mismatch → not_evaluable、event classifier、research queue、priority engine、stale detector、catalyst calendar、dashboard、monthly review、no BUY / SELL、cross-company priority、Level 3 / PL / RKLB / AAPL regression）。

## 8. 限制

- 語意分析是規則式結構化比較，不是 LLM 理解；措辭類發現一律 low confidence，只當作閱讀線索。
- RKLB 的 non-GAAP / Adjusted EBITDA 實際值沒有從新聞稿調節表擷取，所以 50 筆 guidance 為 not_evaluable（不是 missed）。
- 公司自訂 KPI（backlog、客戶別占比、發射次數）靠 `config/kpis.yaml` 手動值；XBRL 沒有維度資料（例如 AAPL Services 只有 FY2025 一筆）。
- 首次掃描在 Level 3 更新當天，真實佇列只有 REASSESS 與 Neutron 延後；A 類流程的實例是重播與合成測試。
- 財報日期是依節奏估的月份；公司正式公告日期需寫進 `config/catalysts.yaml`。
- 市場事件只用已抓到的日線；沒有盤中監控；`--refresh` 只更新 SEC submissions 清單。
- AAPL 的應收帳款 invalidation 是 manual 規則（沒有機器 checks），仍需分析師判斷。
- TradingView / NotebookLM 只產生文字，不呼叫外部服務。
- 尚未 push；PLTR 仍未 migrate。

## 9. Level 4 條件核對

| 條件 | 結果 |
|---|---|
| 1 multi-company event queue | 成立：3 家、10 個 open items、去重、superseded、封存 |
| 2 event classification | 成立：A / B / C / D，含 workflow 與理由 |
| 3 priority engine | 成立：透明規則、可解釋理由、跨公司排序、override |
| 4 KPI registry | 成立：common + 6 產業 + 公司覆寫 |
| 5 guidance-vs-actual | 成立：PL 68、RKLB 83 筆；定義不符 → not_evaluable |
| 6 semantic management diff | 大致成立（規則式）：PL 20 筆 guidance 變化、RKLB 時程延後 |
| 7 catalyst calendar | 成立 |
| 8 stale research detection | 成立（今天三家都不 stale；合成測試涵蓋新財報未吸收） |
| 9 command-center dashboard | 成立 |
| 10 enhanced monthly review | 成立：第 12–22 段 |
| 11 PL / RKLB / AAPL regression | 通過 |
| 12 Level 3 能力保留 | 是 |
| 13 all tests pass | 75 / 75 |
