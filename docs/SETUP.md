# 安裝與 15 步驟執行紀錄

更新日：2026-10-11，Asia/Taipei。工作目錄：`/Users/cheng-kaihuang/stock-deep-research`。
使用者最新選擇為「個股先用 AAPL 做測試」，因此 PL 只備妥流程。

## 使用方式（Codex）

直接在 Codex 桌面 app 開啟此專案，輸入 `docs/research-prompts.md` 的研究需求。
Codex 入口為 `AGENTS.md` 與 `.agents/skills/`，三個 skill 使用 relative symlink
指向 `.claude/skills/` 的完整版本化套件，避免重複及上游內容漂移。
不需要 Claude 帳號、Claude 登入或另裝 Claude CLI。

每份股票分析會先提供 BUY／ACCUMULATE／WATCH／HOLD EXISTING／AVOID、簡短理由、當日股價與估值信心。報告會分開呈現模型估值、市場隱含預期、估值地圖與投資行動；以 reverse DCF 作為主要決策檢查，並在適用時分析獲利追趕情境。不會把單一 DCF 自動折價成必須等待的買入價。完整報告保留假設、來源和風險，標籤不是個人化買賣指令。詳見 `docs/recommendation-policy.md`。

標準研究也會在分析日檢查與公司曝險相關的近期事件：央行利率／公債殖利率、通膨、
匯率、戰爭／制裁／航運、油氣與其他關鍵成本、關稅與監管變更。會追到官方或公司
一手來源並說明傳導路徑；資料足夠才量化，否則列為監控情境，不對所有股票套用
同一個地緣政治或油價折價。新股票可先用 `docs/research-prompts.md` 的 Quick screen。

```sh
cd /Users/cheng-kaihuang/stock-deep-research
python3 scripts/check_setup.py
```

換電腦時只需建立資料工具環境及本機 credentials（不要覆蓋既有 `.env`）：

```sh
uv sync --project .agents/skills/finance-skill/scripts
cp .env.example .env
chmod 600 .env
```

舊 `scripts/claude` 保留為相容入口，不屬於目前 Codex 工作流程。
本機 Homebrew `codex-cli 0.36.0` 是舊版，`login status` 曾發生系統設定 panic；
這不代表目前桌面 Codex 未登入。此次沒有安裝或替換 CLI，也沒有聲稱 CLI 驗證通過。
若 skill 未出現在選單，可重新開啟專案；目前對話可直接讀取完整 SKILL.md。
官方設定說明：https://learn.chatgpt.com/docs/build-skills

此機 `.env` 已設定使用者提供的 SEC identification；Alpha Vantage key 已配置（不記錄其值）。
使用者可直接編輯 `.env` 的 `ALPHA_VANTAGE_API_KEY`。不要把 key 放進聊天、
命令列、報告或 Git。`.env` 及 `.env.*` 已排除，唯 `.env.example` 可提交。
SEC／Yahoo acquisition 與 Alpha Vantage GLOBAL_QUOTE 均已實測；AAPL 最新 close 的日期／價格一致，結果見 `research/AAPL/alpha-vantage-check.json`。

```sh
uv run --project .agents/skills/finance-skill/scripts python \
  .agents/skills/finance-skill/scripts/sec_edgar.py AAPL 10-K
uv run --project .agents/skills/finance-skill/scripts python \
  scripts/acquire_research.py AAPL
python3 scripts/extract_aapl.py
python3 .agents/skills/stock-analysis/scripts/verify_data.py research/AAPL/data-intake.json
python3 .agents/skills/stock-analysis/scripts/ratios.py research/AAPL/ratios-input.json
python3 .agents/skills/stock-analysis/scripts/valuation.py research/AAPL/valuation-input.json
python3 .agents/skills/stock-analysis/scripts/score.py research/AAPL/score-input.json
python3 .agents/skills/stock-analysis/scripts/lint_report.py research/AAPL/AAPL-analysis-2026-10-11.md
```

`extract_aapl.py` 是本次日期／公司專用 intake adapter，不是 generic XBRL engine。
重新研究時須更新 as-of、年度／季度範圍、報告、估值假設與來源；單獨重新跑
extract 不會自動生成新的研究結論。非內建 ticker（例如 PL）必須提供已核驗
的 numeric CIK，例如 `scripts/acquire_research.py PL --cik <verified-cik>`。

## 15 步狀態

