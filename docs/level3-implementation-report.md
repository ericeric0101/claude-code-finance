# Research OS Level 3 實作報告（2026-10-13）

本文件回覆「把 Research OS 從 LEVEL 2 提升到至少 LEVEL 3」的要求。所有數字來自本次實際執行的輸出（SEC companyfacts、8-K Item 2.02 新聞稿、股價檔），未使用記憶中的數字。

## 0. 起始檢查與分支合併

- `git status`：起始只有未追蹤的 `docs/research-os-implementation-audit.md`（稽核文件，本次一併 commit）。
- `.env` 在 `.gitignore` 內、未被追蹤；未印出任何 secret；`research/**/raw/`（SEC 原始檔與新聞稿快取）維持 git-ignored。
- 分支處理：
  - `claude/project-thread-9aep52`（目前分支 = main + 繁中報告規則）作為基底。
  - `claude/project-thread-q265zk`（疊在 `20vr29` 之上）以 `--no-ff` 合併（merge commit `f285180`），一次帶進兩者的成果：PL 2026-10-12 price-only change report、示意性 reverse DCF（implied 36.1%）、expectation gap 首次量化、2 年股價、Form 4/144 紀錄、測試 rewind helper。無衝突；30 個舊測試合併後全數通過。
  - 遠端分支一律未刪除、未 push。
- 新 state 不覆寫舊 state：分析師撰寫的 `thesis/current.yaml` 只改 `as_of` / `last_update_report` 兩行；`invalidation-rules.yaml` 只「新增」機器 checks；管理層 statements / promises 以合併方式加入，舊的 6 則人工陳述保留。

## 1. 實際完成的功能

| 功能 | 狀態 | 證據 |
|---|---|---|
| 通用歷史基本面 baseline（任一美股） | 完成 | PL、AAPL、RKLB 皆 ≥5 FY、≥8 季；`financials/history.json` + `coverage.json` |
| Assumption vs history 檢查 | 完成 | `valuation/assumption-check.{json,md}` |
| Management 8 季歷史 + 跨季比較 | 完成（heuristic） | PL 10 季、206 則陳述、68 筆 guidance；`management/changes.md` |
| Promise lifecycle | 完成 | PL 68 個承諾自動結案 / 保持 pending / superseded |
| 真正的 state diff change report | 完成 | `snapshots/*.json` + `state_diff.py`；PL `reports/2026-10-13-change-report.md` |
| 歷史估值（EV/Sales 等）與百分位 | 完成 | PL 53 個月底點，無 look-ahead |
| 基本面 vs 股價逐季時間線 | 完成 | PL 10 次財報 `market/fundamental-price-timeline.csv` |
| Benchmark-adjusted 反應（SPY；可設 sector ETF） | 完成 | `market/event-reactions.csv` abnormal 1D/5D/20D |
| Expectation-gap 歷史 | 完成 | `valuation/expectation-gap-history.csv`（widening / stable / narrowing） |
| Monitoring：fundamental + market + invalidation | 完成 | `check-rules`；觸發只輸出 REASSESS |
| INIT pipeline（15 步） | 完成 | `/init-stock RKLB` 實跑 |
| UPDATE pipeline（13 步） | 完成 | `/update-stock PL`、AAPL 實跑 |
| Monthly review | 完成（最小可用） | `research/reviews/2026-10-monthly-review.md` |
| PL 多期 state（含 retrospective） | 完成 | 5 個 snapshots |

## 2. 保留的舊功能

- Codex 相容：`.agents/skills/*` symlink、`AGENTS.md` 未刪（只更新過時的一句）。
- `scripts/extract_aapl.py`、`normalize_aapl.py`、`run_valuation_checks.py` 保留未刪；新 builder 已驗證可重現 extract_aapl 的輸出，之後可再考慮 deprecate。
- `research_state.py` 原有指令（init/status/list/snapshot/record-valuation/change-report/check-rules/catch-up/expectation-gap）全部保留；`change-report` 在少於 2 個 snapshot 時仍走舊的 thesis/valuation-history 路徑。
- `recommendation.py`（valuation map、reverse DCF 解讀、catch-up）、`price_reaction.py fetch/analyze`、禁止 buy range 的檢查全部保留。
- 既有 dated reports 一律未改寫、未翻譯。

## 3. 修正的 bugs

