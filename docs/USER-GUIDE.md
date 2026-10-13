# 使用手冊（從這裡開始）

更新日：2026-10-13（對應 commit 7dc0647 之後的 main：Level 3 引擎、Level 4 指揮中心、品質評估層）。

這個 repo 是一套**美股持續研究系統**。它不是每次重寫一份個股報告，而是替每家公司保存一份有版本的研究狀態
（`research/<TICKER>/`），每次只回答一個問題：**「跟上次研究相比，什麼變了？」**
它會告訴你哪家公司現在最值得研究、發生了什麼、要不要重新檢視 thesis。它**不會**下單，也不給個人化投資建議；
所有警示都只代表 REASSESS（重新檢視）。

本手冊是使用者入口。其他文件的分工見最後一節「延伸文件」。

---

## 1. 三種使用方式

| 你在哪裡 | 怎麼下指令 | 說明 |
|---|---|---|
| 本機 Claude Code（終端機或桌面 app 開這個資料夾） | 斜線指令，例如 `/update-stock PL` | 指令定義在 `.claude/commands/`，入口規則在 `CLAUDE.md`。 |
| 專案聊天室（claude.ai Projects 的對話串） | **用一般文字**請 Claude 執行，例如「幫我更新 PL」「跑一次每日掃描」 | **斜線指令在這裡不能用**。只要 Claude 有連到你電腦上的這個資料夾，它會照下表執行同一組腳本。 |
| Codex 桌面 app | 自然語言（範例在 `docs/research-prompts.md`） | 入口是 `AGENTS.md` 與 `.agents/skills/`（指向 `.claude/skills/` 的 symlink）。 |

三種方式讀寫的是同一份 `research/`、`scripts/`、`config/`，結果一致。對照：

| 斜線指令（本機 Claude Code） | 在專案聊天室可以這樣說 | 實際跑的東西 |
|---|---|---|
| `/scan-research [TICKER…]` | 「掃描 watchlist 有沒有新事件」 | 抓股價 → `research_command_center.py scan --refresh --skip-prices` |
| `/research-queue` | 「現在應該先研究哪家？」 | `research_command_center.py prioritize` + `queue` |
| `/watch-stock PL` | 「看一下 PL 現在的狀態」 | 抓股價 → `research_state.py status PL` |
| `/update-stock PL` | 「更新 PL，只看新資料」 | `research_pipeline.py update PL --cik …` |
| `/init-stock TICKER` | 「幫我建立 XXX 的研究（CIK 是 …）」 | `research_pipeline.py init TICKER --cik …` |
| `/deep-stock AAPL` | 「對 AAPL 做完整深度研究」 | orchestrator DEEP：完整報告 + 更新 state |
| `/research-dashboard` | 「給我看 dashboard」 | `research_command_center.py dashboard` |
| `/stale-research` | 「哪些研究過期了？」 | `research_command_center.py stale` |
| `/monthly-research` | 「跑這個月的月度檢視」 | scan → `monthly_research_review.py` |
| `/quality-review [id\|missed]` | 「列出待 review 的品質事件」 | `quality_review.py list/show/review/add-missed-event` |
| `/quality-summary [YYYY-MM]` | 「產生本月品質報告」 | `quality_summary.py --month …` |

---

## 2. 最佳使用節奏

### 每天（約 5 分鐘）

1. `/scan-research`：先刷新股價，只抓每家公司 `monitoring/scan-state.json` 之後的新事件
   （SEC 文件、公司公告、guidance 變化、價量異常、監控規則 / 承諾 / expectation gap 的狀態變化），
   分成 A / B / C / D 放進 `research/queue/current.json`。
2. `/research-queue`：看排序與每件事需要的處理方式。

| 類別 | 意思 | 你要做的事 |
|---|---|---|
| A FULL_UPDATE_REQUIRED | 新 10-Q / 10-K、財報、guidance 下修、thesis invalidation | `/update-stock TICKER`（完成後自動關閉該公司的 A / B 待辦） |
| B TARGETED_UPDATE | 合約、產品、經營層、增資、併購、監控觸發、承諾 missed / delayed | 只更新相關 state（`required_workflow` 欄寫明找哪個 skill） |
| C MARKET_REACTION_ONLY | 沒有新文件的大漲跌、異常量、52 週新高低 | 只做價量分析；state 沒變就不重跑 DCF，也不改 thesis |
| D LOW_PRIORITY_INFORMATIONAL | 例行 Form 4 / 144、proxy | 只記錄 |

處理完一件就關掉它，並寫理由（不相關的用 `dismissed`）：

```bash
python3 scripts/research_queue.py set EVENT_ID completed --note "REASSESS done: thesis unchanged（理由）"
```

### 有 A 類事件時

