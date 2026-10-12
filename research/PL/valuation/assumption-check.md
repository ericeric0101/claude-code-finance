# PL 假設 vs 歷史檢查（Assumption vs History）

營收歷史（Calculation）：3Y CAGR 17.18%、5Y CAGR 22.15%、最近 FY 成長 25.94%、TTM 成長 44.12%、最近 8 季 YoY 範圍 [4.59, 58.14]、中位數 26.37%。

| 情境 | 假設 | 數值 | 分類 | 解讀 |
|---|---|---|---|---|
| base | revenue_cagr_5y | 25.0% | Near historical（reasonable） | base revenue_cagr_5y 25.0% is in line with long-run history (long-run: cagr_5y 22.1%, cagr_3y 17.2%; recent: ttm_growth 44.1%, median_8q_yoy 26.4%) -> Near historical / reasonable. |
| base | fcf_margin_y5 | 20.0% | Above historical（aggressive） | base fcf_margin_y5 20.0% is above long-run history but within recent trajectory (long-run: avg_3y -17.1%; recent: ttm 5.2%, latest_fy 17.2%) -> Above historical / aggressive. |
| bull | revenue_cagr_5y | 35.0% | Above historical（aggressive） | bull revenue_cagr_5y 35.0% is above long-run history but within recent trajectory (long-run: cagr_5y 22.1%, cagr_3y 17.2%; recent: ttm_growth 44.1%, median_8q_yoy 26.4%) -> Above historical / aggressive. |
| bull | fcf_margin_y5 | 25.0% | Materially above historical（very aggressive） | bull fcf_margin_y5 25.0% is materially beyond both long-run history and recent trajectory (long-run: avg_3y -17.1%; recent: ttm 5.2%, latest_fy 17.2%) -> Materially above historical / very aggressive. |

## 歷史比率（年度，%）

| 指標 | FY2021 | FY2022 | FY2023 | FY2024 | FY2025 | FY2026 | TTM |
|---|---|---|---|---|---|---|---|
| gross_margin_pct | 22.78 | 36.75 | 49.15 | 51.18 | 57.18 | 56.05 | 55.42 |
| operating_margin_pct | -77.27 | -97.59 | -91.85 | -76.91 | -47.52 | -30.9 | -27.16 |
| fcf_margin_pct | -30.18 | -43.55 | -45.33 | -42.19 | -26.19 | 17.18 | 5.25 |
| sbc_pct_revenue | 12.38 | 31.98 | 39.5 | 25.89 | 19.84 | 17.87 | 16.53 |
| capex_pct_revenue | 26.62 | 11.38 | 6.67 | 19.22 | 20.31 | 26.48 | 25.84 |

稀釋股數：3Y CAGR 4.84%、最近 FY YoY 5.37%、最近一季 YoY 18.24%。

> History is evidence, not a ceiling: a forward 5-year assumption can exceed history if new evidence supports it. FCF history may include working-capital timing (e.g. customer prepayments).
