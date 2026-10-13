# Research Command Center（2026-10-13）

> 研究優先順序儀表板。Action 取自 thesis/current.yaml；觸發 = REASSESS，不是買賣指令；估值只和公司自己的估值地圖 / 歷史比較，不跨產業比較 EV/Sales。

| Ticker | Action | Priority | Thesis trend | Valuation | Expectation gap | Triggers | Next catalyst | Last review |
|---|---|---|---|---|---|---|---|---|
| PL | WATCH | HIGH | Stable | Demanding（介於 base 與 bull） | Wide（market 36.1% vs base 25.0%，stable） | 5 | Convertible note conversion window 2026-08-01 to（2026-10-31） | 0 天前 |
| AAPL | WATCH | HIGH | Stable | Expensive（高於所有 bull 值） | Wide（market 14.8% vs base 8.0%，no prior state） | 2 | iPhone Duo preorders 2026-10-16 and availability（2026-10-23） | 0 天前 |
| RKLB | WATCH（draft_auto） | MEDIUM | Baseline（無前期） | Expensive（高於所有 bull 值） | Wide（market 108.9% vs base 40.0%，no prior state） | 2 | Company target: Neutron first launch by end of Q（Q4 2026） | 0 天前 |

## Command center 問答

- Thesis 改善最大：無（本期沒有 thesis 狀態改善）
- Thesis 惡化最大：無（本期沒有 thesis 狀態惡化）
- Expectation gap 縮小最多：無（gap 未縮小或無前期）
- 估值變便宜（相對自身研究價格 / 估值地圖）：PL（最新收盤較研究價格 -7.1%，相對自身估值地圖：Demanding（介於 base 與 bull））；RKLB（最新收盤較研究價格 -3.7%，相對自身估值地圖：Expensive（高於所有 bull 值））
- 股價上漲但基本面未跟上：無
- 研究已 stale：無

## 優先順序理由

- **PL**（HIGH）：standing_trigger: multiple monitoring rules triggered (3 distinct conditions)
- **AAPL**（HIGH）：standing_trigger: fundamental rule 'receivables_gap' still triggered since 2026-10-13 → REASSESS still open；standing_trigger: invalidation rule 'receivables_inventory_build' still triggered since 2026-10-13 → REASSESS still open
- **RKLB**（MEDIUM）：promise_delayed: promise RKLB-milestone-neutron-first_launch-2025-02-27 delayed (target moved H2 2025 → Q4 2026 (2026-02-26))；standing_trigger: fundamental rule 'dilution_yoy' still triggered since 2026-10-13 → REASSESS still open；standing_trigger: invalidation rule 'dilution_above_5pct' still triggered since 2026-10-13 → REASSESS still open

## Research confidence（可解釋組成，非公司評分）

- **PL** overall: medium
  - financial_history: strong — strong financial history (6 FY, 12 quarters from SEC filings)
  - management_history: strong — management history over 10 periods with 68 guidance records
  - kpi_coverage: strong — all required KPIs available; company-defined KPIs: non_gaap_gross_margin, adjusted_ebitda, rpo_12m_conversion
  - valuation_agreement: weak — single valuation method; reverse DCF illustrative (low confidence) → high valuation uncertainty
  - evidence_quality: strong — 14 of 16 thesis evidence lines are labelled Fact with sources
  - unresolved_promises: strong — 52 promises resolved, 8 open
  - stale_data: strong — state is current
- **RKLB** overall: low
  - financial_history: strong — strong financial history (6 FY, 12 quarters from SEC filings)
  - management_history: strong — management history over 9 periods with 83 guidance records
  - kpi_coverage: strong — all required KPIs available; company-defined KPIs: launch_cadence
  - valuation_agreement: weak — valuation is an auto-draft (history-anchored assumptions)
  - evidence_quality: weak — thesis is an auto-draft (draft_auto); evidence not analyst-reviewed
  - unresolved_promises: adequate — 25 promises resolved, 60 open (50 not evaluable: definition / actual-basis gaps)
  - stale_data: strong — state is current