| 步驟 | 狀態 | 實際結果 |
|---|---|---|
| 1 Fork | 完成 | 已確認 `ericeric0101/claude-code-finance` 是原主 repo 的 Fork。 |
| 2 Clone | 完成 | 在使用者空白 workspace clone 原主 repo，Fork 建立後改 origin 指向使用者 Fork；保留完整主 repo 歷史與 upstream。 |
| 3 finance skill | 完成 | 整包保存在 `.claude/skills/finance-skill`，由 `.agents/skills/finance-skill` 提供 Codex 入口；上游內容未改。 |
| 4 uv | 完成 | 既有 uv 0.6.14；已建立 Python 3.11 環境並安裝 finance dependencies。 |
| 5 data sources | 完成配置與連線測試 | SEC identification、Yahoo acquisition、Alpha Vantage AAPL GLOBAL_QUOTE 均成功；key 只在 ignored .env。 |
| 6 SEC downloader | 完成 | 原版 CLI 成功下載／解析 AAPL FY2025 10-K，filed 2025-10-31。 |
| 7 second repo | 完成 | 暫存資料夾獨立 sparse clone，未混入主 repo Git 歷史。 |
| 8 full skill | 完成 | references、scripts、examples、evals 全部匯入，MIT LICENSE 保留。 |
| 9 project install | 完成 | stock-analysis 已放進 project skill directory；修正原 repo 忽略整個 `.claude/` 的規則。 |
| 10 Codex skill entry | 已改用 Codex | AGENTS.md 與三個 `.agents/skills/` 入口已配置並驗證；目前 Codex 可直接讀取，選單自動載入未另外實測。不再需要 Claude 登入。 |
| 11 AAPL Standard | 完成現金流／估值更新；peer rating 保留限制 | Codex 完成 CFO 勾稽、明列假設正常化 FCFF、實證折現率 anchors、growth reinvestment DCF、matched reverse、earnings cross-check、independent challenge 與 QA。Current interest／intangible spending 拆分與 validated peer-relative rating 缺口仍揭露；不稱 definitive fair value。 |
| 12 PL Deep Dive | 依最新指示延期 | `docs/research-prompts.md` 已備妥；沒有虛構 PL 報告。 |
| 13 scripts | 完成 | 五個 scripts help／template／example smoke checks 成功；AAPL real input calculations 成功。 |
| 14 custom skill | 完成 | `.agents/skills/my-equity-research/SKILL.md`，官方 quick validator 通過，與上游分離。 |
| 15 commit / push | 完成初次整合；Codex 適配另行提交 | 初次提交 86941f6 已推送 Fork；Codex 更新結果見交付訊息。提交排除 .env、raw filings 及本機工具。 |

## 上游與更新

主 repo：`https://github.com/andrasp/claude-code-finance`，版本
`8870afd6492e846209b6be5b14bd92e4b6f2b719`。
第二 skill：`https://github.com/alirezarezvani/claude-skills`，版本
`19392f7a08264ed00486a251f5b2098321771f94`，來源路徑
`finance/skills/stock-analysis`。每個匯入檔案的 SHA-256 位於
`upstream-versions.json`，`check_setup.py` 驗證其內容未意外改動。

更新時先 fetch／review 上游差異，重新完整複製對應 skill；更新 manifest 和
授權檔，再執行 CLI 與研究 QA。不要只替換 SKILL.md。財務資料與模型假設
有獨立生命週期，更新 skill 不代表舊研究變成最新。`my-equity-research` 不需
與上游內容混合。原版 README、`skills/finance-skill/` 與 LICENSE 均保留。

## 驗證界線

`check_setup.py` 不傳送 API key；另外在使用者配置後已實際測試 Alpha Vantage，保存不含 key 的報價結果。
技能入口與 CLI help 檢查不同於 app 選單 discovery；目前 Codex 已讀取技能，未另外模擬新工作階段自動載入。
intake gate／report linter 為機械 QA，不能證明所有假設正確。研究 raw filings
保留在本機 `research/**/raw/`、不納入 Git；提交來源索引、抽取數據、可重現
計算輸入／輸出、報告与覆核記錄。未提供持股，因此没有 portfolio correlation。

## AAPL 現金流正常化／估值更新

`research/AAPL/cashflow-valuation-review.md` 為本次聚焦交付；主報告已同步。
`cashflow-source-inputs.json` 保存 FY21–25／兩期9M／TTM 元件，
`discount-rate-inputs.json` 保存 dated anchors 及60個monthly return observations。

```sh
python3 scripts/normalize_aapl.py
python3 .agents/skills/stock-analysis/scripts/verify_data.py research/AAPL/normalization-data-intake.json
python3 .agents/skills/stock-analysis/scripts/lint_report.py research/AAPL/AAPL-analysis-2026-10-11.md --strict
```

`normalized-valuation-input.json`／output 保存本次 assumptions、逐年 reinvestment、
同模型 reverse 與 sensitivity；上游 `valuation.py` 另作簡化 DCF cross-check。
原 `valuation-input.json`／output／sensitivity 是初次 pipeline 歷史，現值結論已由
normalized 模型取代，不能把原$205／未折現FY27情境當作本次結果。
會計勾稽與模型驗證通過不表示所有前瞻假設會成真；獨立challenge見
`normalization-challenge.md`。
