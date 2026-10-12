# Research OS 功能驗收稽核（Implementation Audit）

- 稽核日期：2026-10-13（Asia/Taipei）
- 稽核基準：`main` @ `99870a4`（含 `e33b33a Build Claude-compatible continuous US equity research OS`）
- 同時比對的未合併分支：
  - `claude/project-thread-9aep52`（= main + `7e37ffb` 繁體中文報告規則；目前 checkout）
  - `claude/project-thread-20vr29`（= main + `30f95b0` PL 2026-10-12 price-only change report）
  - `claude/project-thread-q265zk`（= 20vr29 + `fe4a943` PL 示意性 reverse DCF 與 expectation gap）
- 方法：直接讀取 skills、scripts、tests、`research/<TICKER>/` state 檔；執行 `python3 -m unittest discover -s tests`；在 scratchpad 的暫存 root 以 `--root` 對 TEST 與 PL 副本做 dry-run。**未呼叫任何網路 API、未修改任何 research 資料、未分析任何股票。**
- 判定標準（依使用者規格）：IMPLEMENTED 需大致同時具備實際 skill/script/schema、明確輸入輸出、Claude Code 可調用、會操作 `research/<TICKER>/` persistent state、有測試或實際 sample output、不只是 markdown 設計。

---

## 0. 結論先講

| 項目 | 判定 |
|---|---|
| 完成度（以「持續追蹤研究系統」為標準） | 約 **40%**（骨架與工具約 70%，實際資料與「持續」部分約 15%） |
| Level | **LEVEL 2 — 原 repo + 部分新研究模組**（尚未到 LEVEL 3） |
| 核心原因 | State schema、state CLI 與 skills 確實存在且可執行，但 (1) 沒有任何把歷史資料自動建起來的程式；(2) PL/AAPL 只做了「一次性報告 → state」的 migration，每家公司只有一個 snapshot；(3) change detection 只比對 thesis status，沒有比對財務、管理層措辭、估值區位或承諾狀態。 |

一句話：**系統的「容器」做出來了，「內容」與「比較引擎」沒做出來。** PL 現在看起來像舊版輸出，是因為 state 裡裝的仍然是 2026-10-11 那份單次報告的數字，而不是系統自己累積出來的歷史。

---

## PART 1 — Inventory

### 1.1 實際結構（main）

| 路徑 | 實際內容 | 備註 |
|---|---|---|
| `CLAUDE.md` | 存在，51 行規則 | 指向 orchestrator 與各 skill |
| `AGENTS.md` | 存在，Codex 用 | 內容有過時處：仍寫「PL is prepared, not scheduled or run」 |
| `.claude/skills/` | 10 個 skill 目錄 | 見 1.2 |
| `.claude/commands/` | `init-stock` `update-stock` `deep-stock` `watch-stock` `monthly-research` | 每個 6–9 行，只是把 intent 轉交 orchestrator |
| `.claude/settings*.json` | **不存在** | 無 hooks、無權限設定 |
| `.codex/` | **不存在** | Codex 相容是靠 `.agents/skills/*` symlink + `AGENTS.md` |
| `.agents/skills/` | 10 個相對 symlink → `.claude/skills/*` | 有 test 確認是 symlink 不是 copy |
| `skills/finance-skill/` | 上游原始副本（無 `.cache`、無 `uv.lock`） | 與 `.claude/skills/finance-skill` 重複，未被引用 |
| `scripts/` | 9 支 .py + `claude` launcher | 見 1.3 |
| `docs/` | 12 份 | 設計、policy、schema、遷移紀錄 |
| `research/` | `AAPL/` `PL/` `PLTR/` | PLTR 未 migrate；**沒有** `research/reviews/` |
| `tests/` | `test_research_os.py`（22 tests）、`test_recommendation.py`（8 tests） | 30 tests 全部通過（0.19s） |

### 1.2 Skills 檢查