`/update-stock TICKER`：只抓比 state 新的 SEC 文件，合併財務歷史、管理層說法、解決舊承諾、
重估規則、只在輸入變動時重算估值、存新 snapshot，輸出
`research/<TICKER>/reports/YYYY-MM-DD-change-report.md`（What Changed Since Last Review）。
自動結果標 `draft_auto` 的部分，請你讀過再定稿。

### 每週

`/research-dashboard` → `research/dashboard/current.md`：每家公司的 Action、Priority、Thesis trend、
相對自身估值地圖的位置、Expectation gap、觸發數、下一個催化劑、上次檢視日，以及可解釋的 research confidence。
順手挑幾筆 MEDIUM 品質事件抽查（見第 5 節）。

### 每月

1. `/monthly-research` → `research/reviews/YYYY-MM-monthly-review.md`（第 1–11 段 Level 3 差異、
   第 12–22 段 Level 4 指揮中心、第 23 段 Research OS Quality）。
2. `/quality-review missed`：補登系統漏抓的重要事件。
3. `/quality-summary`：月度品質報告。

---

## 3. 新增一家公司

1. 先確認 SEC 的數字 CIK（未知 ticker 一定要有已驗證的 CIK，系統不會猜）。
2. `/init-stock TICKER`（= `research_pipeline.py init TICKER --cik CIK`）：建立 5 年 + 8 季財務歷史、
   股價、財報事件、管理層歷史與承諾、自動草稿 thesis / 估值 / 監控規則、snapshot 與 baseline 報告。
   已存在的分析師檔案不會被草稿覆蓋。
3. 在 `config/watchlist.yaml` 加一筆（`sector` 要對應 `config/kpi-registry/` 的檔名：
   common、software、semiconductors、space、biotech、banks、consumer）。
4. 建 `research/TICKER/config/kpis.yaml`，至少寫 `guidance_metrics`（每個 guided metric 的公司定義與比較口徑）；
   沒寫定義的 guidance 一律 `not_evaluable`，不會被自動判定達成或落空。
5. `/scan-research TICKER`。
6. 想要完整報告時再跑 `/deep-stock TICKER`（含 verify_data、valuation、score、challenge、lint_report）。

目前狀態：watchlist 有 **PL、RKLB、AAPL**（三家都有完整 state）。`research/PLTR/` 只有一份 2026-10-11 的單次報告，
沒有 state、也不在 watchlist；要納入追蹤就照上面步驟 init。

---

## 4. 怎麼讀輸出

- **Action**：BUY / ACCUMULATE / WATCH / HOLD EXISTING / AVOID 是研究分類，不是交易指令。
  WATCH 不代表「等跌到某個價」。
- **估值五件事分開看**：模型估值、reverse DCF 的市場隱含預期、由模型值推出的估值地圖、獲利 / 營收追趕情境、
  投資行動。系統刻意不產生「DCF × 8 折 = 買點」這種機械價位（`docs/recommendation-policy.md`）。
- **Expectation gap**：市場價格隱含的假設 vs 你的 base / bull case，並追蹤是在擴大、持平還是縮小。
- **Fact / Calculation / Assumption / Interpretation**：報告裡的重要陳述都有標記。管理層措辭變化只是低信心訊號，
  不會被當成基本面變化。
- **`draft_auto` / `review_required: true`**：自動產生、信心不足，需要你確認。
- **Priority**：代表「先研究誰」，不是「先買誰」。跨公司不比較跨產業的原始倍數。

---

## 5. 品質評估層（讓系統越用越準）

`/scan-research`、`/update-stock`、`/init-stock`、`/monthly-research` 跑完會自動在
`research/quality/quality-events.jsonl` 建立 **pending** 品質事件。只有你能填 review 欄位，系統不會自己打分。

| 系統 priority | 要求 | 做法 |
|---|---|---|
| HIGH | 必 review | `python3 scripts/quality_review.py list --status pending --requirement required` |
| MEDIUM | 抽查；thesis 有改變時一定 review | 每週挑幾筆 |
| LOW | 抽樣 | 偶爾看 |

```bash
python3 scripts/quality_review.py review <id>              # 終端機只會問這筆相關的欄位
python3 scripts/quality_review.py correct <id> --field priority --reviewed-value MEDIUM --reason "..."
python3 scripts/quality_review.py add-missed-event         # 補登漏抓事件
python3 scripts/quality_summary.py --month 2026-10
```

規則：評的是**當時**的流程、證據與推理，不能用之後的股價漲跌評分（這類文字會被拒絕）。
修正只記錄在 `research/quality/corrections.jsonl`，不會自動改規則，也不影響任何公司的 thesis 或 priority。

---

## 6. 讓效果最好的習慣

