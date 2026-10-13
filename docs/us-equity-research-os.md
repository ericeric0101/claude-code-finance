# US Equity Research OS

A continuous research system: each company has persistent, versioned state, and
each update answers **"What changed since the previous research state?"**

## 1. Architecture

```
            user: /init-stock /update-stock /deep-stock /watch-stock /monthly-research
                                   │  (Codex: natural language)
                                   ▼
                    equity-research-orchestrator  (routing, state discipline)
      ┌──────────────┬─────────────┼──────────────┬───────────────┬──────────────┐
      ▼              ▼             ▼              ▼               ▼              ▼
 finance-skill  stock-analysis  my-equity-   management-   thesis-monitor  valuation-monitor
 (SEC, Alpha    (framework,     research     change        (components,    (methods, reverse
  Vantage,       QA scripts,    (actions,    (statements,   invalidation)   DCF, map, catch-up,
  yfinance)      challenge)     policy)      promises)                      expectation gap)
      │                                                                      │
      │            market-reaction (price_reaction.py)   research-monitor (rules.yaml)
      ▼                                   │                       │
 ┌───────────────────────── research/<TICKER>/ state ─────────────────────────┐
 │ evidence/ management/ financials/ thesis/ valuation/ market/ monitoring/   │
 │ reports/  + dated reports and input/output JSON (authoritative per date)   │
 └────────────────────────────────────────────────────────────────────────────┘
                                   │
                         research-review (monthly, all tickers) → research/reviews/
                                   │
                              git history (audit trail)
```

## 2. Data flow

SEC / IR (tier 1) and market data (tier 3, yfinance tier 4) → `finance-skill`
clients → dated inputs in `research/<TICKER>/` → `stock-analysis` scripts
(`verify_data`, `ratios`, `valuation`, `score`, `lint_report`) and
`scripts/recommendation.py` → state files via `scripts/research_state.py` →
change report → git commit.

## 3. Skills

| Skill | Role |
|---|---|
| `equity-research-orchestrator` | Intents: init, update, deep, watch, what-changed, monthly; Level 4: scan-events, research-queue, prioritize, command-center, stale-check |
| `finance-skill` | Data acquisition (upstream, unmodified) |
| `stock-analysis` | Fundamental framework and QA tools (upstream, unmodified) |
| `my-equity-research` | Decision layer: BUY / ACCUMULATE / WATCH / HOLD EXISTING / AVOID |
| `management-change` | Eight-quarter wording comparison; promise tracker |
| `thesis-monitor` | Component status from evidence |
| `valuation-monitor` | Valuation history, reverse DCF, map, catch-up, expectation gap |
| `market-reaction` | Event price / volume reactions (observation vs interpretation) |
| `research-monitor` | Machine-readable rules; optional TradingView |
| `research-review` | Monthly cross-company review |

## 4. Company state

See `docs/research-state-schema.md` (files, authority, field contracts).

## 5. Initial research flow

verify CIK → `research_state.py init` → Standard analysis and dated report →
fill thesis / valuation / financials / management / monitoring →
`snapshot` → `record-valuation` → baseline `change-report` → commit.

## 6. Update flow

refresh prices (`price_reaction.py fetch`, always) → `status` → list filings newer than `as_of` → management-change →
thesis-monitor → valuation-monitor → `check-rules` → `snapshot` →
`record-valuation` → `change-report --out reports/<date>-change-report.md` → commit.

Change report sections: Positive, Negative, Unchanged, Management wording
changes, Promises, Thesis, Valuation (previous → current), Expectation gap,
Action, Confidence, Next catalysts.

## 7. Monthly review flow

`list` → per ticker `status` / `check-rules` / `change-report` (UPDATE only where
new filings exist) → ten-question review in `research/reviews/<YYYY-MM>-monthly-review.md`,
separating what was known then from what became known later.

## 8. Data-source hierarchy

Tier 1 SEC / IR → tier 2 official macro → tier 3 Alpha Vantage / exchange →
tier 4 yfinance / aggregators. Lower tiers never override higher tiers.
Details: `docs/data-source-policy.md`.