| Skill | SKILL.md | Frontmatter | scripts / references / schemas | 引用檔案皆存在 | Claude Code 可 discover | Thin wrapper? | 有可執行 workflow? |
|---|---|---|---|---|---|---|---|
| finance-skill | ✓ 113 行 | ✓（test 驗證） | ✓ `scripts/sec_edgar.py` `alphavantage.py`、apis/、workflows/ | ✓ | ✓ | 否（上游完整套件） | ✓ 資料抓取 |
| stock-analysis | ✓ 318 行 | ✓ | ✓ 5 支 QA scripts、21 份 references、evals | ✓ | ✓ | 否（上游完整套件） | ✓ AAPL 有完整 verify/score/lint 輸出 |
| my-equity-research | ✓ 104 行 | ✓ | 無自有 script；依賴 `scripts/recommendation.py` | ✓ | ✓ | 是（政策層 prose） | 部分 |
| equity-research-orchestrator | ✓ 87 行 | ✓ | 無自有 script；呼叫 `scripts/research_state.py`、`price_reaction.py` | ✓ | ✓ | **是**（路由表 + 步驟 prose） | 部分：步驟清楚，但無程式化決策 |
| management-change | ✓ 53 行 | ✓ | **無 script**；只有 JSON schema 範例 | ✓ | ✓ | **是** | **否**：沒有抽取/比對程式 |
| thesis-monitor | ✓ 47 行 | ✓ | 用 `research_state.py snapshot`（含 validate） | ✓ | ✓ | 半 | ✓ snapshot + 驗證 |
| valuation-monitor | ✓ 57 行 | ✓ | 用 `research_state.py record-valuation / expectation-gap / catch-up`、`recommendation.py` | ✓ | ✓ | 半 | ✓ |
| research-monitor | ✓ 46 行 | ✓ | 用 `research_state.py check-rules` | ✓ | ✓ | 半 | ✓（僅 fundamental 規則） |
| research-review | ✓ 38 行 | ✓ | **無 script** | ✓ | ✓ | **是** | **否**：從未執行、無輸出 |
| market-reaction | ✓ 35 行 | ✓ | `scripts/price_reaction.py` | ✓ | ✓ | 否 | ✓ |

### 1.3 Scripts 實際能力

| Script | 能力 | 通用 / 專用 | 網路 |
|---|---|---|---|
| `research_state.py` (524 行) | `init` `status` `list` `snapshot` `record-valuation` `change-report` `check-rules` `catch-up` `expectation-gap` | 通用 | 無 |
| `price_reaction.py` (205 行) | `fetch`（AV compact ~100 天 + yfinance 預設 2y 回補）、`analyze`（事件反應） | 通用 | fetch 有 |
| `recommendation.py` (202 行) | valuation map、reverse-DCF 比較、earnings / revenue catch-up | 通用 | 無 |
| `acquire_research.py` | 抓 SEC submissions + companyfacts，寫 `filing-manifest.json` | 通用，但 **orchestrator 沒引用**；PL 從未執行 | 有 |
| `extract_aapl.py` | 從 XBRL 抽 5 年年度 + 8 季資料 | **AAPL 專用** | 無 |
| `normalize_aapl.py` / `run_valuation_checks.py` | AAPL 現金流正規化、DCF 敏感度 | **AAPL 專用** | 無 |
| `migrate_legacy_state.py` | 把 2026-10-11 的 AAPL/PL 輸出轉成 state | 一次性；**重跑會覆寫** PL `market/prices.csv`（回到 1 列）與 `evidence/sources.json` | 無 |
| `check_setup.py` | 環境檢查 | 通用 | — |

---

## PART 2 — 七項進階研究能力

### 1. Management Change Tracker — **PARTIAL（偏 DOCUMENTED ONLY）**