1. **Thesis status 排序 bug**：不再用 enum 位置判斷好壞。`THESIS_TRANSITIONS` 明確定義全部 20 種轉換（positive / neutral / negative）；`supported → improving` = neutral（「證據較不穩固，但不自動視為負面」），`uncertain → improving`、`improving → supported` = positive，`supported → weakening`、`weakening → invalidated` = negative。
2. **migrate_legacy_state.py 破壞性覆寫**：改為封存的 one-time 工具，沒有 `--legacy-one-time` 會拒絕執行；所有寫入改為只補缺（prices 依日期、sources 依 id、historical 依 period_end+metric、latest.json 只補缺少的 metric）。在副本實測重跑：0 個檔案被改。
3. **status() 缺 next catalysts**：現在輸出 current action、thesis summary、valuation summary（含歷史百分位）、expectation gap（含歷史方向）、monitoring rules（三類）、next catalysts、latest change date。
4. **check_rules() 只看 fundamental**：加入 market reassess（上次檢視價格到最新收盤之間穿越的價位 = triggered）與 thesis invalidation（機器 checks、連續 N 季、`logic: any`；沒有 checks 的規則標為 manual）。所有觸發只輸出 `REASSESS`。
5. 事件時間：財報 8-K 改用 EDGAR acceptance time 判斷 amc/bmo。PL 2026-09-03 財報原本被當成盤中事件（t0 = 09-03，−8.2%），實際是盤後發布，t0 應為 09-04（−1.25%，SPY 調整後 −0.86%）。

## 4. 新增 scripts

| Script | 用途 |
|---|---|
| `scripts/sec_data.py` | SEC 存取層（重用 finance-skill client；快取到 git-ignored raw/） |
| `scripts/build_fundamental_history.py` | 通用 5Y+8Q 歷史基本面（mapping layer、provenance、YTD 推導、amendment 優先、as_of 截止） |
| `scripts/assumption_history_check.py` | Base/Bull 假設 vs 歷史 |
| `scripts/build_management_history.py` | 管理層陳述、guidance、跨季比較、promise lifecycle、財報事件清單 |
| `scripts/state_diff.py` | 多領域 state snapshot 與 diff、change report |
| `scripts/build_valuation_history.py` | 歷史估值倍數、百分位、基本面-股價時間線 |
| `scripts/baseline_draft.py` | INIT 用的 auto-draft thesis / 估值 / 規則（標示 draft_auto） |
| `scripts/research_pipeline.py` | INIT / UPDATE pipeline |
| `scripts/monthly_research_review.py` | 月度多公司 review |
| `scripts/backfill_state_snapshots.py` | 無後見之明的過去 state（retrospective 或從 git 重建） |

修改：`research_state.py`、`price_reaction.py`（`fetch-benchmark`、abnormal returns）、`migrate_legacy_state.py`。

## 5. 新增 tests

`tests/test_level3.py` 21 個（全部離線）：generic baseline builder、quarterly standalone derivation、missing tag / fallback / amendment precedence、thesis transition classification、market + invalidation rules、status 段落、legacy migration 不可覆寫、state diff（財務 / 承諾 / 估值區位）、expectation-gap history、歷史估值 no-lookahead、guidance 解析與 promise lifecycle、monthly review 輸出、INIT 建立 baseline 而非空殼、UPDATE 保留舊歷史、PL regression ×3、AAPL regression ×2。

## 6. PL 現在的歷史資料

- 年度（SEC companyfacts，USD m）：

| FY | 營收 | YoY | 毛利率 | 營業利益率 | FCF | SBC | 稀釋股數(m) | 現金+短投 | 債務 | RPO |
|---|---|---|---|---|---|---|---|---|---|---|
| FY2022 | 131.2 | 15.9% | 36.8% | −97.6% | −57.1 | 42.0 | 79.6 | 490.8 | 0.0 | 153.4 |
| FY2023 | 191.3 | 45.8% | 49.2% | −91.9% | −86.7 | 75.5 | 267.1 | 408.8 | n/a | 152.0 |
| FY2024 | 220.7 | 15.4% | 51.2% | −76.9% | −93.1 | 57.1 | 279.6 | 298.9 | n/a | 132.6 |
| FY2025 | 244.4 | 10.7% | 57.2% | −47.5% | −64.0 | 48.5 | 292.1 | 222.1 | 0.0 | 412.8 |
| FY2026 | 307.7 | 25.9% | 56.1% | −30.9% | 52.9 | 55.0 | 307.8 | 640.1 | 446.9 | 852.4 |

  另有 FY2021。FY2023/24 的債務在 XBRL 無資料，保留 null（未填 0）。
