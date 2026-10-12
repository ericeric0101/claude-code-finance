# RKLB 基準研究狀態（Baseline）— 2026-10-13

> 自動建立的基準狀態：歷史數字為 SEC 一級來源（Fact / Calculation）；thesis、估值情境與監控規則為 auto-draft（Assumption），需研究員複核後才代表研究判斷。此文件不是買賣建議。

## 資料覆蓋
- 年度：FY2020, FY2021, FY2022, FY2023, FY2024, FY2025（≥5 年：True）
- 季度：Q3 FY2023, Q4 FY2023, Q1 FY2024, Q2 FY2024, Q3 FY2024, Q4 FY2024, Q1 FY2025, Q2 FY2025, Q3 FY2025, Q4 FY2025, Q1 FY2026, Q2 FY2026（≥8 季：True）
- 公司特定 KPI：backlog / ARR / bookings / units / subscribers have no us-gaap tag; null unless an extension tag is configured in tag-overrides.json

## 歷史基本面（年度，USD m / %）

| 期間 | 營收 | YoY | 毛利率 | 營業利益率 | FCF | SBC/營收 | 稀釋股數(m) |
|---|---|---|---|---|---|---|---|
| FY2020 | 35.2 | n/a | -33.6 | -156.3 | -52.9 | 12.0 | 75.4 |
| FY2021 | 62.2 | 77.0 | -3.0 | -164.0 | -97.5 | 52.3 | 209.9 |
| FY2022 | 211.0 | 239.0 | 9.0 | -64.1 | -148.9 | 26.4 | 466.2 |
| FY2023 | 244.6 | 15.9 | 21.0 | -72.7 | -153.6 | 21.9 | 481.8 |
| FY2024 | 436.2 | 78.3 | 26.6 | -43.5 | -116.0 | 13.0 | 495.9 |
| FY2025 | 601.8 | 38.0 | 34.4 | -38.0 | -321.8 | 11.8 | 530.7 |

## 假設 vs 歷史

- bear revenue_cagr_5y 20.0% is more conservative than long-run history (long-run: cagr_5y 76.5%, cagr_3y 41.8%; recent: ttm_growth 52.5%, median_8q_yoy 51.4%) -> Below historical / conservative.
- bear fcf_margin_y5 6.0% is materially beyond both long-run history and recent trajectory (long-run: avg_3y -47.6%; recent: ttm -48.2%, latest_fy -53.5%) -> Materially above historical / very aggressive.
- base revenue_cagr_5y 40.0% is in line with long-run history (long-run: cagr_5y 76.5%, cagr_3y 41.8%; recent: ttm_growth 52.5%, median_8q_yoy 51.4%) -> Near historical / reasonable.
- base fcf_margin_y5 10.0% is materially beyond both long-run history and recent trajectory (long-run: avg_3y -47.6%; recent: ttm -48.2%, latest_fy -53.5%) -> Materially above historical / very aggressive.
- bull revenue_cagr_5y 56.0% is in line with long-run history (long-run: cagr_5y 76.5%, cagr_3y 41.8%; recent: ttm_growth 52.5%, median_8q_yoy 51.4%) -> Near historical / reasonable.
- bull fcf_margin_y5 15.0% is materially beyond both long-run history and recent trajectory (long-run: avg_3y -47.6%; recent: ttm -48.2%, latest_fy -53.5%) -> Materially above historical / very aggressive.

## 估值（auto-draft）
- 價格 68.21（2026-10-09 close）
- 情境：{"five-year scenario DCF (auto-draft)": {"bear": 4.43, "base": 11.37, "bull": 33.38}}
- 位置：above all modeled bull values
- Reverse DCF implied 5Y revenue CAGR：1.0891
- 歷史 ev_sales：current 50.09；1Y pct 23.1；3Y pct 73.0；since listing 80.4
- 歷史 ev_ebit：current None；1Y pct None；3Y pct None；since listing None
- 歷史 pe：current None；1Y pct None；3Y pct None；since listing None
- 歷史 p_fcf：current None；1Y pct None；3Y pct None；since listing None

## 管理層與承諾
- 承諾計數：{}（Counts only; not a credibility score. Guidance ranges are set by management and mostly quantitative; a small sample says little.）
- 逐季措辭比較見 management/changes.md

## 監控規則（觸發 = REASSESS）
- [fundamental] revenue_growth: not_triggered
- [fundamental] dilution_yoy: triggered
- [fundamental] gross_margin: not_triggered
- [fundamental] backlog_yoy: not_triggered
- [fundamental] capex_intensity: not_triggered
- [market] reassess_price_4.43: not_triggered
- [market] reassess_price_11.37: not_triggered
- [market] reassess_price_33.38: not_triggered
- [invalidation] revenue_decline_two_quarters: not_triggered
- [invalidation] dilution_above_5pct: triggered
- [invalidation] gross_margin_below_8q_low: not_triggered
- [invalidation] rpo_decline_yoy: not_triggered

## INIT 步驟紀錄
- 1. init state: ok
- 2. acquire SEC data: ok
- 3. build 5Y + 8Q history: ok
- 4. historical prices: ok
- 5. earnings event list: ok
- 6. management history: ok
- 7. initial promise tracker: ok
- 8. stock-analysis QA: ok
- 9. thesis: auto-draft written
- 10. valuation: auto-draft written
- 11. assumption-vs-history check: ok
- 12. historical valuation: ok
- 13. monitoring rules: auto-draft written
- 14. snapshot: ok