## 9. Valuation philosophy

Five separate outputs: (1) model valuation (forward DCF, earnings method,
scenarios), (2) market-implied expectations (reverse DCF as a primary decision
tool), (3) valuation map derived from model values, (4) earnings / revenue
catch-up scenarios, (5) investment action as an evidence-based judgment.
No default "forward DCF × 80–90% = buy range". WATCH never means "wait for the
stock to fall to X". Policy: `docs/recommendation-policy.md`.

## 10. Expectation Gap

Per metric, compare market-implied assumptions (solved from price) with the
internal base and bull cases: at/below base, above base within bull, or above
bull; then track whether the gap is widening, stable or narrowing between
reviews (`research_state.py expectation-gap`). It is not collapsed into one
score. Example (AAPL, 2026-10-11): implied ~14.8% ten-year growth vs 8% base and
12% bull → above the bull case. PL: not quantified because a unique reverse DCF
could not be supported; recorded qualitatively.

## 11. NotebookLM (optional)

Reading and Q&A layer only; the repo is canonical. `docs/notebooklm-optional-workflow.md`.

## 12. TradingView (optional)

`research-monitor` can emit alert text or Pine snippets from
`monitoring/rules.yaml` price levels. Alerts mean "reassess", never "trade".

## 13. Codex / Claude coexistence

Same `research/`, `scripts/`, `docs/`, skills. Codex enters via `AGENTS.md` and
`.agents/skills/` symlinks; Claude via `CLAUDE.md`, `.claude/skills/` and
`.claude/commands/`. `docs/dual-codex-claude-usage.md`.

## 14. Example commands

```text
/watch-stock PL
/update-stock PL
/init-stock PLTR
/deep-stock AAPL
/monthly-research
/scan-research          # Level 4: new events → classifier → queue → priorities
/research-queue         # Level 4: which company to research first, and the workflow
/research-dashboard     # Level 4: watchlist command center
/stale-research         # Level 4: stale research detector
```

```bash
uv run --project .claude/skills/finance-skill/scripts python scripts/price_reaction.py fetch PL
python3 scripts/research_state.py status PL
python3 scripts/research_state.py change-report AAPL
python3 scripts/research_state.py check-rules PL
python3 scripts/research_state.py catch-up PL
python3 scripts/research_state.py expectation-gap AAPL
python3 scripts/price_reaction.py analyze PL research/PL/market/events.csv --write
python3 scripts/research_command_center.py scan --refresh --skip-prices
python3 scripts/research_command_center.py queue
python3 scripts/research_command_center.py dashboard
python3 -m unittest discover -s tests
```

## 15. Level 3 implementation (2026-10-13)

The engine below turns the state containers into a continuously accumulating
research record. Every script is local-first; network calls are limited to SEC
(finance-skill client, `.env` user agent) and price refreshes.

| Capability | Script | Output (`research/<TICKER>/…`) |
|---|---|---|
| Baseline builder | `build_fundamental_history.py` | `financials/history.json`, `coverage.json`, merged `historical.csv` |
| Assumption vs history | `assumption_history_check.py` | `valuation/assumption-check.{json,md}` |
| Management history | `build_management_history.py` | `management/statements.json`, `guidance.json`, `reported-kpis.json`, `changes.md`, `market/events.csv` |
| Promise lifecycle | `build_management_history.py` | `management/promises.json` |
| State snapshots + diff | `state_diff.py`, `research_state.py snapshot-state / change-report` | `snapshots/<date>.json`, `reports/<date>-change-report.md` |
| Valuation history | `build_valuation_history.py` | `valuation/historical-multiples.csv`, `historical-percentiles.json`, `market/fundamental-price-timeline.csv` |
| Expectation-gap history | `research_state.py record-gap` | `valuation/expectation-gap-history.csv` |
| Benchmark-adjusted reactions | `price_reaction.py analyze` / `fetch-benchmark` | `market/event-reactions.csv`, `research/benchmarks/SPY/prices.csv` |
| INIT / UPDATE | `research_pipeline.py init|update` | everything above + baseline / change report |
| Monthly review | `monthly_research_review.py` | `research/reviews/YYYY-MM-monthly-review.md` |
| Past state without hindsight | `backfill_state_snapshots.py` | `snapshots/<date>.json` (`retrospective: true` or from git) |