- 有：`management-change/SKILL.md` 定義 statement schema（period/topic/statement/verbatim/source/date/interpretation/evidence_strength）與 `changes.md` 表格格式；`research_state.py` 只在 change report 中計數 statements。
- 沒有：任何抽取、比對、diff 管理層措辭的程式；沒有「change vs prior period」欄位的實作。
- PL 實際資料：`management/statements.json` **6 筆，全部是 Q2 FY2027**；topics 只有 guidance×2、backlog/RPO、customer ordering、capex、dilution。`verbatim: false`（全為 paraphrase）。`changes.md` 自己寫明「Only one quarter … no wording comparison exists yet」。
- AAPL：3 筆，全為 Q3 FY2026。
- **PL 沒有 6–8 季 management history → 不能算 IMPLEMENTED。**

### 2. Company Evidence Store — **PARTIAL**

- 有：`evidence/{filings,earnings,presentations,announcements,external}/` 目錄與 `evidence/sources.json` 來源登記（id、tier、type、period_end、filed、url）。
- 實際：五個子目錄**只有 `.gitkeep`，零份文件**（AAPL、PL 皆是）。AAPL 的原始文件在 git-ignored 的 `raw/`；**PL 沒有 `raw/`**。
- PL `sources.json` 6 筆：最新 10-Q、對應 8-K、FY2026 10-K（缺 filed 日期）、3 則 issuer 公告。q265zk 分支另加 Form 4/144 紀錄（+80 行）。
- AAPL 有 22 筆（5×10-K、8×10-Q、8×8-K、1×DEF 14A），來自 `acquire_research.py`，有 retrieved_at。
- 判定：只有「來源索引」，沒有歷史文件庫；provenance 有，但 PL 只覆蓋最新一季。

### 3. Market / Price Reaction Analyzer — **PARTIAL**

- 有：`price_reaction.py analyze` 真的會計算 gap、day return、20 日 median 量比、t-1→t+1、t+2→t+20 drift、20 日 max drawdown，支援 `amc` timing；有 2 個 unit tests；PL、AAPL 都有 `event-reactions.csv` sample output。
- 價格資料：PL `market/prices.csv` 499 列，**2024-10-14 → 2026-10-09（約 2 年）**；400 列 yfinance、100 列 Alpha Vantage。沒有 2024 以前資料（`--period` 可調，但沒做）。
- 事件對齊：PL `events.csv` **只有 3 個事件**（2026-09-03 財報、09-15 德國標案、10-01 發射），沒有過去 8 季財報日。AAPL 有 6 個。
- 缺：abnormal return（無 benchmark）、基本面 vs 股價逐季對照、EV/Sales history。
- 判定：引擎是真的，但資料與事件覆蓋只到最近幾個事件 → PARTIAL。

### 4. Monitoring Rule Engine — **IMPLEMENTED（有限制）**

- `research/PL/monitoring/rules.yaml` 存在，8 條 fundamental 規則 + market `reassess_price: [3, 12, 25]` + optional TradingView 文字。
- `check-rules PL` 實際輸出：`rpo_vs_fiscal_year_end` = triggered（-11.65）；`backlog_yoy`、`dilution_yoy`、`fy27_revenue` = **missing_data**；其他 not_triggered。
- 「alert = reassess」：規則 `meaning` 與 test `test_market_rules_mean_reassess` 都確保不會變成 BUY/SELL；`record-valuation` 會拒絕 `buy_range` 等欄位（有 test）。
- 限制：
  - **market 價格規則沒有被程式評估**（`status` 只是列出價位，不會說是否穿越）。
  - `thesis/invalidation-rules.yaml` 的 `state` 是手寫的，**沒有程式評估**。
  - next catalysts 在 `thesis/current.yaml`，不在 rules 裡。
  - 3/8 規則因資料缺漏無法判斷——這正是缺歷史基線的後果。

### 5. Scenario / Valuation Engine — **PARTIAL**

