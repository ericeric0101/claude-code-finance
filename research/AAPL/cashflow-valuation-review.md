# AAPL — Cash-flow normalization and valuation validation

As of 2026-10-11 Asia/Taipei. Consolidated, nominal USD millions except per-share USD. Latest reported period incorporated: Q3 FY2026 ending 2026-06-27, filed 2026-07-31; issuer/SEC recency checked to research date.

### Cash-flow normalization update — 2026-10-11

**Fact／Calculation：** TTM = FY2025 + 9M FY2026 − 9M FY2025，ending 2026-06-27。NI $128,930 + total D&A $13,100 + SBC $13,706 − other noncash $378 − trade operating WC cash use $3,388 − other operating asset/liability cash use $5,246 = CFO $146,724，精確相符。FY2021–25 與兩期九個月也全部勾稽。[SEC component review](cashflow-source-review.md)、[source inputs](cashflow-source-inputs.json)、[model input](normalized-valuation-input.json)、[reproducible output](normalized-valuation-output.json)。

**Fact／Interpretation：** Ireland $15.4bn 已於 first nine months FY2025 settled，因此在這個 TTM annual+9M−9M 組合中抵消，不能再加回。9M FY2026 的最後 TCJA deemed-repatriation payment $8.8bn 仍位於 TTM；改用 normalized NOPAT 並移除實際稅款相關資產／負債時點後，不再第二次加回。[SEC component review](cashflow-source-review.md)、[source inputs](cashflow-source-inputs.json)、[model input](normalized-valuation-input.json)、[reproducible output](normalized-valuation-output.json)。

**Assumption／Calculation：** Operating EBIT $154,859 減除約 $2,188 tariff-refund benefit（Q3 revenue×approximately 2 margin points），得到 $152,671；18% normalized operating tax 得 NOPAT $125,190。18% 是近期 ETR 記錄支持的模型假設，不是已披露未來現金稅率。只加回 FY25 rounded PP&E depreciation $8,000 作前瞻假設，減 FY25 full PP&E cash capex $12,715，trade WC neutral，得到 **約 $120.5bn normalized FCFF proxy**。總 D&A $13,100 含其他攤銷，其配對 cash reinvestment 未拆分，故沒有全部加回；精確 TTM PP&E-only depreciation 不可得。[SEC component review](cashflow-source-review.md)、[source inputs](cashflow-source-inputs.json)、[model input](normalized-valuation-input.json)、[reproducible output](normalized-valuation-output.json)。

| Operation | Change, USD millions | Running cashflow | Basis |
|---|---:|---:|---|
| Reported TTM CFO | +146,724 | 146,724 | Fact/Calculation |
| Retain economic SBC cost; reverse CFO addback | -13,706 | 133,018 | Calculation |
| Reverse other noncash adjustments | +378 | 133,396 | Calculation |
| Remove actual asset/liability cash timing | +8,634 | 142,030 | Calculation |
| Replace reported NI with normalized operating NOPAT | -3,740 | 138,290 | Assumption/Calculation |
| Replace total D&A with PPE-only assumed depreciation | -5,100 | 133,190 | Assumption/Calculation |
| Subtract normalized full cash PPE capex | -12,715 | 120,475 | Assumption |
| Insert normalized working-capital cash credit | +0 | 120,475 | Assumption |


**Accounting convention：** 從 CFO 路徑只反轉一次 SBC add-back，使它維持經濟成本；从 EBIT 路徑因 SBC 已在費用中，沒有第二次扣除。NI 改為 operating NOPAT 同時排除 financing interest、investment income 與其他 non-operating income 的淨影響，避免假造最新利息拆分；持有 securities 的價值另在 equity bridge 處理。Operating leases 保留 rent operating cost，未單方面資本化。[SEC component review](cashflow-source-review.md)、[source inputs](cashflow-source-inputs.json)、[model input](normalized-valuation-input.json)、[reproducible output](normalized-valuation-output.json)。

**Assumption sensitivity：** tax 16%–20%、PP&E capex $10.041bn–$20bn、trade WC cash credit −$5bn／0／+$5bn，固定 assumed PP&E depreciation $8bn，機械得到約 $105bn–$131bn；此範圍不是信賴區間。Other-assets cash use 包含未完全辨識的 recurring intangible/licensing/content investment；維持攤銷費用可避免當成免費現金，但不能證明所有額外 cash investment 都已辨識。DCF 另用完整 reinvestment budget 與 ROIIC／capex 壓力測試處理。[SEC component review](cashflow-source-review.md)、[source inputs](cashflow-source-inputs.json)、[model input](normalized-valuation-input.json)、[reproducible output](normalized-valuation-output.json)。

## 7. Valuation

