# RKLB TradingView alerts（選用；2026-10-13）

> 每個 alert 的意思都是「重新評估研究」（REASSESS），不是下單、不是進出場價；技術面不得覆蓋基本面 thesis。

## Price reassessment levels（monitoring/rules.yaml）

- RKLB crosses 4.43 — reassess vs valuation map (valuation-map boundaries of the auto-draft scenario DCF); research note, not an order
- RKLB crosses 11.37 — reassess vs valuation map (valuation-map boundaries of the auto-draft scenario DCF); research note, not an order
- RKLB crosses 33.38 — reassess vs valuation map (valuation-map boundaries of the auto-draft scenario DCF); research note, not an order

## Volume alert

- RKLB daily volume > 48,451,434（2.5x 50-day average 19,380,574） — check for news / filings; price action alone is not evidence

## Moving-average alerts（僅在 rules.yaml 設定時）

- 未設定（預設不產生技術面 alert）

## Pine Script（選用）

```pine
//@version=5
indicator("RKLB research reassess levels", overlay=true)
hline(4.43)
hline(11.37)
hline(33.38)
alertcondition(ta.cross(close, 4.43), title="RKLB reassess 4.43", message="RKLB crossed 4.43: REASSESS research (not an order)")
alertcondition(ta.cross(close, 11.37), title="RKLB reassess 11.37", message="RKLB crossed 11.37: REASSESS research (not an order)")
alertcondition(ta.cross(close, 33.38), title="RKLB reassess 33.38", message="RKLB crossed 33.38: REASSESS research (not an order)")
```