| 子項 | 狀態 | 證據 |
|---|---|---|
| Bear / Base / Bull | ✓ | `valuation/latest.json` methods |
| Reverse DCF | AAPL ✓（implied growth 14.8%）；PL main 上 **not established**；q265zk 分支有示意值 36% | `valuation/history.csv` |
| Expectation gap | 程式 ✓（`expectation-gap`，per-metric + direction，有 test）；PL main 上 `market_implied: {}` → not quantified | dry-run 輸出 |
| Earnings catch-up | ✓（AAPL；有 test） | `recommendation.py` |
| Revenue catch-up | ✓（PL 實際輸出 EV/Sales 13.5x→6.9x 等） | `catch-up PL` |
| Valuation history | 檔案 ✓，**PL main 只有 1 個日期**（q265zk 有 2 個） | `valuation/history.csv` |
| Valuation confidence | ✓（欄位） | latest.json |
| Valuation map | ✓ | latest.json zones |
| previous → current | change report 有做 method 值的 prev→cur，但只在 ≥2 日期時；**不比對價格區位變化** | `research_state.py:change_report` |

判定：引擎都在、也有 history 檔，但 PL 的 history 只有基準一筆 → PARTIAL。

### 6. Thesis Monitor — **IMPLEMENTED（機制）／PL history 不足**

- `thesis/current.yaml`：PL 8 個 components，皆有 name/importance/status/evidence/last_updated/next_check/invalidation_condition。
- 五種 status 由 `validate_thesis` 強制（有 test `test_thesis_rejects_unknown_status`）。
- `thesis/history.json`：**main 上 PL 只有 1 筆（2026-10-11，migration baseline）**；q265zk 有 2 筆（第二筆是 price-only，無 status 變化）。
- 機制達標；但「PL 有 thesis history」實際上只有基準點。
- 發現 bug：change report 用 `THESIS_STATUSES` 的順序判斷好壞，順序是 supported < improving < uncertain…，所以 **`supported → improving` 會被列為 Negative**（scratchpad dry-run 已重現）。

### 7. Monthly Research Review — **DOCUMENTED ONLY**

- 有：`research-review/SKILL.md`（10 個必要段落、hindsight discipline）、`/monthly-research` command、`research_state.py list`（回傳 AAPL、PL）。
- 沒有：彙整多公司的程式、跨公司優先排序邏輯、`research/reviews/` 目錄、任何一份 monthly review 輸出、任何 test。
- Hindsight control 只是 prose 規則。
- 依使用者標準（無實際 workflow 輸出 → MISSING），嚴格說介於 DOCUMENTED ONLY 與 MISSING 之間；底層的 per-ticker `status/check-rules/change-report` 可用，所以標 DOCUMENTED ONLY。

---

## PART 3 — 新架構功能