**Calculation：** Alpha Vantage key 已配置並成功取得 AAPL $336.64、交易日 2026-10-09，與 Yahoo acquisition 一致。Common-share 市值 proxy $4,917,961、financing debt $84,344、cash＋securities $146,517；保留 **assumed** operating cash $10,000 後 surplus liquidity $136,517、operating EV $4,865,788。不是核驗當日 fully diluted market cap。[API check](alpha-vantage-check.json)、[market data](market-data.json)、[SEC share/debt data](financial-data.json)、[valuation bridge](normalized-valuation-input.json)。

**Share／lease consistency：** Forward per-share 與 matched reverse 都用 latest reported quarter **weighted-average diluted** 14,714.676 million shares，反解 target EV = $336.64×同一股數＋financing debt−surplus liquidity；不同於 common-share 市值 proxy。這是透明的最新可用 dilution proxy，並非研究日真正 treasury-stock-method outstanding shares。Operating lease rent 留在 EBIT／cashflow，EV 排除相應 operating lease liabilities；finance-lease debt／principal 最新拆分缺口保留，僅 FY25 finance lease liabilities $1,230 已知，其數量級 stress 約 $0.08/share、不是當期精確修正。[Input](normalized-valuation-input.json)、[SEC annual statements](financial-data.json)。

| Trailing metric | Result | Convention／source |
|---|---:|---|
| P/E | 38.1x | common-share mcap proxy／reported TTM NI，[original trailing tool](valuation-output.json) |
| EV/EBIT | 31.4x | 未預留 operating cash 的原 EV convention，用於原 trailing comparables，不與新 operating EV 混稱，[original tool](valuation-output.json) |
| EV/Sales | 10.4x | 同上；period/basis limitation，[original tool](valuation-output.json) |
| Reported simple FCF yield | 2.8% | CFO−PP&E capex／common-share mcap proxy；不是 FCFF，[source bridge](cashflow-source-review.md) |
| Normalized operating cashflow / operating EV | 2.48% [E] | 約 $120.5bn normalized FCFF proxy／new operating EV；enterprise cashflow 與 enterprise claim 配對，[new output](normalized-valuation-output.json) |

### Discount rate

**Fact／sourced estimate／Calculation：** 2026-10-09 US 10Y Treasury 5.24%，2026-10-01 Damodaran implied US ERP 4.20%（作者模型估計）；AAPL/SPY 60 monthly adjusted returns，2021-10 through 2026-09，raw beta 1.0686、Blume 1.0460、R² 0.4588。Ke = 5.24%＋1.0460×4.20% = **9.633%**。用 note fair-value debt weight 約 1.47%、synthetic marginal Kd 5.715%、assumed debt tax shield 21%，得到 conditional **WACC 9.558%**。最新 Apple bond YTM／bottom-up business beta 尚未核實，因此不是客觀已觀測的 WACC。全部回歸 observations 和公式可重算。[Dated discount-rate review](discount-rate-review.md)、[inputs](discount-rate-inputs.json)、[US Treasury](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value=2026)、[NYU Stern](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/home.htm)。

### Reinvestment-aware DCF and matched reverse

**Assumption [E]：** 不把約 $120.5bn 正常化基期直接當成會無成本成長的現金。模型從 normalized operating NOPAT $125,190 出發，revenue／NOPAT growth 8% 持續十年，再五年 fade 到 3%；EBIT margin 32.70%、operating tax 18% 固定。Stage-one incremental ROIC **100%**、terminal **20%** 是對資本效率的明列假設，未用受 buybacks 扭曲的歷史 financing ROIC 作證據。[Driver inputs](normalized-valuation-input.json)、[cashflow source constraints](cashflow-source-review.md)。

**Model convention：** Year investment = max(NOPAT×growth/assumed ROIIC, scaled full-capex−PP&E depreciation−normalized WC cash-credit baseline)。這個 max 避免把同一成長支出重複相加，且讓高 capex／WC 壓力進入主 DCF。FCFF = NOPAT−investment，SBC 不加回；terminal 也扣 g/ROIIC reinvestment。Base growth budget 高於 baseline，所以正常化現金流數字與第一年 forecast FCFF 不相同；單獨改某些 capex 假設可能尚未觸及 growth budget floor，而不影響 base value，不能誤稱每個 capex cell 都直接線性影響估值。[Year-by-year model](normalized-valuation-output.json)、[reproduction script](../../scripts/normalize_aapl.py)。

**Calculation [E]：** Mid-year discounted DCF 約 **$194/share**；terminal 占 EV **43.8%**。第十五年 revenue 約 $1.29 trillion，terminal implied EV/EBIT **10.9x**；這些是模型結果，不是已證實的市場占有率或公司指引。End-year timing alternative 約 $185。同一模型、同一 diluted-share proxy 的 reverse 解要求約 **14.8% 年增長十年**，再 fade，才能支持 $336.64；margin／tax／ROIIC 維持本模型設定。這是條件式 expectations test。[Output and matched target](normalized-valuation-output.json)。