1. **每次分析前先刷新股價**（斜線指令都已內建）。手動時：
   `uv run --project .claude/skills/finance-skill/scripts python scripts/price_reaction.py fetch TICKER`；
   盤中報價會標 intraday。
2. **先看 queue 再決定做什麼**，不要每天對每家都跑完整研究。C 類事件（純價格）不會也不該改 thesis。
3. **處理完的 queue item 一定要 set completed / dismissed 並寫理由**，否則 HIGH 會一直掛著
   （例如目前 PL、AAPL 的 standing_trigger 就是這種「REASSESS 仍未處理」）。
4. **為每家公司寫好 `config/kpis.yaml` 的 `guidance_metrics`**，guidance vs actual 才能真的被評估。
5. **讀 `draft_auto` 草稿並定稿**：thesis 改變需要證據，價格變動本身不是證據。
6. **每週至少清掉 HIGH 品質事件、每月補登漏抓事件**，月報才有意義。
7. **每次重大更新後 commit**：git 歷史就是研究歷史。push 由你決定。
8. 一手資料優先（SEC / 公司 IR）；聚合資料不會默默覆蓋申報數字（`docs/data-source-policy.md`）。
   系統不會捏造 consensus。

---

## 7. 設定與檔案位置

| 檔案 | 用途 |
|---|---|
| `config/watchlist.yaml` | 掃描名單：CIK、sector、research_role、`priority_override`、`enabled`、`macro_links`。不是持股清單。 |
| `config/research-policy.yaml` | 價量門檻、staleness 天數（依 research_role）、priority 門檻、queue 封存天數、首次掃描回看天數。 |
| `config/kpi-registry/*.yaml` | common 與 6 個產業的 KPI 定義。 |
| `research/<T>/config/kpis.yaml` | 公司 KPI、`guidance_metrics`、`milestone_subjects`。 |
| `research/<T>/config/catalysts.yaml`（選用） | 已公告的日期，以高信心進 calendar。 |
| `research/<T>/` | `thesis/`、`valuation/`、`financials/`、`management/`、`monitoring/`、`market/`、`snapshots/`、`reports/`、日期報告。schema 見 `docs/research-state-schema.md`。 |
| `research/queue/`、`research/dashboard/`、`research/calendar/`、`research/reviews/`、`research/quality/` | 跨公司的佇列、儀表板、催化劑日曆、月報、品質紀錄。 |
| `.env`（不進 Git） | `SEC_EDGAR_USER_AGENT`、`ALPHA_VANTAGE_API_KEY`。不要貼到聊天或 commit。範本：`.env.example`。 |

選用工具：`python3 scripts/tradingview_alert_export.py PL`（把監控價位轉成 TradingView 警示文字）、
`python3 scripts/notebooklm_export.py PL`（NotebookLM 閱讀用來源清單，repo 才是正本）。

---

## 8. 環境檢查與疑難排解

```bash
python3 scripts/check_setup.py            # 檢查 .env、上游套件雜湊、skill 入口
python3 -m unittest discover -s tests     # 全部測試（2026-10-13：91 個通過）
uv sync --project .claude/skills/finance-skill/scripts   # 換電腦時建立資料工具環境
```

- 斜線指令沒反應：你可能在專案聊天室。改用一般文字描述（見第 1 節對照表）。
- 新 ticker 抓不到 SEC 資料：需要 `--cik` 帶已驗證的數字 CIK。
- 沒網路時：`research_pipeline.py init|update … --offline` 會用已快取的 raw 資料與已存股價。
- 上游套件（`finance-skill`、`stock-analysis`、`skills/finance-skill/`）不要改；客製化放在專案自有的 skill 或 `docs/`。

---

## 9. 延伸文件

| 文件 | 何時看 |
|---|---|
| `docs/level4-operating-guide.md` | 每日 / 每週 / 每月流程的操作細節 |
| `docs/us-equity-research-os.md` | 系統架構、資料流、Level 3 引擎（§15）、Level 4 指揮中心（§16） |
| `docs/research-os-quality-framework.md` | 品質評估層完整規格 |
| `docs/research-state-schema.md` | `research/<TICKER>/` 每個檔案的欄位與權威性 |
| `docs/recommendation-policy.md` | Action 標籤、估值決策規則 |
| `docs/data-source-policy.md` | 資料來源層級 |
| `docs/research-report-template.md` | 完整報告格式 |
| `docs/research-prompts.md` | Codex 用的研究提示範例 |
| `docs/dual-codex-claude-usage.md` | Codex 與 Claude Code 共用同一個 repo 的分工 |
| `docs/SETUP.md` | 安裝紀錄與換電腦步驟 |
| `docs/level3-implementation-report.md`、`docs/level4-implementation-report.md`、`docs/quality-implementation-report.md` | 各階段實作與驗證紀錄（歷史文件） |