| 功能 | 判定 | 證據與說明 |
|---|---|---|
| A. Equity Research Orchestrator | **PARTIAL** | SKILL.md 有 INIT/UPDATE/DEEP/WATCH/WHAT CHANGED/MONTHLY 六個 intent 與路由表，5 個 slash commands 會導向它（有 test）。決策邏輯完全是 prose，沒有程式。實際被跑過一次：20vr29/q265zk 分支的 PL `/update-stock` 產出 change report（未合併）。INIT 步驟沒有「建立歷史基線」這一步。 |
| B. Persistent Company State | **PARTIAL** | AAPL、PL 目錄結構完全符合 schema（company-profile、evidence、management、financials、thesis、valuation、market、monitoring、reports）。但大多數檔案是 2026-10-11 報告的單次轉存；evidence 子目錄是空的；PLTR 未 migrate。 |
| C. Change Detection | **PARTIAL** | `change-report` 真的會比對 thesis/history.json 的前後兩筆（scratchpad 模擬兩筆 snapshot 已驗證會輸出 Positive/Negative/Unchanged）。但：管理層措辭只是「詳見 changes.md」；承諾只計數，不比前後狀態；不比對財務指標；不比對價格與估值區位；expectation gap 是讀 latest.json 的文字；有上述 improving 排序 bug。main 上 PL/AAPL 都只有 1 筆 history，所以實際輸出永遠是「沒有先前狀態」。 |
| D. Management Promise Tracker | **PARTIAL** | `management/promises.json` 存在，欄位齊全（promise_id/topic/statement_date/management_claim/target_date/expected_result/status），status 列舉在程式中定義。PL 6 筆全部 `pending`（皆來自 2026-09-03）；AAPL 2 筆（1 delivered、1 pending）。沒有程式會依新財報更新狀態；沒有過去季度的承諾，所以無法判斷「歷來兌現率」。 |
| E. Expectation Gap | **PARTIAL** | 程式正確比較 market-implied vs internal base vs bull，並輸出 widening/stable/narrowing（有 test），不是單純「股價 > DCF」。但 PL 在 main 上未量化；q265zk 有第一次量化（36% vs 25%/35%），方向仍是「no prior state」。 |
| F. Historical Fundamental Baseline | **PL：MISSING**；AAPL：已有 | PL `financials/historical.csv` **只有 H1 FY2027 一期**（42 列全是 2026-07-31）。**沒有 FY2022–FY2026、沒有 8 季資料。** 沒有任何通用程式會在 init 時從 SEC companyfacts 建 5 年 + 8 季基線（`extract_aapl.py` 是 AAPL 專用）。也沒有程式把 Base 25% CAGR 與歷史 3y/5y CAGR 比較。AAPL 有 FY2021–FY2025 + 8 季，是因為當時另寫了 AAPL 專用 script。 |
| G. Historical Valuation Baseline | **MISSING** | 沒有任何檔案或程式保存 market cap / EV / EV/Sales / P/E / P/FCF 的時間序列。PL 的「~13.5x EV/Sales」只是報告中的單點計算。無法回答 1y/3y/5y 分布位置。必要材料（季度股數、淨現金、營收）在 PL 也都沒有歷史。 |

---

## PART 4 — Workflow Dry-run（不耗 API）

| Intent | 實際測法 | 結果 | 判定 |
|---|---|---|---|
| `/init-stock TEST` | scratchpad root 執行 `research_state.py --root … init TEST` | 建立 15 個 state 檔 + 12 個目錄，全為空殼；`status` 全 None；`snapshot` 因缺 `as_of` 正確拒絕。**不會建立任何歷史財務、價格、估值或管理層基線**；這些要靠後續 Standard analysis 手動填。 | 骨架 ✓，基線 ✗ |
| `/update-stock PL` | 讀 orchestrator UPDATE 步驟 + 跑 `status` / `check-rules` / `change-report`；檢查 q265zk 分支的實際 run | 流程設計上**有**先讀 prior state、只抓新 evidence、更新 thesis/valuation、輸出 change report——不是單純重跑 stock-analysis。q265zk 實際 run 也確實這樣做（查 EDGAR 只有 Form 4/144、thesis 不變、新增 snapshot 與 valuation 列）。但：比較只靠 thesis status；新 evidence 的判斷全靠模型；沒有新財報時能比較的東西很少。 | PARTIAL（真的是增量流程，但比較引擎淺） |
| `/watch-stock PL` | 跑 `status PL`（未 fetch，避免耗 quota） | 輸出 thesis 8 元件、valuation 3/12/25、map 位置、reverse DCF「not established」、expectation gap 文字、8 條 rules 狀態、reassess 價位。**next catalysts 沒出現在 `status` 輸出**（只在 change report）；價格規則不判斷是否穿越。 | PARTIAL+ |
| `/monthly-research` | 跑 `list`，檢查 skill 與輸出目錄 | `list` 回傳 AAPL、PL；之後完全靠模型逐家執行並自行彙整，無程式、無輸出範例、無 `research/reviews/`。 | DOCUMENTED ONLY |

