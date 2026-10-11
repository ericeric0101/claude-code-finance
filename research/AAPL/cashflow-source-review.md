# AAPL cash-flow source review

As of 2026-10-11 Asia/Taipei. Amounts USD million unless stated. Primary statement data were read from saved SEC HTML/text; cash bridge arithmetic independently reconciled. Latest accessible statement ends 2026-06-27; FY2026 annual statements are unavailable. This file supplies source inputs and accounting judgments, not an independent valuation.

## Annual and nine-month reconciliation

| Component | FY2021 | FY2022 | FY2023 | FY2024 | FY2025 | 9M2025 | 9M2026 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Net income | 94,680 | 99,803 | 96,995 | 93,736 | 112,010 | 84,544 | 101,464 |
| D&A | 11,284 | 11,104 | 11,519 | 11,445 | 11,698 | 8,571 | 9,973 |
| SBC addback | 7,906 | 9,038 | 10,833 | 11,688 | 12,863 | 9,680 | 10,523 |
| Other noncash | -4,921 | 1,006 | -2,227 | -2,266 | -89 | -1,748 | -2,037 |
| Trade AR cash effect | -10,125 | -1,823 | -1,688 | -3,788 | -6,682 | 5,685 | 8,316 |
| Vendor nontrade AR cash effect | -3,903 | -7,520 | 1,271 | -1,356 | -347 | 13,555 | 5,671 |
| Inventory cash effect | -2,642 | 1,484 | -1,618 | -1,046 | 1,400 | 1,223 | -5,461 |
| Other current/noncurrent assets cash effect | -8,042 | -6,499 | -5,684 | -11,731 | -9,197 | -6,116 | -16,266 |
| AP cash effect | 12,326 | 9,448 | -1,889 | 6,020 | 902 | -18,479 | -5,203 |
| Other current/noncurrent liabilities cash effect | 7,475 | 6,110 | 3,031 | 15,552 | -11,076 | -15,161 | 10,016 |
| Reported CFO | 104,038 | 122,151 | 110,543 | 118,254 | 111,482 | 81,754 | 116,996 |
| PP&E capex payments (+ magnitude) | 11,085 | 10,708 | 10,959 | 9,447 | 12,715 | 9,473 | 6,799 |
| Income taxes paid net (+ magnitude) | 25,385 | 19,573 | 18,679 | 26,102 | 43,369 | 37,332 | 26,555 |
| Equity award tax withholding (financing) | 6,556 | 6,223 | 5,431 | 5,441 | 5,960 | 5,719 | 6,462 |
| Derived narrow trade WC cash effect | -4,344 | 1,589 | -3,924 | -170 | -4,727 | 1,984 | 3,323 |
| Derived other-assets/liabilities cash effect | -567 | -389 | -2,653 | 3,821 | -20,273 | -21,277 | -6,250 |
| Derived all operating assets/liabilities effect | -4,911 | 1,200 | -6,577 | 3,651 | -25,000 | -19,293 | -2,927 |
| CFO minus PP&E capex (diagnostic) | 92,953 | 111,443 | 99,584 | 108,807 | 98,767 | 72,281 | 110,197 |

FY2021–2023: [FY2023 10-K, filed 2023-11-03](https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm), cash-flow statement p32. FY2024–2025: [FY2025 10-K, filed 2025-10-31](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm), p33. Both nine-month comparatives: [FY2026 Q3 10-Q, filed 2026-07-31](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm), p5. Fiscal 2023 has 53 weeks; other annual periods shown have 52.

## Exact trailing reconciliation

TTM = FY2025 + nine months FY2026 − nine months FY2025, ending 2026-06-27. Derived from reported periods; not a separately reported annual period.

