# PL TradingView alerts（選用；2026-10-13）

> 每個 alert 的意思都是「重新評估研究」（REASSESS），不是下單、不是進出場價；技術面不得覆蓋基本面 thesis。

## Price reassessment levels（monitoring/rules.yaml）

- PL crosses 3.00 — reassess vs valuation map (valuation-map boundaries from the five-year scenario DCF (bear / base / bull), 2026-10-11); research note, not an order
- PL crosses 12.00 — reassess vs valuation map (valuation-map boundaries from the five-year scenario DCF (bear / base / bull), 2026-10-11); research note, not an order
- PL crosses 25.00 — reassess vs valuation map (valuation-map boundaries from the five-year scenario DCF (bear / base / bull), 2026-10-11); research note, not an order

## Volume alert

- PL daily volume > 23,553,284（2.5x 50-day average 9,421,314） — check for news / filings; price action alone is not evidence

## Moving-average alerts（僅在 rules.yaml 設定時）

- 未設定（預設不產生技術面 alert）

## Pine Script（選用）

```pine
//@version=5
indicator("PL research reassess levels", overlay=true)
hline(3)
hline(12)
hline(25)
alertcondition(ta.cross(close, 3), title="PL reassess 3", message="PL crossed 3: REASSESS research (not an order)")
alertcondition(ta.cross(close, 12), title="PL reassess 12", message="PL crossed 12: REASSESS research (not an order)")
alertcondition(ta.cross(close, 25), title="PL reassess 25", message="PL crossed 25: REASSESS research (not an order)")
```