另：`python3 -m unittest discover -s tests` → **30 tests OK**。tests 涵蓋 frontmatter、symlink、state 不含 buy range、upsert、rule 評估、event reaction、change report 基準輸出；**沒有** 測試多期 change detection、management diff、歷史基線、monthly review。

---

## PART 5 — PL Regression 逐項判斷

原因代碼：A=功能根本沒實作｜B=功能存在但 orchestrator 沒調用｜C=功能存在但 PL 尚未 migration｜D=資料來源不足

| 已知缺口 | 主因 | 說明 |
|---|---|---|
| 基本面幾乎只有 Q2 FY2027 | **A + C** | 沒有通用 XBRL 基線建置程式（A）；migration 只轉存 `filings-data.json` 的 H1 FY2027（C）。`acquire_research.py` 能抓 PL companyfacts，但 orchestrator 沒呼叫、PL 也從未執行（B 的成分）。SEC companyfacts 對 PL（CIK 1836833，2021 年底上市）可提供 FY2022 起資料，**不是 D**。 |
| 缺 FY2022–FY2026 長期趨勢 | **A + C** | 同上。 |
| 缺過去 8 季 quarterly trend | **A + C** | 同上；XBRL 有季度資料可用。 |
| Base 25% / 20% FCF margin 缺歷史驗證 | **A** | 沒有任何「assumption vs history」檢查程式或報告段落要求被強制執行。 |
| 股價有歷史但沒有逐季對照基本面 | **A**（+C） | `price_reaction.py` 只做事件窗口，不 join 財務資料；PL `events.csv` 只有 3 個近期事件。 |
| 沒有完整 historical EV/Sales | **A**（+少量 D） | 無程式、無 schema；價格只有 2y（`--period` 可拉長，AV 免費版只有 compact），股數/淨現金歷史沒建。 |
| Management 8 季 guidance/actual 不完整 | **A + C**（+部分 D） | 沒有抽取/比對程式（A）；只寫入 Q2 FY2027（C）；過去 8-K Item 2.02 exhibits 可從 SEC 取得，但 earnings call 逐字稿非 SEC 一級來源（D 只影響逐字稿部分）。 |
| TradingView 只是 optional alert 文字 | **設計如此 / A** | 架構文件本來就只承諾 optional alert 文字與 Pine 範例；技術分析從未被規劃實作。 |
| （額外）PL 未跑完整 stock-analysis QA | **B** | PL 目錄沒有 `data-verification`、`score-output`、`report-lint` 檔；AAPL 有。CLAUDE.md 要求 full report 要跑。 |

**結論：主要是 A（功能不存在），其次是 C（只做了單點 migration）。不是 orchestrator 漏叫（B 只佔小部分），也不是資料來源不足（D 很次要）。**

---

## PART 6 — Compliance Matrix