| Component | TTM |
|---|---:|
| Net income | 128,930 |
| D&A | 13,100 |
| SBC addback | 13,706 |
| Other noncash | -378 |
| Trade AR cash effect | -4,051 |
| Vendor nontrade AR cash effect | -8,231 |
| Inventory cash effect | -5,284 |
| Other current/noncurrent assets cash effect | -19,347 |
| AP cash effect | 14,178 |
| Other current/noncurrent liabilities cash effect | 14,101 |
| Reported CFO | 146,724 |
| PP&E capex payments (+ magnitude) | 10,041 |
| Income taxes paid net (+ magnitude) | 32,592 |
| Equity award tax withholding (financing) | 6,703 |
| Derived narrow trade WC cash effect | -3,388 |
| Derived other-assets/liabilities cash effect | -5,246 |
| Derived all operating assets/liabilities effect | -8,634 |
| CFO minus PP&E capex (diagnostic) | 136,683 |

Exact CFO bridge: 128,930 NI + 13,100 D&A + 13,706 SBC − 378 other noncash − 3,388 narrow trade WC − 5,246 other operating assets/liabilities = 146,724. CFO minus PP&E capex = 136,683; minus SBC diagnostic = 122,977. These diagnostics retain interest, tax timing, tariff refunds and opaque other cash movements; neither is verified FCFF.

## Normalization and source limits

1. **Trade WC vs opaque residual (fact/calculation):** include trade AR, vendor nontrade AR, inventory and AP in the narrow cash-effect subtotal. Vendor AR is economically operating: components sold to manufacturing vendors, with gains recognized as product cost reductions (FY2025 Note4 p38). The other-assets/liabilities subtotal includes tax and other noncurrent items and is not pure recurring working capital. FY2025 tax payable fell from 26,601 to 13,016 (Note6), so blindly extrapolating its cash-effect bucket is inappropriate. Even narrow WC varies materially: annual effects 2021–25 are −4,344/+1,589/−3,924/−170/−4,727; TTM −3,388. Use explicit growth/inventory/payment assumptions, with sensitivity; do not assert a precise recurring residual.

