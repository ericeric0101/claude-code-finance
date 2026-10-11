# 安裝與 15 步驟執行紀錄

更新日：2026-10-11，Asia/Taipei。工作目錄：`/Users/cheng-kaihuang/stock-deep-research`。
使用者最新選擇為「個股先用 AAPL 做測試」，因此 PL 只備妥流程。

## 使用方式

```sh
cd /Users/cheng-kaihuang/stock-deep-research
python3 scripts/check_setup.py
./scripts/claude auth login
./scripts/claude
```

Claude Code 2.1.296 已以官方 npm package 安裝在 `.tools/claude/`，使用
`scripts/claude` 啟動，不更動全域 PATH。登入需要使用者自己的帳號。
若換一台電腦，重新建立本機工具：

```sh
npm install --prefix .tools/claude @anthropic-ai/claude-code@2.1.296
uv sync --project .claude/skills/finance-skill/scripts
cp .env.example .env
chmod 600 .env
```

此機 `.env` 已設定使用者提供的 SEC identification；Alpha Vantage key 尚空白。
使用者可直接編輯 `.env` 的 `ALPHA_VANTAGE_API_KEY`。不要把 key 放進聊天、
命令列、報告或 Git。`.env` 及 `.env.*` 已排除，唯 `.env.example` 可提交。
SEC／Yahoo 不需要 Alpha Vantage key，本次 AAPL 使用這兩個來源。

```sh
uv run --project .claude/skills/finance-skill/scripts python \
  .claude/skills/finance-skill/scripts/sec_edgar.py AAPL 10-K
uv run --project .claude/skills/finance-skill/scripts python \
  scripts/acquire_research.py AAPL
python3 scripts/extract_aapl.py
python3 .claude/skills/stock-analysis/scripts/verify_data.py research/AAPL/data-intake.json
python3 .claude/skills/stock-analysis/scripts/ratios.py research/AAPL/ratios-input.json
python3 .claude/skills/stock-analysis/scripts/valuation.py research/AAPL/valuation-input.json
python3 .claude/skills/stock-analysis/scripts/score.py research/AAPL/score-input.json
python3 .claude/skills/stock-analysis/scripts/lint_report.py research/AAPL/AAPL-analysis-2026-10-11.md
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
| 3 finance skill | 完成 | 整包複製至 `.claude/skills/finance-skill`，上游內容未改。 |
| 4 uv | 完成 | 既有 uv 0.6.14；已建立 Python 3.11 環境並安裝 finance dependencies。 |
| 5 data sources | 部分完成 | SEC identification 已設定並測試；Alpha Vantage 缺使用者 key；Yahoo price retrieval 成功。 |
| 6 SEC downloader | 完成 | 原版 CLI 成功下載／解析 AAPL FY2025 10-K，filed 2025-10-31。 |
| 7 second repo | 完成 | 暫存資料夾獨立 sparse clone，未混入主 repo Git 歷史。 |
| 8 full skill | 完成 | references、scripts、examples、evals 全部匯入，MIT LICENSE 保留。 |
| 9 project install | 完成 | stock-analysis 已放進 project skill directory；修正原 repo 忽略整個 `.claude/` 的規則。 |
| 10 Claude discovery | 待登入驗證 | Claude CLI 安裝並驗證版本；未登入，無法聲稱 Claude 已辨識 skills。靜態完整性检查成功。 |
| 11 AAPL Standard | 完成 pipeline 測試／研究草稿 | SEC／Yahoo acquisition、document review、data gate、calculators、challenge、lint 已實測；完整 normalized FCFF、比較估值與 validated rating 尚未完成，不能稱 definitive Standard research。不是 Claude 模型執行的結果。 |
| 12 PL Deep Dive | 依最新指示延期 | `docs/research-prompts.md` 已備妥；沒有虛構 PL 報告。 |
| 13 scripts | 完成 | 五個 scripts help／template／example smoke checks 成功；AAPL real input calculations 成功。 |
| 14 custom skill | 完成 | `.claude/skills/my-equity-research/SKILL.md`，官方 quick validator 通過，與上游分離。 |
| 15 commit / push | 本次提交保存整合結果 | 遠端推送結果見本次交付訊息；已確認 dry-run 可用，提交排除 .env、raw filings 及本機工具。 |

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

`check_setup.py` 不傳送 API key、未對 Alpha Vantage 作未配置的請求。
Static skill discovery／CLI help 成功不同於登入後 Claude 正常使用 skill。
intake gate／report linter 為機械 QA，不能證明所有假設正確。研究 raw filings
保留在本機 `research/**/raw/`、不納入 Git；提交來源索引、抽取數據、可重現
計算輸入／輸出、報告与覆核記錄。未提供持股，因此没有 portfolio correlation。