- **AAPL** overall: medium
  - financial_history: strong — strong financial history (6 FY, 12 quarters from SEC filings)
  - management_history: adequate — management statements over 9 periods; limited guidance history
  - kpi_coverage: strong — all required KPIs available; company-defined KPIs: services_revenue, services_mix, capex
  - valuation_agreement: adequate — 2 methods, base values 194–242; methods broadly agree; but the analyst's valuation confidence is low
  - evidence_quality: strong — 8 of 13 thesis evidence lines are labelled Fact with sources
  - unresolved_promises: adequate — 1 promises resolved, 1 open
  - stale_data: strong — state is current

## Triggered rules（REASSESS）

- PL: rpo_vs_fiscal_year_end, capex_intensity, dilution_yoy, capex_heavy_with_negative_fcf, dilution_above_5pct
- RKLB: dilution_yoy, dilution_above_5pct
- AAPL: receivables_gap, receivables_inventory_build

## Guidance vs actual / KPI coverage

- PL: guidance {'delivered': 44, 'missed': 6, 'partially_delivered': 2, 'superseded': 8, 'pending': 8}；KPI sector space，required unavailable 無
- RKLB: guidance {'not_evaluable': 50, 'delivered': 19, 'partially_delivered': 5, 'pending': 10, 'delayed': 1}；KPI sector space，required unavailable 無
- AAPL: guidance No explicit evaluable management guidance found.；KPI sector consumer，required unavailable 無

## Research OS Quality（品質評估層；不影響 thesis / priority）

- Reviewed events: 0
- Pending review: 8（required 3）
- False positives: 0
- False negatives: 0
- Priority agreement: 0/0（insufficient_sample）
- Manual corrections: 0
- Largest weakness: 尚無（無已 review 的錯誤）
- 完整細節：`python3 scripts/quality_summary.py --month YYYY-MM`

## Open research queue（10）

| Priority | Ticker | Cat | Event | Date | Workflow | Reason | Status |
|---|---|---|---|---|---|---|---|
| HIGH | AAPL | B | standing_trigger | 2026-10-13 | thesis-monitor / research-monitor: the REASSESS is still open — record | fundamental rule 'receivables_gap' still triggered since 2026-10-13 → REASSESS still open | pending |
| HIGH | AAPL | B | standing_trigger | 2026-10-13 | thesis-monitor / research-monitor: the REASSESS is still open — record | invalidation rule 'receivables_inventory_build' still triggered since 2026-10-13 → REASSES | pending |
| HIGH | PL | B | standing_trigger | 2026-10-13 | thesis-monitor / research-monitor: the REASSESS is still open — record | fundamental rule 'rpo_vs_fiscal_year_end' still triggered since 2026-10-13 → REASSESS stil | pending |
| HIGH | PL | B | standing_trigger | 2026-10-13 | thesis-monitor / research-monitor: the REASSESS is still open — record | fundamental rule 'capex_intensity' still triggered since 2026-10-13 → REASSESS still open | pending |
| HIGH | PL | B | standing_trigger | 2026-10-13 | thesis-monitor / research-monitor: the REASSESS is still open — record | fundamental rule 'dilution_yoy' still triggered since 2026-10-13 → REASSESS still open | pending |
| HIGH | PL | B | standing_trigger | 2026-10-13 | thesis-monitor / research-monitor: the REASSESS is still open — record | invalidation rule 'capex_heavy_with_negative_fcf' still triggered since 2026-10-13 → REASS | pending |
| HIGH | PL | B | standing_trigger | 2026-10-13 | thesis-monitor / research-monitor: the REASSESS is still open — record | invalidation rule 'dilution_above_5pct' still triggered since 2026-10-13 → REASSESS still  | pending |
| MEDIUM | RKLB | B | promise_delayed | 2026-10-13 | management-change: timing slip; thesis-monitor for the affected milest | promise RKLB-milestone-neutron-first_launch-2025-02-27 delayed (target moved H2 2025 → Q4  | pending |
| MEDIUM | RKLB | B | standing_trigger | 2026-10-13 | thesis-monitor / research-monitor: the REASSESS is still open — record | fundamental rule 'dilution_yoy' still triggered since 2026-10-13 → REASSESS still open | pending |
| MEDIUM | RKLB | B | standing_trigger | 2026-10-13 | thesis-monitor / research-monitor: the REASSESS is still open — record | invalidation rule 'dilution_above_5pct' still triggered since 2026-10-13 → REASSESS still  | pending |
