# Apple Inc. (NASDAQ:AAPL) — Equity Analysis

**Analysis date:** 2026-10-11，Asia/Taipei。**Mode:** Standard research update；現金流勾稽、正常化估計與條件式估值完成驗證；完整 sector-relative rating 仍為 provisional。
**Basis:** Consolidated；US GAAP；USD millions（美元百萬）；股數為百萬股，股價為美元。
**Latest reported period:** Q3 FY2026，截至 2026-06-27，10-Q 於 2026-07-31 提交。
**Price reference:** $336.64，2026-10-09 美國東部時間收盤，非即時價。[Yahoo price history](https://finance.yahoo.com/quote/AAPL/history/)，[價格交叉檢查](https://stockanalysis.com/stocks/aapl/history/)。

## VERDICT AND KEY RISKS

**Interpretation：** Apple 的現金創造與生態系優勢仍有證據。完成現金流正常化與 reinvestment-aware valuation 後，中央假設下 DCF 約 $194、earnings-method cross-check 現值約 $242，均低於 $336.64 參考價格；更樂觀營運與折現率組合可得到約 $360，所以結論是 **目前價格需要較強的成長與資本效率，估值吸引力取決於假設**。基本面信心中等，估值信心中低；不是確定 fair value 或 buy/sell 指令，完整 peer-relative rating 仍未核實。[Updated inputs/results](normalized-valuation-output.json)、[cashflow/valuation review](cashflow-valuation-review.md)。

**Research label：WATCH.** 估值模型不確定性偏高，兩種方法的 base value 有明顯分歧；這是研究分類，不是依你的個人情況作出的下單建議。參考股價 $336.64（2026-10-09 close）。**條件式 DCF 買入觀察參考區間：$155–$175/share**，即 DCF base 約 $194 的 80%–90%；假設包含18% operating tax、十年8% growth、stage ROIIC100%、terminal ROIIC20%、9.56% WACC。Earnings cross-check 對應的80%–90%區間約 $193–$218，差異顯示估值方法／假設尚未收斂；因此更審慎的可執行觀察區間目前 **尚未建立**。若新增資料支持 recurring intangible／AI cash investment、normalized margin 或折現率不同，須重算兩區間，不應只盯 DCF 數字。[Range math and scenarios](normalized-valuation-output.json)。

**Calculation：** 標準權重計算分數原為 6.6/10，歷史應收帳款增速 gate 將分數上限限制為 **6.0/10**；這是依上游 `score.py` 的 pipeline demonstration，**不是已驗證的公司評等**。[評分輸入](score-input.json)、[評分輸出](score-output.json)。

最影響結論的事項：產品與服務組合支撐高現金創造；近期一次性關稅退款不可外推；現價隱含的現金流成長需要多年延續。主要風險是零組件成本／供應限制、平台監管與 Google 授權收入、以及管理層交接執行。[FY2025 10-K Items 1/1A/8](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm)、[最新 10-Q MD&A／Part II](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm)。

## RECENCY STATEMENT

Most recent reported period incorporated: **Q3 FY2026，2026-06-27**；SEC 發布／提交日 **2026-07-31**。[最新 10-Q](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm)。

Events checked through: **2026-10-11**，查閱 SEC submissions、issuer 公告與文件；不是涵蓋所有新聞或法院卷宗的事件保證。[Filing manifest](filing-manifest.json)、[文件覆核記錄](document-review.md)。最新年度資料仍為 FY2025；取得的 filings inventory 未包含 FY2026 10-K，因此未把前三季當作全年。[SEC submissions](https://data.sec.gov/submissions/CIK0000320193.json)。

**Macro／geopolitical event check：** 本次將10Y Treasury 5.24%與60個月beta放入dated WACC試算，並用8.5%–11.5%作折現率敏感度；這不是將Fed policy rate直接等同Apple資金成本。公司最新10-Q／風險披露提到關稅、貿易限制與供應鏈／零件可得性，Q3約2個margin points tariff refund已從normalized EBIT剔除。[10-Q](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm)、[issuer Q3 release](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/)、[dated WACC sources](discount-rate-review.md)。Apple供應鏈依賴使衝突、制裁、航運及晶片限制可能透過供應量、運費、交期與毛利傳導；截至研究日，本次未取得足以把某一項近期戰事／油價變動映射為Apple特定現金支出的 primary quantification，故列為供應鏈與投入成本監控情境，沒有另加通用WACC懲罰。不是窮盡全球新聞搜尋。

已知重大事件包含 CEO 交接：公司公告 John Ternus 於 2026-09-01 接任 CEO，Tim Cook 為 Executive Chairman；本次未找到撤回公告，不能沿用舊資料稱 Cook 為現任 CEO。[Apple，2026-04-20 公告](https://www.apple.com/newsroom/2026/04/tim-cook-to-become-apple-executive-chairman-john-ternus-to-become-apple-ceo/)。已触發的監控訊號是應收帳款增速與庫存增加；未直接證明正面經營論點失效。

**Fact — post-filing events：** Apple developer 條款於 2026-08-18 更新，2026-10-01 生效；EU 統一條款以 App Store 外數位交易的 5% Core Technology Commission 取代 per-install CTF。這不是所有 EU App Store 銷售都採用 5%，且收入影響未揭露。[Apple developer EU terms](https://developer.apple.com/support/apps-in-the-eu/)。另於 2026-09-09 公告首款摺疊 iPhone Duo，10-16 預購、10-23 開售；公告以 Ternus 為 CEO。研究日尚未取得其實際銷售，不能把產品公告當獲利驗證。[Apple product announcement](https://www.apple.com/newsroom/2026/09/apple-unveils-iphone-duo/)。

## DATA QUALITY NOTE

| 項目 | 說明 |
|---|---|
| Primary sources | SEC XBRL companyfacts、FY2025／FY2024 10-K、最新及 Q2 10-Q、2026 proxy、AGM 8-K；數字保留 tag、起訖、accession、filed 與 URL。[Financial data](financial-data.json) |
| Secondary sources | Apple 與 peer issuer earnings releases；Yahoo 僅用於價格。沒有用 aggregator 財務數字取代 filings。[Document review](document-review.md)、[Peer review](peer-review.md) |
| As-of dates | 財報資產負債日 2026-06-27；股價 2026-10-09 close。相隔不同日期，市值與 EV 是估算。[Market data](market-data.json) |
| Reporting basis and units | Consolidated、US GAAP、USD millions；無匯率換算。年度為 Apple 財年，不是曆年。 |
| Classification | **Fact**：來源所述；**Calculation**：公式運算；**Assumption [E]**：模型假設；**Interpretation**：分析判斷。 |
| Calculations | TTM = FY2025 + 9M FY2026 − 9M FY2025；Q4 income = 全年 − 前九月，未把 weighted EPS 當普通金額相減。[Data intake](data-intake.json) |
| Estimated | 市值用最近財報期末股數；DCF 現金流基期、成長、WACC、terminal growth、情境 EPS／倍數／機率均為假設，不是公司指引或市場共識。[Valuation input](valuation-input.json) |
| Missing | 完整兩次電話會議 Q&A、較早年度完整風險差異、所有合約條款、獨立 ESG 報告、current fully diluted shares、可比 peers TTM 估值、bottom-up business beta／當期 Apple bond YTM／current interest split 與 intangible cash-investment breakdown。已列具體文件覆核範圍。[Coverage record](document-review.md) |
| Verification | intake gate 為 PASS；這只驗 provenance／basis／units，不能替代逐項人工核對，也不能證明數字全部正確。[Verification output](data-verification.txt) |

## 1. The Business — What It Sells and How It Makes Money

**Fact：** Apple 銷售 iPhone、Mac、iPad、穿戴／配件及服務；硬體、作業系統、開發者與服務共同形成 ecosystem。FY2025 iPhone 銷售 $209,586，Services $109,158，總營收 $416,161；Services 佔約 26.2%，iPhone 約 50.4% 為計算值。[FY2025 10-K Item 7 product sales](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm)。

**Interpretation：** 裝置更新與服務變現共同驅動價值。品牌、整合体验、切換成本與開發者網絡支持 moat，但不能直接由毛利率證明競爭壁壘仍在擴大。公司未完整揭露產品單位量／ASP，因此營收成長不能拆成可驗證的純量價貢獻。[FY2025 10-K Item 1/7](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm)。

**Fact：** 最新 MD&A 指出 advanced semiconductor、NAND／DRAM 與 AI compute constraints；產品與服務成長原因為管理層解釋。製造外包降低自有廠房需求，也增加供應商依賴。[FY2026 Q3 10-Q MD&A and risks](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm)。

## 2. Sector Classification and Playbook Applied

**Interpretation：** Consumer-device ecosystem，含高毛利 services。使用 `02-core-factors.md` generic framework，補以 consumer／platform 經濟的判斷；不把 Apple 當 semiconductor 製造商或純 SaaS 公司。沒有專門覆蓋此混合業務的 playbook，因此 shipped generic benchmark 明確只供參考。[Scoring input](score-input.json)。

| 指標 | 處理 |
|---|---|
| P/E、EV/EBIT、FCF yield | 可用，但先辨識一次性稅／退款、SBC 與 cash conversion。 |
| ROE、P/B | 回購壓縮權益，無法當作獨立品質或便宜程度證據。 |
| ROIC／ROIIC | 財務資本定義會因回購、securities、R&D expensing 改變；附計算限制，不拿其高數字外推成長。 |
| Segment ROCE | 公司未提供 CODM 使用的 segment capital，標記 not available，沒有補造。 |

## 3. Situation Classification

**Interpretation：** 成熟全球品牌、硬體周期＋服務變現；有 CEO succession、AI 投資與監管變化，沒有資料支持把它當 turnaround。高現金創造並不消除高價格風險。[Latest 10-Q](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm)。

## 4. Scorecard

以下均為 **Calculation／Interpretation**；輸入、benchmark basis、各指標與 notes 完整保存在 [score-input.json](score-input.json) 及 [score-output.json](score-output.json)。同業不足，margin 用自身歷史；其餘 numeric bands 為 indicative，judgment 有證據理由。

| Category | Score /10 | Weight | Weighted | 理由 |
|---|---:|---:|---:|---|
| Business quality & moat | 7.57 | 15% | 1.135 | 生態系／定價判斷；非市場份額實測。 |
| Profitability & returns | 6.11 | 20% | 1.222 | FY2025 margins 對 own history；ROE／ROIC 未用來美化分數。 |
| Earnings quality | 6.47 | 15% | 0.970 | 多年現金轉換良好，FY2025 FCF margin 弱於自身中位。 |
| Balance sheet | 9.07 | 12% | 1.088 | 流動性與近期債務涵蓋；不能忽略 purchase commitments。 |
| Growth | 6.00 | 12% | 0.720 | Runway judgment；未捏造缺少的五年 CAGR 指標。 |
| Governance | 7.00 | 10% | 0.700 | 公開披露／資本配置，交接後仍需觀察。 |
| Valuation | 4.24 | 10% | 0.424 | 高 P/E 與低現金收益率；generic bands 非 peer median。 |
| Risk | 5.67 | 6% | 0.340 | 平台、供應鏈與交接。 |
| Composite before gate | 6.60 | 100% | 6.600 | 上游 scorer，四捨五入。[Score output](score-output.json) |
| Composite after gate | **6.00** | — | — | `receivables_blowout` cap。[Score output](score-output.json) |

**Coverage limitation：** category coverage 100%，weighted metric coverage 僅 42.5%；scorer 的 `composite_confident=true` 只反映 category completeness，本文仍視為 **indicative**，不是高信心股票評等。[Score output](score-output.json)。

**Gate disclosure — checked / not checked / raised：**

| Gate | Status | Evidence／限制 |
|---|---|---|
| Going concern、qualified/adverse audit | Checked，未發現 | EY FY2025 clean opinion；不是季度重新審計。[10-K Item 8](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm) |
| CFO/NI 持續低於 gate 門檻 | Checked，未觸發 | FY2023–FY2025 合計 CFO/NI 約 1.12x。[Financial data](financial-data.json) |
| Receivables blowout | **Raised** | FY2024 trade AR +13.2% vs sales +2.0%；FY2025 +19.1% vs +6.4%；連續增速差，score cap 6.0。[FY2025／FY2024 10-K balance sheets](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm) |
| Serial dilution | Checked，未觸發 | FY2021–FY2025 期末股數下降；SBC 仍有成本。[Financial data](financial-data.json) |
| Related party／board／structure | 部分 checked | proxy／subsidiary list 已閱讀；未完成全部合約／所有 jurisdiction 調查。[Document review](document-review.md) |
| Fraud enforcement／default／auditor resignation | Not fully checked | 未發現與未調查不同；未完成獨立監管／信用／法院資料庫全面搜尋。 |
| India promoter pledge／ASM | n/a | 美國普通股，印度專屬 gate 不適用。 |

**Interpretation：** 應收訊號可有季節性、批發付款條件／渠道 mix 的合理解釋；本報告不斷言虛增收入。gate 是保守流程規則，仍需 aging、收款趨勢與管理層說明。

**Calculation：** latest June trade AR YoY 約 13.9%，低於同季 revenue growth 約 16.4% 與 9M growth 約 16.2%；不能宣稱最新同季收款 divergence 持續惡化。歷史 end-balance DSO proxy FY2023／FY2024／FY2025 約 28.1／31.2／34.9 days，僅為期末 balance proxy。[Financial data](financial-data.json)、[Independent source check](challenge-review.md)。

**Weight sensitivity：** default／quality-compounder／deep-value raw composite 6.60／6.75／6.50，全部被歷史 gate cap 為 6.00。未發現 preset 反轉，但 binding cap 不能證明 coverage 足夠。[Preset outputs](score-quality-output.json)、[deep-value output](score-value-output.json)。

## 5. Core Analysis by Dimension

### 5.1 Multi-year record

**Fact／Calculation：** 金額 USD millions；FCF = CFO − PP&E cash capex，未稱為 unlevered FCFF。[逐數字 SEC provenance](financial-data.json)，來源對應各年 10-K consolidated statements／cash flows。

| Metric | FY2021 | FY2022 | FY2023 | FY2024 | FY2025 | Source |
|---|---:|---:|---:|---:|---:|---|
| Revenue | 365,817 | 394,328 | 383,285 | 391,035 | 416,161 | [SEC annual facts](financial-data.json) |
| EBIT | 108,949 | 119,437 | 114,301 | 123,216 | 133,050 | [SEC annual facts](financial-data.json) |
| Net income | 94,680 | 99,803 | 96,995 | 93,736 | 112,010 | [SEC annual facts](financial-data.json) |
| CFO | 104,038 | 122,151 | 110,543 | 118,254 | 111,482 | [SEC annual cash flows](financial-data.json) |
| PP&E cash capex | 11,085 | 10,708 | 10,959 | 9,447 | 12,715 | [SEC annual cash flows](financial-data.json) |
| FCF [Calculation] | 92,953 | 111,443 | 99,584 | 108,807 | 98,767 | [CFO minus capex](financial-data.json) |
| Diluted EPS | 5.61 | 6.11 | 6.13 | 6.08 | 7.46 | [SEC annual statements](financial-data.json) |
| SBC | 7,906 | 9,038 | 10,833 | 11,688 | 12,863 | [SEC annual cash flows](financial-data.json) |

**Calculation：** FY2021→FY2025 是四個年度間隔，revenue CAGR 約 3.3%，不是五年 CAGR；較長期紀錄明顯慢於近期季度成長。FY2025 gross margin 約 46.9%，own FY2021–FY2025 range 約 41.8%–46.9%；operating margin 約 32.0%，own range 約 29.8%–32.0%。[Ratios output](ratios-output.json)、[raw inputs](ratios-input.json)。

### 5.2 Latest eight quarterly income trends

| Fiscal quarter／period end | Revenue | EBIT | Net income | Source／Calculation |
|---|---:|---:|---:|---|
| Q4 FY2024／2024-09-28 | 94,930 | 29,591 | 14,736 | Annual minus 9M，[SEC intake](data-intake.json) |
| Q1 FY2025／2024-12-28 | 124,300 | 42,832 | 36,330 | [SEC 10-Q provenance](financial-data.json) |
| Q2 FY2025／2025-03-29 | 95,359 | 29,589 | 24,780 | [SEC 10-Q provenance](financial-data.json) |
| Q3 FY2025／2025-06-28 | 94,036 | 28,202 | 23,434 | [SEC 10-Q provenance](financial-data.json) |
| Q4 FY2025／2025-09-27 | 102,466 | 32,427 | 27,466 | Annual minus 9M，[SEC intake](data-intake.json) |
| Q1 FY2026／2025-12-27 | 143,756 | 50,852 | 42,097 | [SEC 10-Q provenance](financial-data.json) |
| Q2 FY2026／2026-03-28 | 111,184 | 35,885 | 29,578 | [SEC 10-Q provenance](financial-data.json) |
| Q3 FY2026／2026-06-27 | 109,417 | 35,695 | 29,789 | [SEC 10-Q provenance](financial-data.json) |

**Interpretation：** 季節性強，holiday quarter 不能直接年化。FY2024 淨利含一次性 Ireland tax charge，FY2025 rebound 不能全算成經營改善。[FY2025 10-K tax note／FY2024 comparison](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm)。

### 5.3 Earnings quality and cash flow

**Calculation：** FY2025 CFO/NI 約 1.00x；FY2023–FY2025 累計約 1.12x，單年回落不等於帳務問題，但要解釋 working capital。TTM CFO $146,724 − capex $10,041 = FCF $136,683；再扣 SBC $13,706 得 owner-cash proxy $122,977。SBC subtraction 是保守經濟成本代理，不能同時再無說明地扣相同回購補稀釋成本。[TTM FY2025+9M26−9M25](financial-data.json)。

**Calculation：** 9M CFO YoY 增加 $35,242，其中 NI 增加 $16,920、noncash adjustments 差額 $1,956、operating assets／liabilities movements 改善 $16,366；後者含 other current／noncurrent liabilities movement 差額 $25,177，與其他負向變化抵銷。Cash tax 下降與這些現金流項目有重疊，不重複加總。持續性拆解與正常化假設見下方更新。[Q3 10-Q cash flows](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm)、[Challenge arithmetic](challenge-review.md)。

**Calculation [E]：** 對 FY2024 加回 $10,246 Ireland charge、FY2025 扣除 $486 benefit 的對稱稅項比較，NI growth 約 7.25%，低於 reported 19.50%；這只是兩項調整，不是完整 adjusted earnings。Reported FCF FY2021→FY2025 四年間 CAGR 約 1.53%，亦不直接代表 normalized 未來能力。[FY2025 10-K tax note](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm)、[Source verification](challenge-review.md)。

**Fact／Calculation [E]：** Q3 reported GM 50.1%、EPS $2.02；公司說 tariff refunds 增加約 2 percentage points 與 $0.11，簡單扣除為 GM 約 48.1%、EPS 約 $1.91；這不是完整 issuer non-GAAP reconciliation，不能由四捨五入的百分點算出精確退款額。[Apple 2026-07-30 results](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/)。

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

### 5.4 Balance sheet and capital intensity

**Calculation：** 2026-06-27 cash $39,544＋current securities $22,855＋noncurrent securities $84,118 = liquidity $146,517；commercial paper $1,997＋current term debt $11,007＋noncurrent term debt $71,340 = financing debt $84,344；net cash 約 $62,173。[Q3 10-Q consolidated balance sheet](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm)。

**Fact：** 存貨 $11,092 vs FY2025 year-end $5,718，零件庫存是主要增加來源；manufacturing commitments $57.0bn、other purchase commitments $29.3bn。這些營運承諾不是全部立即加進 interest-bearing debt 的項目，但限制現金彈性。[Q3 10-Q notes／MD&A](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm)。

**Interpretation：** 現金／securities 支持流動性，但非流動投資不是全部等同即日現金；trade receivables 集中與零件預購要監控。FY2025 capex/revenue 約 3.1%，自有資本密集度較低，不能因此忽略外包 purchase commitments。[FY2025 cash flows](financial-data.json)。

### 5.5 Returns on capital

**Calculation [E]：** 上游 ratio utility 的 FY2025 financing-route ROIC 約 102.3%；定義是 EBIT×(1−全期間 derived normalized tax)／平均 equity＋gross financing debt−cash−current investments，不含非流動 securities 調整，且未完整重建 leases／operating route；此數字只展示工具與定義，**不作評分輸入或成長預測**。[Ratios input/output](ratios-output.json)。

**Interpretation：** 大量回購、費用化 R&D 與低帳面資本使 ROE／ROIC 高得不宜與 peers 機械排名。增量 capital base 在工具使用視窗縮減，ROIIC not meaningful；capital-release 與獲利改善應分開報告，不說它能持續產生無限高增量回報。[Ratio warnings](ratios-output.json)。

### 5.6 Governance

**Fact：** EY FY2025 audit／ICFR opinion unqualified，uncertain tax positions 為 CAM；CAM 本身不是 qualification。股權獎酬与 GAAP 銷售／營業利益、相對 TSR 有關，並非直接 ROIC／FCF 目標。Proxy ownership footnotes 含較早機構持股時間，不能當作 October 2026 ownership。[2026 proxy](https://www.sec.gov/Archives/edgar/data/320193/000130817926000008/aapl014016-def14a.htm)、[Document review](document-review.md)。

**Interpretation：** 公開披露支持治理基礎，但薪酬指標、股權成本、executive-chair 架構及實際股東投票都應持續追蹤；「未找到 disqualifying fraud」不能寫成「保證没有問題」。

## 6. Peer Comparison

**Interpretation：** DELL／HPQ 是 partial hardware comparables；MSFT 為 platform context。Apple 的手機＋服務混合，沒有直接匹配的成熟美國上市 peer；不能把三者混成一個 sector median。以下都是 USD millions、GAAP、consolidated 三個月數字，結束日不同。[Peer evidence and cashflow caveats](peer-review.md)。

| Company／period end | Revenue | Gross margin | Operating margin | Role／source |
|---|---:|---:|---:|---|
| AAPL／2026-06-27 | 109,417 | 50.1% reported；~48.1% ex-refund [E] | 32.6% reported；~30.6% ex-refund [E] | [SEC Q3 10-Q](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm)，refund 降低 COGS，同樣影響 EBIT |
| DELL／2026-07-31 | 46,971 | 20.9% | 11.5% | [Issuer Q2 FY2027](https://investors.delltechnologies.com/news-events/press-releases/detail/1653/dell-technologies-delivers-second-quarter-fiscal-2027-financial-results) |
| HPQ／2026-07-31 | 15,677 | 18.8% | 5.7% | [Issuer Q3 FY2026](https://investor.hp.com/news-events/news/news-details/2026/HP-Inc--Reports-Fiscal-2026-Third-Quarter-Results/default.aspx) |
| MSFT／2026-06-30 | 90,007 | 67.2% | 45.1% | [Issuer Q4 FY2026](https://www.microsoft.com/en-us/investor/earnings/fy-2026-q4/press-release-webcast) |

**Interpretation：** 不同 services／server／printing mix 解釋大部分差异；不能直接說 margin 較高就是管理更好。Peers 的 cash capex／leases／financing-receivable adjusted FCF 定義不同；本次沒有生成假 precision 的 TTM peer multiple comparison。價格已同步取得，但不足以補齊 normalized peer TTM financials。[Market snapshots](market-data.json)、[Peer review](peer-review.md)。

**Fact／Interpretation — smartphone context：** Samsung Q2 2026 MX／Networks revenue KRW33.2tn、operating loss KRW0.7tn，issuer 說 premium sales growth 同時受零件成本壓力。這是更接近手機的 operational counter-evidence，但其 segment、IFRS、KRW 與 Apple consolidated USD 不可直接合併排名。[Samsung official Q2 results](https://news.samsung.com/global/samsung-electronics-announces-second-quarter-2026-results)。Xiaomi primary IR event 可定位，但本次 presentation 未取得，沒有採用無來源數字；smartphone peer valuation 留作未完成的研究項目。[Primary Xiaomi event](https://ir.mi.com/events/event-details/2026-interim-results-announcement)。

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

## 8. Short-Term and Long-Term Thesis

**Interpretation — short term：** 下一次年報／財報、iPhone 更新需求、零件缺貨／價格與去除退款後 margin 是較有辨識力的檢查。CEO 交接是既定公告事件，是否成功還需看執行成果。[Issuer／SEC record](document-review.md)。

具體觀察事件是已公告的 Duo 預購／出貨，並檢查新品營收是增量还是既有 iPhone cannibalization；EU 新條款已生效，後續披露才可檢驗對 Services economics 的影響。[Duo announcement](https://www.apple.com/newsroom/2026/09/apple-unveils-iphone-duo/)、[EU terms](https://developer.apple.com/support/apps-in-the-eu/)。

**Interpretation — long term：** 生態系若維持客戶留存並擴大服務變現，現金流可持續；若 AI／監管改變 distribution economics，歷史優勢可能減弱。現價必須用可驗證的 operating assumptions 支撐，不能把 brand 當無上限估值。

**Research role：Core candidate**（企業角色，不是建議現在買入或配置）；成熟現金創造符合 Core 研究池，但估值與質量 gate 限制吸引力。未提供現有持股，portfolio correlation／曝險重疊為 not available，沒有虛構相關係數。

## 9. Bear Case, Risks and Invalidation

**Bear case — Interpretation：** 投資人可能為服務與 AI 成長支付过高價格；現金流近期反彈可能包含 working-capital timing，關稅退款美化近期盈利，輸入成本與 App Store／Google 經濟限制壓低未來 cash conversion。在這種組合下，獲利只小幅落後假設，multiple 收縮就足以使股票回報落後。[Financial record](financial-data.json)、[latest SEC risk disclosure](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm)。

**Observable invalidation conditions — Assumption／Interpretation：**

- Services 成長連續季度明顯失速，且不是 FX／可解釋會計基數：長期變現論點需下修。
- 去除一次性項目後 margin 与現金轉換同步惡化：不可沿用 current normalized FCFF。
- Receivables 增速差／庫存堆積延續並伴隨收款／減值問題：目前 raised gate 升級為實質 earnings-quality finding。
- EU 新條款對 Services 利潤的影響、或 Google revenue-sharing 受到可核驗的結構性不利判決：重建 cashflow。EU 條款更新已發生，財務損益幅度尚待披露，不列為純未來事件。[Current EU terms](https://developer.apple.com/support/apps-in-the-eu/)
- 出現重大 controls weakness、audit qualification 或資金運用異常：重跑 gates，不能用 moat score 抵銷。

截至寫作日，應收與庫存監控訊號已存在，沒有把它們全部列成尚未發生的風險；其餘未完成完整外部 enforcement 搜尋的部分保留 unknown。[Document review](document-review.md)。

**After a decline：** 價格下降只有在基本面假設未損壞時才增加吸引力。先驗證將 SBC 留為成本、去除 tax timing／non-operating income 的 cashflow bridge、应收 aging 与 Services economics，再使用多種估值方法重建 margin of safety。此處**撤回未經校準的 $165–$185 fundamental entry anchor**；單一假設 DCF 不足以給出可靠吸引價位。[Challenge disposition](challenge-review.md)。

## 10. Challenge Pass

**Method：** 先前 document／peer targeted independent challenge 記錄保留；本次另由獨立 reviewer 專注於現金流正常化、成長再投資、折現與 reverse 配對，原 author 並未只重跑 linter。[Historical challenge](challenge-review.md)、[Current normalization challenge](normalization-challenge.md)。

| Claim challenged | Disposition | Consequence |
|---|---|---|
| Total D&A 可全部配 PP&E cash capex | UPHELD objection | 改只用 assumed PPE depreciation $8bn，保留其他 amortization expense；cashflow baseline 從約 $125.6bn 降為約 $120.5bn。[Sources](cashflow-source-review.md) |
| Ireland cash settlement 要再加回 TTM | REJECTED proposed addback | annual+9M−9M 已抵消；TCJA 時點也只正常化一次。[Source bridge](cashflow-source-inputs.json) |
| 常數 FCF 成長不需投資 | UPHELD objection | 用 NOPAT／ROIIC reinvestment budget、terminal reinvestment 及 capex/WC floor；假設非實測 ROIC。[Model](normalized-valuation-output.json) |
| Common-share EV reverse 與 diluted per-share 可以混用 | UPHELD objection | matched reverse target 也用相同 diluted-share proxy，計算可還原 $336.64。[Output](normalized-valuation-output.json) |
| 任意假設都顯示目前價格昂貴 | REJECTED absolute claim | joint bullish case 約 $360，撤回無條件昂貴結論；中央情境要求偏高成長，仍需驗證。[Sensitivity](normalized-valuation-output.json) |

**Verdict change：** 由「FCFF／WACC 尚無完整 bridge、估值不可判斷」更新為「會計 bridge 與模型已核對，基準估值低於市價，但成長／資本效率／折現率的可行性仍決定結論」。不是把 arithmetic PASS 升格為 forecast confirmation。

**Single-input sensitivity：** Base WACC 約6.84%使模型接近參考價；另列多項 joint bullish scenario，不能把它當單一輸入測試。**Most likely way wrong：** 對未來 ROIIC／持續 cash investment、terminal excess return 或成長期作錯估計。**What would change my mind：** issuer 新結果與可辨識的 recurring intangible／capex／cash-tax disclosure、更新 market risk inputs，支持不同現金轉換及 growth path。**Searched but not found：** 精確最新 PP&E-only depreciation、current fully diluted count、完整當期利息拆分／bond YTM、拆分 intangible cash investment；未知項未默認為零。[Review](cashflow-source-review.md)、[Discount inputs](discount-rate-review.md)。

## 11. Disclaimer

This is equity research, not personalised investment advice or licensed financial advice. 沒有依個人資產、負債或目標作配置／買賣建議；假設與不足已揭露，決策由使用者負責。

## What must go right

服務與裝置生態系維持定價／留存；去除一次性退款後 cashflow 仍成長；供應鏈與管理交接執行有效。價格所要求的成長必須轉化成每股 owner economics。[Primary evidence register](document-review.md)。

## What can go wrong

監管侵蝕平台抽成／搜尋授權、AI 或 memory 支出先於收入、工作資本反轉、回購在高估值消耗現金，以及 investors 對倍數的願付價格下降。[SEC risks](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm)。

## What would change my mind

最新年報提供可重複、將 SBC 保留為成本並扣除一次性項目後的 cashflow 改善，應收與庫存疑慮消退，以及較保守成長／折現假設仍能支持市價；或出現相反證據，使 normalized base 下修。結論以可核驗條件更新，不以股價單獨改變。