**Baseline builder.** A mapping layer lists candidate us-gaap tags per metric
(e.g. revenue: `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`,
`SalesRevenueNet`); the tag used is stored per period and a fallback is flagged.
Only 10-K / 10-Q (and amendments) count; duplicates resolve to the latest filed
fact (amendments and restated comparatives win); an `as_of` cutoff hides later
filings. Durations are classified by length so YTD values are never stored as
quarters; a standalone quarter is derived (YTD minus prior YTD, or cumulative
minus contiguous standalone quarters, same fiscal-year start) only when valid,
with the derivation recorded. Missing values stay null; nothing is zero-filled
or interpolated. Company KPIs (backlog, ARR, bookings, units, subscribers) are
filled only from a configured extension tag (`financials/tag-overrides.json`).
On AAPL it reproduces all values of the AAPL-specific `extract_aapl.py`
(kept, not deleted).

**Management history.** EX-99.1 earnings releases (8-K Item 2.02) are quoted
verbatim by topic (demand, customers, backlog/RPO, guidance, capex, margins,
product launch, customer qualification, constraints, cash flow, dilution); the
Outlook section is parsed into guidance ranges; `changes.md` compares guidance
raised / maintained / lowered and wording per topic over up to eight quarters.
Wording changes are labelled low-confidence heuristics, never fundamentals.

**Promise lifecycle.** Each guided metric becomes a promise (`pending`); once the
period is reported it is resolved against SEC actuals (revenue, capex, GAAP
margin) or company-reported non-GAAP figures (`delivered`,
`partially_delivered`, `missed`; capex is judged as a spending plan, under or
over), or `superseded` by later guidance. Counts carry a caveat; no credibility
score.

**State diff.** A snapshot freezes financials (latest quarter, TTM), management
(guidance, tone, promises), thesis (status + evidence fingerprint), valuation
(price, scenarios, zone, historical percentiles), expectation gap, rule states,
action / confidence and catalysts. `change-report` diffs the last two snapshots
across Financials, Management, Promises, Thesis, Valuation, Expectation gap and
Monitoring; thesis transitions use an explicit mapping (e.g. supported →
improving is neutral). Monitoring evaluates fundamental, market (price crossed a
reassessment level since the last reviewed price) and thesis-invalidation rules;
a trigger only means REASSESS.

**Valuation history.** Month-end and pre/post-earnings price × cover-page shares,
EV = market cap + debt − cash/investments, TTM revenue / EBIT / net income /
FCF from facts filed on or before each date (no look-ahead). EV/Sales,
EV/EBIT, P/E, P/FCF (null when not meaningful) and 1Y / 3Y / since-listing
percentiles, flagged when data is thin. The fundamental-price timeline aligns
each earnings release with price before / after, SPY-adjusted moves and the
quarter's fundamentals.

**Monthly review.** Compares each company's latest snapshot with its last one
before the month: thesis moves, gap widening / narrowing, promises, newly
triggered rules; High / Medium / Low priority by transparent rules; five tasks.

**Level assessment (2026-10-13): LEVEL 3** — generic baseline works (PL, AAPL,
RKLB), PL has multi-period state (2 retrospective + 3 recorded snapshots), UPDATE
produces a multi-domain diff, valuation / expectation-gap / thesis / promise
histories persist, and tests pass. Not LEVEL 4: thesis judgment and long-form
reports still need an analyst, management extraction is heuristic, transcripts
and company KPIs outside XBRL are not automated.


## 16. Level 4 — Research Command Center（2026-10-13）