**Independent calculator cross-check [E]：** 另外將 normalized FCFF proxy 輸入上游 `valuation.py` 的簡化兩階段現金流模型，得到約 **$201**。它直接成長 cashflow、沒有本模型逐年 NOPAT／investment budget；只作方法比較，不混用兩者的 reverse。Zero-reinvestment control 與 upstream DCF 加 mid-year adjustment 相符。[Upstream cross-check inputs](normalized-upstream-valuation-input.json)、[output](normalized-upstream-valuation-output.json)。

### Bear / Base / Bull — current present-value scenarios

**Assumption [E]：** 全部下列 DCF 用相同 WACC 9.558%、相同 share／surplus-cash basis，改變營運假設；沒有另加任意風險溢酬。情境價不是發生機率或交易建議。[Scenario input/output](normalized-valuation-output.json)。

| Scenario | EBIT margin | Ten-year growth | Operating tax | Stage / terminal ROIIC | Present value/share | vs Oct9 close |
|---|---:|---:|---:|---:|---:|---:|
| Bear | 29.0% | 4% | 20% | 50% / 15% | $117 | -65.1% |
| Base | 32.7% | 8% | 18% | 100% / 20% | $194 | -42.5% |
| Bull | 35.0% | 12% | 17% | 100% / 25% | $295 | -12.4% |

### Earnings-method cross-check

**Assumption／Calculation [E]：** Normalized EBIT 加回 reported TTM net non-operating income $1,047，再套同一 18% 稅率，normalized net income proxy 約 $126,048／EPS約 $8.57。這是 equity earnings 路徑，不能改拿 EV 當 numerator；非報告 diluted EPS。以 2027-09-25 作 FY27 情境觀察日，距研究日約 0.956 年，按 Ke 9.633% 折現，assume current $0.27 quarterly dividend 維持，未含交易成本與個人稅。Growth、exit P/E 均為 analyst assumptions，未完成 comparable-peer valuation calibration；這是第二方法交叉檢查，不能當作 validated sector-relative P/E。[Earnings inputs/results](normalized-valuation-output.json)。

| Earnings scenario | Annual NI/EPS growth assumption | Exit P/E assumption | FY27 EPS | Future price, ex-dividend | Present value incl assumed dividend |
|---|---:|---:|---:|---:|---:|
| Bear | 0% | 22x | $8.57 | $188 | $174 |
| Base | 10% | 28x | $9.38 | $263 | $242 |
| Bull | 20% | 34x | $10.20 | $347 | $318 |

**Interpretation：** 中央 DCF 約 $194 與 earnings-method 約 $242 都低於參考價格，但方法間差距本身代表不確定性，不能取平均假裝更準確。原草稿 $110bn／9%／$205 illustrative DCF 與未折現 FY27 $286 scenario 已由本次模型更新取代；原 JSON 保留作歷史 pipeline 測試，並非本次現值結論。[Current valuation output](normalized-valuation-output.json)。

### Sensitivity and what flips the conclusion

**Assumption／Calculation [E]：** WACC×terminal g 固定其他 base inputs，完整矩陣及 EBIT margin×growth、stage／terminal ROIIC、capex／WC 敏感度已保存。[Sensitivity output](normalized-valuation-output.json)。下表呈現部分 matrix，不是統計信賴區間。

| WACC | g=2% | g=3% | g=4% |
|---|---:|---:|---:|
| 8.50% | $217 | $232 | $254 |
| 9.56% | $184 | $194 | $206 |
| 10.50% | $162 | $169 | $177 |
| 11.50% | $144 | $148 | $153 |

**Conclusion-flip [E]：** Base terminal ROIIC 降至 WACC（不再永久超額資本回報）時約 **$176**。固定 base 營運假設、僅改 WACC，約 **6.84%** 可接近 $336.64；但 joint bullish assumptions（35% EBIT margin、12%十年 growth、17% tax、terminal ROIIC25%、WACC8.5%）產生約 **$360**，方向可翻轉。這不是已證實的 forecast，卻足以否定「任何合理假設都昂貴」這種過度確定說法。[Flip calculations](normalized-valuation-output.json)、[independent challenge](normalization-challenge.md)。

**Fundamental downside scenario：** Bear DCF 約 $117、與參考價格差約−65%；另保留原極端 EPS $6×18x=$108／約−67.9% stress reference。皆非保證最大損失、非機率估計；普通股極端情況可全額損失。[Current scenario output](normalized-valuation-output.json)、[original stress input](valuation-input.json)。

## Validation boundaries

Accounting bridges, model identities, independent calculator controls and focused challenge are checked. Future taxes, reinvestment efficiency, cash spending, terminal returns and multiples remain assumptions. Current fully diluted shares, latest interest-income split and intangible cash-investment breakdown are unavailable; a unique sustainable FCFF cannot be measured precisely from these disclosures. This update completes the requested cashflow/valuation work with explicit estimates; it does not claim a completed peer-relative rating or all missing document diligence. Research, not personalised allocation or trading advice.