- 季度：Q3 FY2024–Q2 FY2027 共 12 季（含由 YTD 推導的單季 CFO/capex/SBC、Q4 由 FY − 9M 推導，均記錄推導方式）。核對：Q1+Q2 FY2027 營收 210.2、capex 47.1、CFO 68.4 與 10-Q 的 H1 數字一致。
- Backlog：us-gaap 無標準 tag，維持 unavailable（新聞稿陳述有記錄在 statements）。
- 財報事件：最近 10 次 8-K Item 2.02（2024-06-06 起），含 amc/bmo。
- 管理層：10 季、206 則原文陳述；68 筆 guidance；guidance vs actual 自動比較。
- 股價：2021-04 起（含 SPAC 期間；估值從 2021-12-08 de-SPAC 後開始），SPY 2015 起。
- 歷史 EV/Sales：2022-06 起 53 個月底點 + 財報前後點；目前 15.2x（2026-10-09 收盤），1Y 百分位 30.8（區間 12.8–50.8x）、3Y 75.7、上市以來 80.9。
- 基本面-股價時間線回答「$2 → $17 期間發生什麼」：RPO 從 $112m（Q2 FY2025）升到 $413m（Q4 FY2025）再到 $753m；營收 YoY 從 4.6% 加速到 58.1%；營業利益率從約 −65% 改善到 −11.6%；同時 EV/Sales 從約 1.1x 擴張到 15–50x。股價的大部分漲幅發生在估值倍數擴張，基本面改善是真的但速度慢於倍數。
- State 歷史：snapshots 2025-09-10（retrospective）、2026-06-08（retrospective）、2026-10-11（從 git 重建的實際檢視）、2026-10-12（實際）、2026-10-13（本次 UPDATE）。Retrospective snapshot 的 action / thesis 為空，標示 `retrospective = true`，不捏造當時建議。

## 7. PL Base/Bull 假設 vs 歷史

歷史（Calculation）：營收 3Y CAGR 17.2%、5Y CAGR 22.1%、FY2026 成長 25.9%、TTM 成長 44.1%、最近 8 季 YoY 4.6%–58.1%（中位數 26.4%）；FCF margin 3 年平均 −17.1%、FY2026 17.2%（受客戶預付款墊高）、TTM 5.2%。

| 假設 | 數值 | 分類 | 白話 |
|---|---|---|---|
| Base 營收 CAGR | 25% | Near historical | reasonable：與 5Y CAGR 22% 相當，低於近期軌跡 |
| Bull 營收 CAGR | 35% | Above historical | aggressive：高於長期歷史，但仍在近期軌跡（TTM 44%）內 |
| Base FCF margin | 20% | Above historical | aggressive：只有 FY2026 曾接近（17%，且含預付款效果），TTM 僅 5% |
| Bull FCF margin | 25% | Materially above historical | very aggressive：超過所有歷史實績 |

解讀（Interpretation）：成長假設有歷史支撐，主要風險在現金轉換假設。市場隱含（36.1% 5 年 CAGR，在 Base 的 20% margin 下）比 Bull 成長還高，等於同時押注成長與尚未證明的 margin。

## 8. Management 8-quarter tracking

完成（以 Tier 1 新聞稿為主）：每季分 demand、customers、backlog/RPO、guidance、capex、margins、product launch、customer qualification、constraints、cash flow、dilution 主題擷取原文；guidance 跨期比較（例：FY2027 營收 guidance 415–440 → 425–441 → 430–441；非 GAAP 毛利率 50–52% → 52–54% → 55–57%，均為 raised；capex 計畫 80–95 → 100–115，標為支出計畫上調）。限制：主題與語氣為關鍵字 heuristic（低信心）；逐字稿未納入。

Promise 結果（PL）：delivered 44、missed 6、partially_delivered 2、superseded 8、pending 8（Q3 FY2027 與 FY2027 guidance）。營收、毛利率、EBITDA guidance 全部達成；所有 missed / partial 都是 capex 偏離支出計畫（有低於也有高於），且 capex 口徑（PP&E + 資本化軟體）可能與公司定義不同。僅為計數，不是管理層可信度分數。

## 9. Historical EV/Sales

完成。每個日期只使用當時已申報的財報（每個 10-Q/10-K 申報日重建一次 history，取 ≤ 該日的最新版本），股數用封面流通股數，EV 不含租賃。EV/EBIT、P/E 因虧損標為 n/m；P/FCF 只在 FCF > 0 時計算。

## 10. Change detector 現在能比較什麼