核心問題從「這家公司值多少？」變成「**哪家公司現在最值得我研究？發生了什麼？是否改變 thesis？下一步應該做什麼？**」。
Level 4 疊在 Level 3 之上：不重寫 INIT / UPDATE / MONTHLY、不取代 state schema、不新增估值模型；
只新增 `config/`、`research/queue/`、`research/calendar/`、`research/dashboard/` 與每家公司的
`config/kpis.yaml`、`monitoring/scan-state.json`。自動化 ≠ 自動交易：所有觸發只代表 REASSESS，
沒有任何輸出是 BUY / SELL 指令。

```
                    DATA / EVENTS
                         │
        ┌────────────────┼────────────────┐
        │                │                │
      SEC             Market          Company IR   (+ research state: rules, promises, gap, percentiles;
        │                │                │            macro only when linked to the thesis)
        └────────────────┼────────────────┘
                         ▼
                  EVENT DETECTOR          research_event_detector.py（增量：scan-state）
                         │
                  EVENT CLASSIFIER        research_event_classifier.py（A / B / C / D）
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
     Research Queue              Immediate Alert（= REASSESS，不是下單）
     research_queue.py
            │
            ▼
      Priority Engine             research_priority.py（透明規則 + 理由）
            │
    ┌───────┼────────┐
    ▼       ▼        ▼
 HIGH     MEDIUM     LOW
    │
    ▼
 Existing Level-3 /update-stock（research_pipeline.py update；完成後關閉該公司 A / B queue items）
    │
    ▼
  State Diff（state_diff.py）
    │
    ▼
 Research Command Center（research_dashboard.py → research/dashboard/current.md）
```

| 元件 | Script | 輸出 |
|---|---|---|
| KPI Registry | `kpi_registry.py` + `config/kpi-registry/{common,software,semiconductors,space,biotech,banks,consumer}.yaml` + `research/<T>/config/kpis.yaml` | `financials/kpi-history.csv`、`kpi-coverage.json` |
| Management Semantic Intelligence | `management_semantic_diff.py` | `management/claims.json`、`semantic-diff.{json,md}` |
| Guidance-vs-Actual Engine | `guidance_tracker.py` | `management/promises.json`（lifecycle 欄位）、`guidance-vs-actual.{json,md}` |
| Research Event Queue | `research_event_detector.py`、`research_queue.py` | `research/queue/current.json`、`archive/` |
| Event Classifier | `research_event_classifier.py` | category / severity / required_workflow / reason |
| Priority Engine | `research_priority.py` | `research/queue/priorities.json`、`priority-history.csv` |
| Catalyst Calendar | `catalyst_calendar.py` | `research/calendar/upcoming.csv` |
| Stale Research Detector | `stale_research.py` | `research/dashboard/stale-research.{json,md}` |
| Research confidence | `research_confidence.py` | dashboard 內的可解釋組成 |
| Research Command Center | `research_dashboard.py`、`research_command_center.py` | `research/dashboard/current.{md,json}` |
| Enhanced Monthly Review | `monthly_research_review.py`（第 12–22 段） | `research/reviews/YYYY-MM-monthly-review.md` |
| P2（選用） | `tradingview_alert_export.py`、`notebooklm_export.py` | `monitoring/tradingview-alerts.md`、`exports/notebooklm-sources.md` |

**Event queue。** Detector 只看 scan-state 之後的新東西：SEC（10-Q、10-K、8-K 依 item、DEF 14A、
Form 4 / 144 合併為一筆、S-3 / 424B 增資、S-4 / 425 併購）、issuer 公告（`market/events.csv`）、
guidance 上修 / 下修、市場（單日大漲跌、異常量、大回檔、52 週新高 / 新低、相對研究價格的大幅變動）、
state 變化（監控規則 / thesis invalidation 新觸發或仍未處理、承諾 missed / delayed、時程延後、
expectation gap 與歷史百分位顯著變動）。Macro 只收 `macro_links` 內、和 thesis 明確相關的主題。
第一次掃描以「上次研究檢視日」為起點（最多回看 `first_scan_lookback_days`）；已併入 state 的
10-Q / 10-K 不再列為事件；`--since` 可做不寫 state 的重播。Queue item 狀態：pending → processing →
completed / dismissed / superseded；同公司有待處理的 FULL_UPDATE 時，較早的 C / D 自動 superseded。

