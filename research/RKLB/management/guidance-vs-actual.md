# RKLB Guidance vs Actual（2026-10-13）

> draft_auto：自動結案只在公司 metric 定義與實際值口徑一致時進行；口徑不一致或未記錄定義 → not_evaluable。Spending plan（capex / opex）偏離區間是「與計畫不同」，少花不等於負面。

狀態計數：delayed 1, delivered 19, not_evaluable 50, partially_delivered 5, pending 10

| Promise | Metric | Period | Guided | Actual | Status | Basis | Confidence | Rule |
|---|---|---|---|---|---|---|---|---|
| RKLB-2025-02-27-q1-net_interest | net_interest | Q1 FY2025 | 2.7–2.7 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-02-27-q1-non_gaap_operating_expenses | non_gaap_operating_expenses | Q1 FY2025 | 77.0–79.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-02-27-q1-revenue | revenue | Q1 FY2025 | 117.0–123.0 USD millions | 122.569 | delivered | gaap_match | high | at or above low end of range |
| RKLB-2025-02-27-q1-sbc | sbc | Q1 FY2025 | 16.0–18.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-milestone-neutron-first_launch-2025-02-27 | operational milestone | H2 2025 | H2 2025 | — | delayed | timing claim (same subject and milestone) | medium | target moved H2 2025 → Q4 2026 (2026-02-26) |
| RKLB-2025-05-08-q2-basic_shares_guided | basic_shares_guided | Q2 FY2025 | 514.0–514.0 millions of shares | 515.086631 | not_evaluable | definition_mismatch | — | metric definition mismatch: basic weighted average common shares outstanding, from 2025 releases INCLUDING ~41-51m Serie |
| RKLB-2025-05-08-q2-ebitda | adjusted_ebitda | Q2 FY2025 | -30.0–-28.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-05-08-q2-gaap_operating_expenses | gaap_operating_expenses | Q2 FY2025 | 96.0–98.0 USD millions | 106.027 | partially_delivered | calculated_gaap | medium | overspent vs plan by 8%; a spending-plan deviation, not by itself a negative signal |
| RKLB-2025-05-08-q2-gaapgm | gross_margin | Q2 FY2025 | 30.0–32.0 % | 32.102866 | delivered | gaap_match | high | at or above low end of range |
| RKLB-2025-05-08-q2-gm | non_gaap_gross_margin | Q2 FY2025 | 34.0–36.0 % | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-05-08-q2-net_interest | net_interest | Q2 FY2025 | 3.1–3.1 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-05-08-q2-non_gaap_operating_expenses | non_gaap_operating_expenses | Q2 FY2025 | 82.0–84.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-05-08-q2-revenue | revenue | Q2 FY2025 | 130.0–140.0 USD millions | 144.498 | delivered | gaap_match | high | at or above low end of range |
| RKLB-2025-05-08-q2-sbc | sbc | Q2 FY2025 | 13.0–14.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-08-07-q3-basic_shares_guided | basic_shares_guided | Q3 FY2025 | 528.0–528.0 millions of shares | 528.72598 | not_evaluable | definition_mismatch | — | metric definition mismatch: basic weighted average common shares outstanding, from 2025 releases INCLUDING ~41-51m Serie |
| RKLB-2025-08-07-q3-ebitda | adjusted_ebitda | Q3 FY2025 | -23.0–-21.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-08-07-q3-gaap_operating_expenses | gaap_operating_expenses | Q3 FY2025 | 104.0–109.0 USD millions | 116.283 | partially_delivered | calculated_gaap | medium | overspent vs plan by 7%; a spending-plan deviation, not by itself a negative signal |
| RKLB-2025-08-07-q3-gaapgm | gross_margin | Q3 FY2025 | 35.0–37.0 % | 36.957699 | delivered | gaap_match | high | at or above low end of range |
| RKLB-2025-08-07-q3-gm | non_gaap_gross_margin | Q3 FY2025 | 39.0–41.0 % | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-08-07-q3-net_interest | net_interest | Q3 FY2025 | 1.3–1.3 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-08-07-q3-non_gaap_operating_expenses | non_gaap_operating_expenses | Q3 FY2025 | 86.0–91.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-08-07-q3-revenue | revenue | Q3 FY2025 | 145.0–155.0 USD millions | 155.08 | delivered | gaap_match | high | at or above low end of range |
| RKLB-2025-08-07-q3-sbc | sbc | Q3 FY2025 | 16.0–17.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-11-10-q4-basic_shares_guided | basic_shares_guided | Q4 FY2025 | 571.0–571.0 millions of shares | — | not_evaluable | definition_mismatch | — | metric definition mismatch: basic weighted average common shares outstanding, from 2025 releases INCLUDING ~41-51m Serie |
| RKLB-2025-11-10-q4-ebitda | adjusted_ebitda | Q4 FY2025 | -29.0–-23.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-11-10-q4-gaap_operating_expenses | gaap_operating_expenses | Q4 FY2025 | 122.0–128.0 USD millions | 119.274 | partially_delivered | calculated_gaap | medium | underspent vs plan by 2%; a spending-plan deviation, not by itself a negative signal |
| RKLB-2025-11-10-q4-gaapgm | gross_margin | Q4 FY2025 | 37.0–39.0 % | 37.980095 | delivered | gaap_match | medium | at or above low end of range |
| RKLB-2025-11-10-q4-gm | non_gaap_gross_margin | Q4 FY2025 | 43.0–45.0 % | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-11-10-q4-net_interest | net_interest | Q4 FY2025 | 3.5–3.5 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-11-10-q4-non_gaap_operating_expenses | non_gaap_operating_expenses | Q4 FY2025 | 107.0–113.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2025-11-10-q4-revenue | revenue | Q4 FY2025 | 170.0–180.0 USD millions | 179.652 | delivered | gaap_match | medium | at or above low end of range |
| RKLB-2025-11-10-q4-sbc | sbc | Q4 FY2025 | 15.0–17.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2026-02-26-q1-basic_shares_guided | basic_shares_guided | Q1 FY2026 | 605.0–605.0 millions of shares | 605.434642 | not_evaluable | definition_mismatch | — | metric definition mismatch: basic weighted average common shares outstanding, from 2025 releases INCLUDING ~41-51m Serie |
| RKLB-2026-02-26-q1-ebitda | adjusted_ebitda | Q1 FY2026 | -27.0–-21.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2026-02-26-q1-gaap_operating_expenses | gaap_operating_expenses | Q1 FY2026 | 120.0–126.0 USD millions | 132.462 | partially_delivered | calculated_gaap | medium | overspent vs plan by 5%; a spending-plan deviation, not by itself a negative signal |
| RKLB-2026-02-26-q1-gaapgm | gross_margin | Q1 FY2026 | 34.0–36.0 % | 38.180067 | delivered | gaap_match | high | at or above low end of range |
| RKLB-2026-02-26-q1-gm | non_gaap_gross_margin | Q1 FY2026 | 39.0–41.0 % | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2026-02-26-q1-net_interest | net_interest | Q1 FY2026 | 8.0–8.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2026-02-26-q1-non_gaap_operating_expenses | non_gaap_operating_expenses | Q1 FY2026 | 106.0–112.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2026-02-26-q1-revenue | revenue | Q1 FY2026 | 185.0–200.0 USD millions | 200.348 | delivered | gaap_match | high | at or above low end of range |
| RKLB-2026-02-26-q1-sbc | sbc | Q1 FY2026 | 16.0–18.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-milestone-neutron-first_launch-2026-02-26 | operational milestone | Q4 2026 | Q4 2026 | — | pending | timing claim (same subject and milestone) | — | target window not reached |
| RKLB-2026-05-07-q2-basic_shares_guided | basic_shares_guided | Q2 FY2026 | 629.0–629.0 millions of shares | 629.681803 | not_evaluable | definition_mismatch | — | metric definition mismatch: basic weighted average common shares outstanding, from 2025 releases INCLUDING ~41-51m Serie |
| RKLB-2026-05-07-q2-ebitda | adjusted_ebitda | Q2 FY2026 | -26.0–-20.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2026-05-07-q2-gaap_operating_expenses | gaap_operating_expenses | Q2 FY2026 | 138.0–144.0 USD millions | 142.09 | delivered | calculated_gaap | medium | within guided spending range |
| RKLB-2026-05-07-q2-gaapgm | gross_margin | Q2 FY2026 | 33.0–35.0 % | 36.133398 | delivered | gaap_match | high | at or above low end of range |
| RKLB-2026-05-07-q2-gm | non_gaap_gross_margin | Q2 FY2026 | 38.0–40.0 % | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2026-05-07-q2-net_interest | net_interest | Q2 FY2026 | 12.5–12.5 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2026-05-07-q2-non_gaap_operating_expenses | non_gaap_operating_expenses | Q2 FY2026 | 120.0–126.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2026-05-07-q2-revenue | revenue | Q2 FY2026 | 225.0–240.0 USD millions | 234.066 | delivered | gaap_match | high | at or above low end of range |
| RKLB-2026-05-07-q2-sbc | sbc | Q2 FY2026 | 19.0–21.0 USD millions | — | not_evaluable | comparison_basis_mismatch | — | company metric definition not recorded in config/kpis.yaml guidance_metrics |
| RKLB-2026-08-10-q3-basic_shares_guided | basic_shares_guided | Q3 FY2026 | 641.0–641.0 millions of shares | — | pending | definition_mismatch | — | period not yet reported |
| RKLB-2026-08-10-q3-ebitda | adjusted_ebitda | Q3 FY2026 | -23.0–-17.0 USD millions | — | pending | unverified | — | period not yet reported |
| RKLB-2026-08-10-q3-gaap_operating_expenses | gaap_operating_expenses | Q3 FY2026 | 143.0–149.0 USD millions | — | pending | calculated_gaap | — | period not yet reported |
| RKLB-2026-08-10-q3-gaapgm | gross_margin | Q3 FY2026 | 29.0–31.0 % | — | pending | gaap_match | — | period not yet reported |
| RKLB-2026-08-10-q3-gm | non_gaap_gross_margin | Q3 FY2026 | 35.0–37.0 % | — | pending | unverified | — | period not yet reported |
| RKLB-2026-08-10-q3-net_interest | net_interest | Q3 FY2026 | 21.0–21.0 USD millions | — | pending | unverified | — | period not yet reported |
| RKLB-2026-08-10-q3-non_gaap_operating_expenses | non_gaap_operating_expenses | Q3 FY2026 | 121.0–127.0 USD millions | — | pending | unverified | — | period not yet reported |
| RKLB-2026-08-10-q3-revenue | revenue | Q3 FY2026 | 250.0–265.0 USD millions | — | pending | gaap_match | — | period not yet reported |
| RKLB-2026-08-10-q3-sbc | sbc | Q3 FY2026 | 18.0–20.0 USD millions | — | pending | unverified | — | period not yet reported |
