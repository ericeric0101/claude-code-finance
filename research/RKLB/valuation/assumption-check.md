# RKLB 假設 vs 歷史檢查（Assumption vs History）

營收歷史（Calculation）：3Y CAGR 41.82%、5Y CAGR 76.47%、最近 FY 成長 37.96%、TTM 成長 52.53%、最近 8 季 YoY 範圍 [32.13, 120.68]、中位數 51.44%。

| 情境 | 假設 | 數值 | 分類 | 解讀 |
|---|---|---|---|---|
| bear | revenue_cagr_5y | 20.0% | Below historical（conservative） | bear revenue_cagr_5y 20.0% is more conservative than long-run history (long-run: cagr_5y 76.5%, cagr_3y 41.8%; recent: ttm_growth 52.5%, median_8q_yoy 51.4%) -> Below historical / conservative. |
| bear | fcf_margin_y5 | 6.0% | Materially above historical（very aggressive） | bear fcf_margin_y5 6.0% is materially beyond both long-run history and recent trajectory (long-run: avg_3y -47.6%; recent: ttm -48.2%, latest_fy -53.5%) -> Materially above historical / very aggressive. |
| base | revenue_cagr_5y | 40.0% | Near historical（reasonable） | base revenue_cagr_5y 40.0% is in line with long-run history (long-run: cagr_5y 76.5%, cagr_3y 41.8%; recent: ttm_growth 52.5%, median_8q_yoy 51.4%) -> Near historical / reasonable. |
| base | fcf_margin_y5 | 10.0% | Materially above historical（very aggressive） | base fcf_margin_y5 10.0% is materially beyond both long-run history and recent trajectory (long-run: avg_3y -47.6%; recent: ttm -48.2%, latest_fy -53.5%) -> Materially above historical / very aggressive. |
| bull | revenue_cagr_5y | 56.0% | Near historical（reasonable） | bull revenue_cagr_5y 56.0% is in line with long-run history (long-run: cagr_5y 76.5%, cagr_3y 41.8%; recent: ttm_growth 52.5%, median_8q_yoy 51.4%) -> Near historical / reasonable. |
| bull | fcf_margin_y5 | 15.0% | Materially above historical（very aggressive） | bull fcf_margin_y5 15.0% is materially beyond both long-run history and recent trajectory (long-run: avg_3y -47.6%; recent: ttm -48.2%, latest_fy -53.5%) -> Materially above historical / very aggressive. |

## 歷史比率（年度，%）

| 指標 | FY2020 | FY2021 | FY2022 | FY2023 | FY2024 | FY2025 | TTM |
|---|---|---|---|---|---|---|---|
| gross_margin_pct | -33.61 | -3.04 | 9.0 | 21.02 | 26.63 | 34.43 | 37.26 |
| operating_margin_pct | -156.29 | -163.97 | -64.08 | -72.74 | -43.51 | -38.03 | -29.06 |
| fcf_margin_pct | -150.39 | -156.64 | -70.59 | -62.79 | -26.59 | -53.47 | -48.25 |
| sbc_pct_revenue | 12.0 | 52.31 | 26.37 | 21.86 | 13.02 | 11.81 | 10.61 |
| capex_pct_revenue | 71.45 | 41.29 | 20.1 | 22.37 | 15.38 | 25.97 | 19.33 |

稀釋股數：3Y CAGR 4.41%、最近 FY YoY 7.0%、最近一季 YoY 22.25%。

> History is evidence, not a ceiling: a forward 5-year assumption can exceed history if new evidence supports it. FCF history may include working-capital timing (e.g. customer prepayments).