| Capability | Status | Actual implementation | Evidence | PL usable now? | Action needed |
|---|---|---|---|---|---|
| Finance data acquisition | IMPLEMENTED | 上游 finance-skill（SEC/AV/yfinance）+ `price_reaction.py fetch` + `acquire_research.py` | `.claude/skills/finance-skill/scripts/`；AAPL `filing-manifest.json` | 部分：價格可；PL 從未跑 `acquire_research.py` | 把 acquire 步驟接進 INIT/UPDATE |
| Stock analysis | IMPLEMENTED | 上游 stock-analysis 5 支 QA scripts | AAPL `score-output.json` `report-lint.json` 等 | 否：PL 未跑 QA | PL 重跑 QA（實作階段） |
| Historical financial baseline | **MISSING**（PL）／AAPL 專用版 | 只有 `extract_aapl.py` | PL `financials/historical.csv` 僅 H1 FY2027 | 否 | 通用 companyfacts → 5y + 8Q 基線建置器 |
| 8-quarter management tracker | PARTIAL（偏文件） | SKILL.md schema；無程式 | PL statements 6 筆皆 Q2 FY2027 | 否 | 回填 8 季 + 比對程式 |
| Management promise tracker | PARTIAL | `promises.json` schema + 狀態列舉 | PL 6 筆全 pending | 有限 | 回填過去季度承諾並驗證兌現 |
| Company evidence store | PARTIAL | `sources.json` 登記 | evidence 子目錄皆空；PL 無 raw/ | 有限 | 版本化保存一級文件或摘錄 |
| Thesis monitor | IMPLEMENTED | `current.yaml` + `snapshot` 驗證 | 8 元件、五種 status、test | 是 | 修 improving 排序 bug |
| Thesis history | PARTIAL | `history.json` upsert | main 1 筆；q265zk 2 筆 | 只有基準 | 合併分支；累積 snapshot |
| Valuation monitor | IMPLEMENTED | `record-valuation`、`recommendation.py` | history.csv、tests | 是 | — |
| Valuation history | PARTIAL | `history.csv` upsert by as_of×method | PL main 1 日期 | 只有基準 | 合併分支；每次更新記錄 |
| Reverse DCF | PARTIAL | AAPL 量化；PL 未建立（分支有示意） | `valuation/latest.json` | main 上否 | PL 正式建立 |
| Expectation gap | PARTIAL | 程式 + direction + test | PL `market_implied: {}` | main 上否 | 填 market_implied |
| Catch-up analysis | IMPLEMENTED | earnings / FCF / revenue catch-up | `catch-up PL` 實際輸出；tests | 是 | 加入股數稀釋路徑 |
| Market reaction analyzer | PARTIAL | `price_reaction.py analyze` | PL 3 事件、2y 價格 | 有限 | 8 季財報事件 + 更長價格 + benchmark |
| Historical valuation baseline | **MISSING** | 無 | 無檔案、無程式 | 否 | EV/Sales、P/FCF 等時間序列與分位 |
| Monitoring rules | IMPLEMENTED（有限制） | `rules.yaml` + `check-rules` | PL 8 規則，3 條 missing_data | 是 | 評估 market 規則與 invalidation rules |
| TradingView optional alerts | DOCUMENTED ONLY（設計如此） | rules.yaml 內文字 + SKILL.md Pine 範例 | 無產生器 | 文字可用 | P2，可維持現狀 |
| Change detector | PARTIAL | `change-report` 只比 thesis status | dry-run；分支 sample | 只會說「無先前狀態」 | 擴充為 state diff 引擎 |
| Research orchestrator | PARTIAL | SKILL.md prose + 5 commands | 分支上有一次真實 UPDATE | 是（靠模型） | INIT 加歷史基線；UPDATE 加 diff 步驟 |
| Monthly review | DOCUMENTED ONLY | SKILL.md + command | 無輸出、無程式、無 test | 否 | 彙整程式 + 第一次實跑 |
| NotebookLM optional workflow | DOCUMENTED ONLY（設計如此） | 一份 22 行說明 | `docs/notebooklm-optional-workflow.md` | N/A | 無需動作 |
| Codex/Claude dual compatibility | IMPLEMENTED | `.agents/skills` symlink、AGENTS.md、CLAUDE.md | `test_codex_entries_are_symlinks_not_copies` | 是 | 更新 AGENTS.md 過時敘述 |

---

## PART 7 — Verdict

**LEVEL 2：Original repos + some new research modules.**

不給 LEVEL 3 的理由：
1. Persistent state 存在，但每家公司都只有一個時間點；系統從未自己累積過第二個有實質內容的狀態（main 上）。
2. Change detection 只比 thesis status，沒有 state-level diff。
3. 歷史基本面與歷史估值基線（研究「回推未來」最需要的部分）在 PL 完全缺失，且沒有通用程式能建立。
4. Monthly review 從未產出。
5. 最新的 update 成果還在未合併分支上。

不給 LEVEL 1 的理由：`research_state.py`、`price_reaction.py`、`recommendation.py`、rule 評估、snapshot/upsert、expectation gap 都是真的、可執行、有 tests 的新程式。