前後兩個 snapshot 的：A 財務（營收、YoY、毛利率、營業利益率、FCF、TTM、normalized FCF、SBC、稀釋股數、債務、現金、RPO、backlog）；B 管理層（新一季陳述、主題措辭、guidance raised/lowered、新 guidance）；承諾（新承諾、狀態轉換與實際值）；C thesis（狀態轉換依明確 mapping、證據變更）；D 估值（價格、情境值、估值區位、歷史百分位、信心）；E expectation gap（widening / stable / narrowing）；F 監控（newly triggered、resolved、still triggered、missing data）；以及 action / confidence previous → current、next catalysts。股價變動只列在估值，不當成基本面變化。

本次 PL UPDATE（2026-10-12 → 2026-10-13）實際結果：無新 SEC 財報；thesis、估值、gap 不變；新觸發 4 條需 REASSESS 的規則，原因是歷史資料首次可用或口徑改為 TTM：稀釋股數 YoY +18.2%（>5%）、TTM capex/營收 25.8%（>25%）且 FCF 扣除遞延收入為負。這是「重新評估」訊號，不是賣出訊號。

## 11. Monthly review

可以實際執行：`research/reviews/2026-10-monthly-review.md` 涵蓋 AAPL、PL、RKLB，11 個段落齊全。PL = High（guidance 改變、新財報、capex 承諾偏離、規則新觸發）；AAPL、RKLB = Low。規則透明，不用事後股價評斷論點。

## 12. AAPL regression

- 新的通用 builder 與 `extract_aapl.py` 產出的 5 個年度與 8 季（營收、淨利、CFO、capex、營業利益、SBC、稀釋股數、現金等）逐值比對全部一致（差異 < 0.5m）。
- Reverse DCF 仍為 quantified（implied 14.8%）；earnings catch-up（10%、2 年 → 32.5x）不變；valuation map 位置仍為 "above all modeled bull values"；`valuation/latest.json` 無 buy range / entry price。
- AAPL 也跑了一次 UPDATE：無新 10-Q/10-K（只有 8-K/A），應收帳款相關規則仍為 triggered。

## 13. Tests

`python3 -m unittest discover -s tests` → **51 tests, OK**（原 30 + 新 21）。

## 14. Level 評估

**LEVEL 3 — Persistent continuous-equity research system mostly working.** 條件逐項核對：

| 條件 | 結果 |
|---|---|
| generic historical baseline working | ✓ PL / AAPL / RKLB |
| PL has multi-period state | ✓ 5 個 snapshots（2 retrospective + 3 實際） |
| update produces real multi-domain diff | ✓ |
| historical valuation exists | ✓ |
| management history exists | ✓ 10 季 |
| promise lifecycle works | ✓ |
| state histories persist | ✓ thesis / valuation / gap / snapshots / promises |
| tests pass | ✓ 51 |

不是 LEVEL 4：thesis 判斷與長篇報告仍需研究員；管理層擷取是 heuristic；逐字稿與非 XBRL 公司 KPI 未自動化。

## 15. 限制

- 管理層主題 / 語氣為關鍵字 heuristic；RKLB 與 AAPL 的新聞稿不寫 guidance，因此 promise tracker 為空（guidance 若只在電話會議或簡報中，需 Tier 2 人工補）。
- Backlog、ARR、bookings 等公司 KPI 無 us-gaap tag，預設 unavailable；需在 `financials/tag-overrides.json` 指定擴充 tag 或人工填。
- Capex promise 判斷用現金流量表口徑，可能與公司定義不同。
- INIT 的 thesis / 估值 / 規則是 auto-draft（`draft_auto: true`，WATCH / low confidence），必須研究員複核；RKLB 的 auto-draft 估值（bear 4.4 / base 11.4 / bull 33.4，價格 68.21）只反映歷史錨定的假設，不是判斷。
- INIT 自動跑 stock-analysis 的 ratios.py 與 verify_data.py；valuation.py / score.py / challenge / lint_report 需要研究員撰寫的報告，未自動化。
- 歷史估值 EV 不含租賃；債務在 XBRL 無資料的期間以 0 計算並在 note 標示。
- 股價來自 yfinance（tier 4）回補 + Alpha Vantage（tier 3）近 100 日；PL 2021-12 以前為 SPAC 價格，未用於估值。
- 2026-10-12（美東）盤中執行，最新完整收盤為 2026-10-09；盤中價只存在 `latest-quote.json`。
- 2026-10-11 snapshot 是從 git 重建（state 檔取自當時 commit，SEC 歷史以同日截止重建），不是當時即時產生。
- 尚未 push；PLTR 尚未 migrate。

## 16. Commit

見 thread 回覆中的 commit hash（`Implement Level 3 continuous equity research engine`）。
