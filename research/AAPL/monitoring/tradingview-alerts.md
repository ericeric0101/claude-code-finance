# AAPL TradingView alerts（選用；2026-10-13）

> 每個 alert 的意思都是「重新評估研究」（REASSESS），不是下單、不是進出場價；技術面不得覆蓋基本面 thesis。

## Price reassessment levels（monitoring/rules.yaml）

- AAPL crosses 117.00 — reassess vs valuation map (valuation-map boundaries from DCF and earnings-method bear / base / bull values, 2026-10-11); research note, not an order
- AAPL crosses 174.00 — reassess vs valuation map (valuation-map boundaries from DCF and earnings-method bear / base / bull values, 2026-10-11); research note, not an order
- AAPL crosses 194.00 — reassess vs valuation map (valuation-map boundaries from DCF and earnings-method bear / base / bull values, 2026-10-11); research note, not an order
- AAPL crosses 242.00 — reassess vs valuation map (valuation-map boundaries from DCF and earnings-method bear / base / bull values, 2026-10-11); research note, not an order
- AAPL crosses 295.00 — reassess vs valuation map (valuation-map boundaries from DCF and earnings-method bear / base / bull values, 2026-10-11); research note, not an order
- AAPL crosses 318.00 — reassess vs valuation map (valuation-map boundaries from DCF and earnings-method bear / base / bull values, 2026-10-11); research note, not an order

## Volume alert

- AAPL daily volume > 103,465,217（2.5x 50-day average 41,386,087） — check for news / filings; price action alone is not evidence

## Moving-average alerts（僅在 rules.yaml 設定時）

- 未設定（預設不產生技術面 alert）

## Pine Script（選用）

```pine
//@version=5
indicator("AAPL research reassess levels", overlay=true)
hline(117)
hline(174)
hline(194)
hline(242)
hline(295)
hline(318)
alertcondition(ta.cross(close, 117), title="AAPL reassess 117", message="AAPL crossed 117: REASSESS research (not an order)")
alertcondition(ta.cross(close, 174), title="AAPL reassess 174", message="AAPL crossed 174: REASSESS research (not an order)")
alertcondition(ta.cross(close, 194), title="AAPL reassess 194", message="AAPL crossed 194: REASSESS research (not an order)")
alertcondition(ta.cross(close, 242), title="AAPL reassess 242", message="AAPL crossed 242: REASSESS research (not an order)")
alertcondition(ta.cross(close, 295), title="AAPL reassess 295", message="AAPL crossed 295: REASSESS research (not an order)")
alertcondition(ta.cross(close, 318), title="AAPL reassess 318", message="AAPL crossed 318: REASSESS research (not an order)")
```