---

## PART 8 — Gap Analysis

排序標準：讓系統從「一次性股票分析器」變成「持續追蹤公司變化的研究系統」。不以新增估值模型為優先。

### P0 — 必須先補

1. **通用歷史基本面基線建置器**：從 SEC companyfacts 為任一 ticker 建 5 年年度 + 8 季以上資料（revenue、GP/GM、OI/OM、NI、CFO、capex、FCF、SBC、diluted shares、debt、cash、RPO/backlog），寫入 `financials/historical.csv`，並接到 INIT 與 UPDATE。取代 AAPL 專用 `extract_aapl.py` 的角色。
2. **Assumption-vs-history 檢查**：Base/Bull 假設必須輸出 3y/5y CAGR、最近 8 季軌跡、假設比歷史高多少（PL 的 25%/20% 是第一個案例）。
3. **真正的 state diff change detector**：比對前後 state 的財務指標、thesis status（修 improving 排序 bug）、估值值與區位、expectation gap、承諾狀態變化、rule 狀態變化；不只是 thesis status。
4. **PL 依新架構重新 migration（回填）**：8 季 management statements、過去季度 promises 與兌現結果、8 季財報事件。
5. **合併未合併分支並鎖定流程**：把 20vr29/q265zk/9aep52 的成果整理進 main，避免 state 分叉；並讓 `migrate_legacy_state.py` 不會覆寫已更新資料（或封存）。

### P1 — 很重要

6. 歷史估值基線：價格 × 股數 × 淨現金 → market cap / EV / EV/Sales / P/FCF 時間序列，回答 1y/3y/5y 分位。
7. 價格與基本面逐季對照（財報日事件表自動由 `sources.json` 產生；加 benchmark 算 abnormal return；價格拉長到上市以來）。
8. Monitoring：程式評估 market 價格規則與 `invalidation-rules.yaml`；`status` 輸出 next catalysts。
9. Monthly review 彙整程式 + 第一次實跑，產出 `research/reviews/<YYYY-MM>-monthly-review.md`。
10. Management wording diff 工具（同 topic 跨期對照表半自動產生）。
11. Evidence store 實際保存一級文件摘錄（至少 8-K exhibits 與 10-Q 關鍵段落）。

### P2 — Optional

12. TradingView Pine 產生器。
13. NotebookLM 匯出。
14. PLTR migration。
15. 移除重複的 `skills/finance-skill/` 上游副本或註明用途；更新 AGENTS.md 過時敘述。

---

## PART 9 — 本次未做的事

- 未修改 architecture、未新增 skills、未重寫 PL、未更改任何 `research/` 檔案。
- 未執行 `price_reaction.py fetch` 或任何 SEC/AV 呼叫（避免耗 quota）。所有 dry-run 都在 scratchpad 暫存 root 進行。
- 本文件尚未 commit。

---

## 附錄：已發現的具體問題

1. `scripts/research_state.py` `change_report()`：以 `THESIS_STATUSES` 索引判斷好壞，`supported → improving` 被列為 Negative（scratchpad 重現）。
2. `change_report()` 不比對價格、估值區位、財務指標、承諾狀態前後變化；expectation gap 只讀 latest.json 文字。
3. `status()` 不輸出 next catalysts，也不判斷價格是否穿越 `reassess_price`。
4. `check_rules()` 只評估 `monitoring.fundamental`；`invalidation-rules.yaml` 的 `state` 為手寫。
5. `migrate_legacy_state.py` 重跑會把 PL `market/prices.csv` 覆寫成 1 列、覆寫 `evidence/sources.json`。
6. `init` 只建空殼，不建任何歷史基線。
7. PL 未執行 stock-analysis QA scripts（無 verify/score/lint 輸出）。
8. `AGENTS.md` 仍寫「PL is prepared, not scheduled or run」。
9. PL `sources.json` 的 FY2026 10-K 缺 `filed` 日期。