**Classifier。** A FULL_UPDATE_REQUIRED（新 10-Q / 10-K、財報、guidance 下修、thesis invalidation）
→ `/update-stock`；B TARGETED_UPDATE（合約、產品、經營層、增資、併購、監控觸發、承諾、gap / 百分位）
→ 擁有該 state 的 skill；C MARKET_REACTION_ONLY（無新文件的價量事件）→ `market-reaction`，除非 state 改變
否則不重跑 DCF；D LOW_PRIORITY_INFORMATIONAL（例行 Form 4 / 144、proxy）→ 只記錄。

**Priority engine。** 透明規則（見 `research_priority.py` docstring）：事件嚴重度、thesis 重要性
（對應到 high importance component 且證據 HIGH → 升級）、證據品質（LOW → 降一級，只降信心不判偽）、
上次檢視距今（過久 → B / C 升一級）、研究信心（tie-break）。公司層級 = 最高的未處理事件，
有未吸收的新財報時一律 HIGH；watchlist 的 `priority_override` 最後套用並標示。跨公司只比較 state、
趨勢、優先順序與信心，不比較跨產業的原始倍數。

**KPI registry。** 三層：common → sector → company。缺資料寫 `unavailable`（不填 0）；單位不符拒收；
RPO、backlog、ARR 是不同 concept，`backlog` concept 不能用 `rpo` metric 填。公司自訂指標保留原名與定義。

**Semantic management analysis。** 不是 LLM：以結構化 claims（point / range / qualitative guidance、
timing promise、operational milestone）逐維度比較（quantitative guidance、timing、confidence、
bottleneck、demand、capex、margin、product launch），輸出 FACT / CHANGE / INTERPRETATION / CONFIDENCE。
只有措辭變化 → low confidence，且不推論「基本面惡化」。「Margins should improve in H2」保持質化。

**Guidance tracking。** 解析 Level 3 漏掉的條列式 guidance（例：RKLB 每季「Guidance … expects: •」）；
每個 guided metric 必須在 `config/kpis.yaml` → `guidance_metrics` 記錄公司定義與比較口徑。
Audit rule：公司定義與可量測的 actual 不一致或未記錄 → `not_evaluable`，不自動結案。新增狀態
`delayed`、`not_evaluable`，以及 `metric_definition`、`comparison_basis`、`resolution_confidence`、
`actual_source` 欄位。沒有 guidance 時明確輸出 “No explicit evaluable management guidance found.”。

**Dashboard / catalyst calendar / stale research / monthly review。** Dashboard 表格欄位：Ticker、Action、
Priority、Thesis trend、Valuation（相對自身估值地圖）、Expectation gap、Triggers、Next catalyst、Last review，
並回答六個問題（thesis 改善 / 惡化最大、gap 縮小最多、估值相對自身變便宜、股價漲但基本面沒跟上、
研究 stale）。Calendar 對未知日期只給月份 / 季度 / 年並標信心；法規申報期限標為 upper bound。
Stale 門檻在 `config/research-policy.yaml`（依 research_role 調整）。Monthly review 新增第 12–22 段。

**Draft 標示。** 自動產生的 thesis、估值假設、KPI mapping、promise resolution、語意解讀，只要信心不高
就標 `draft_auto` 與 `review_required: true`，不會默默變成分析師定稿。

**增量。** 每家公司的 `monitoring/scan-state.json` 記錄 `last_checked`、`last_filing`、
`last_price_update`、`last_management_update`（與已看過的 accession、已觸發規則、承諾狀態），
scan 只抓增量；UPDATE 仍只抓比 state 新的 SEC 文件。

使用方式見 `docs/level4-operating-guide.md`；實作與驗證結果見 `docs/level4-implementation-report.md`。