2. **Ireland (fact):** FY2024 recognized 10,246 net book tax charge; FY2025 tax reconciliation has a 486 benefit. The FY2024 15.8bn liability/escrow valuation is not the exact FY2025 cash settlement. [FY2025 Q3 10-Q, filed 2025-08-01, MD&A](https://www.sec.gov/Archives/edgar/data/320193/000032019325000073/aapl-20250628.htm) reports €14.2bn/$15.4bn released in first nine months FY2025, fully settling the obligation. Funds were already held in restricted cash/securities; this is release of an existing funded escrow. Book-tax and cash-tax effects must be normalized separately. The first-nine-month settlement is removed automatically from TTM FY2025+9M26−9M25: **do not add another 15.4bn to TTM CFO**. Likewise no Ireland addback on top of removal of the associated liabilities cash movement.

3. **TCJA (fact/judgment):** latest Q3 MD&A states the remaining deemed-repatriation tax payable 8.8bn was paid in first nine months 2026. It is in the TTM window, distinct from Ireland; do not annualize this legacy payment. CFO-based normalization could separately consider it, with explicit tax bridge. In EBIT/NOPAT normalization, use normalized operating taxes and NWC excluding tax payable; **do not add the same 8.8bn again**.

4. **Tariffs (fact/approximation):** [Apple July 30, 2026 release](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/) says Q3 total gross margin benefited approximately 2 percentage points and diluted EPS benefited $0.11. Q3 revenue 109,417 ×2% implies approximately 2,188 pretax gross-profit benefit; this is an estimate, not an exact disclosed dollar amount. EPS benefit implies roughly 1.6bn net income using rounded EPS/share count; it is not an exact cash receipt. Latest 10-Q MD&A says refunds received reduce product cost of sales. Strip approximate gross benefit from operating EBIT for a recurring model, label it approximate, and avoid assuming all future tariffs disappear. No precise separately disclosed refund-cash line was identified.

5. **Interest (data gap):** FY2023 Note6 p39 reports expense 3,933, interest/dividend income 3,750; cash interest paid 3,803 (p32). FY2021/22 expense 2,645/2,931, income 2,843/2,825, cash interest 2,687/2,865. These are historical. Latest applicable companyfacts end FY2023 and FY2024/FY2025/latest10Q do not identify current split/cash-interest-paid. Other income net FY25 −321; nine months FY26 +670 vs FY25 −698; TTM +1,047. Net other income does not reveal financing interest or cash yields. Future debt interest payments 37bn/2.6bn next 12 months are contractual forecasts, not historical interest expense. Do not fabricate current after-tax interest addback or infer precise expense from debt×snapshot coupon.

6. **Tax rate (calculation/assumption):** FY2023 book ETR 14.72%; FY2024 excluding 10,246 Ireland charge 15.79%; FY2025 excluding 486 Ireland benefit 15.98% (includes 2,091 valuation-allowance charge); FY2026 nine-month ETR 17.58%, Q3 alone 17.9%. A 17–19% forward normalized rate is a conservative **scenario assumption**, anchored near recent 2026 conditions and above 2023–25 normalized history, not a factual average. SBC tax benefits and jurisdiction mix remain variable. Cash-tax 32,592 TTM/book-tax 26,976 TTM difference includes timing; do not replace normalized NOPAT rate with cash-tax/EBIT.

7. **Recommended FCFF convention (judgment):** normalized EBIT×(1−normalized tax) + D&A − capex − modeled increase in operating NWC. EBIT already expenses SBC, so do not deduct SBC again in this route; also do not add it back as free economic cash. Exclude cash/securities income and financing interest via operating EBIT, add excess cash/subtract debt in equity bridge. Split NWC trade and other recurring operating items explicitly; tax settlement normalization occurs once. Preserve CFO reconciliation as a quality cross-check. Intangibles and other operating asset uses can represent real reinvestment beyond PP&E: nine-month intangible assets net grew from 13,301 to 25,417, while other-assets cash use 16,266 is undissected. Do not simply assume this residual is entirely tax/nonrecurring; state coverage limits or impose conservative additional reinvestment scenario.

Machine-readable inputs: `cashflow-source-inputs.json`; reported signed cash effects are distinct from positive payment magnitudes. All seven reported CFO bridges and TTM bridge reconcile exactly; no assumptions are silently inserted as facts.

## PP&E depreciation and intangible reinvestment follow-up

**Fact/data gap:** FY2025 Note 5 p39 discloses rounded PP&E depreciation $8.0bn, with FY2024 $8.2bn and FY2023 $8.5bn. Latest FY2026 Q3 Note 5 and [FY2025 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/320193/000032019325000073/aapl-20250628.htm) do not separately disclose nine-month PP&E depreciation expense. Companyfacts `us-gaap:Depreciation` latest observation is the FY2025 annual amount. Exact TTM PP&E-only depreciation is therefore **unavailable**, not $8.0bn as a reported TTM fact. The $730m change in accumulated PP&E depreciation cannot substitute for expense because disposals, retirements and other adjustments change that balance.

**Fact/calculation:** Latest Note 5 shows intangible gross assets growing $13.270bn, accumulated amortization growing $1.154bn and net assets growing $12.116bn in nine months. These changes do not identify cash additions or period amortization expense; complete acquisitions, disposals, FX and noncash rollforwards are absent. No separate current intangible cash-purchase amount was identified. Companyfacts `PaymentsToAcquireIntangibleAssets` latest observation is FY2018 Q1, unusable as a current input. The $16.266bn other-operating-assets cash use must not be assumed entirely disposable or nonrecurring.

**Updated conservative convention (assumption):** for a sustainable proxy matched to PP&E-only capex, add back **modeled PP&E depreciation only**, retain intangible amortization in operating EBIT, and disclose missing intangible cash-investment detail. A forward $8.0bn depreciation assumption anchored to rounded FY2025 is reasonable for scenario modeling, with sensitivity; it is not reconstructed TTM depreciation. Relative to adding back the entire $13.1bn TTM D&A, this reduces the modeled cash addback by $5.1bn, an assumption-driven adjustment rather than a measured TTM amortization split. Retaining amortization mitigates the reinvestment gap but does not guarantee sufficient reinvestment when intangible assets are growing rapidly. Full D&A addback requires a separately modeled corresponding intangible reinvestment charge.
