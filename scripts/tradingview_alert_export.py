#!/usr/bin/env python3
"""TradingView alert export (Level 4, P2, optional): research/<TICKER>/monitoring/tradingview-alerts.md.

Contents: price reassessment levels from monitoring/rules.yaml (valuation-map boundaries),
volume alerts (config/research-policy.yaml market.volume_ratio x 50-day average) and
moving-average alerts only when monitoring.tradingview.moving_averages is configured.
Every alert means "reassess the research", never an order; technical signals never
override the fundamental thesis. TradingView is optional; nothing here calls it.

Usage: python3 scripts/tradingview_alert_export.py PL
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import level4_common as l4  # noqa: E402


def export(ticker: str, root: Path = ROOT, as_of: Optional[str] = None, write: bool = True) -> str:
    t = ticker.upper()
    base = l4.company_dir(t, root)
    rules = (l4.read_yaml(base / "monitoring/rules.yaml", {}) or {}).get("monitoring") or {}
    market = rules.get("market") or {}
    tv = rules.get("tradingview") or {}
    policy = l4.load_policy(root)
    px = l4.prices(t, root)
    vols = [p["volume"] for p in px[-50:] if p.get("volume")]
    avg = sum(vols) / len(vols) if vols else None
    levels: List[float] = list(market.get("reassess_price") or [])
    L = [f"# {t} TradingView alerts（選用；{l4.today(as_of)}）", "",
         "> 每個 alert 的意思都是「重新評估研究」（REASSESS），不是下單、不是進出場價；技術面不得覆蓋基本面 thesis。", "",
         "## Price reassessment levels（monitoring/rules.yaml）", ""]
    L += [f"- {t} crosses {lv:.2f} — reassess vs valuation map ({market.get('basis', 'rules.yaml')}); research note, not an order"
          for lv in levels] or ["- 無設定"]
    L += ["", "## Volume alert", ""]
    if avg:
        thr = avg * float(policy["market"]["volume_ratio"])
        L.append(f"- {t} daily volume > {thr:,.0f}（{policy['market']['volume_ratio']}x 50-day average {avg:,.0f}）"
                 " — check for news / filings; price action alone is not evidence")
    else:
        L.append("- 無成交量資料")
    mas = tv.get("moving_averages") or []
    L += ["", "## Moving-average alerts（僅在 rules.yaml 設定時）", ""]
    L += [f"- {t} close crosses SMA{n} — background context only" for n in mas] or ["- 未設定（預設不產生技術面 alert）"]
    if levels:
        conds = "\n".join(f'alertcondition(ta.cross(close, {lv}), title="{t} reassess {lv}", '
                          f'message="{t} crossed {lv}: REASSESS research (not an order)")' for lv in levels)
        L += ["", "## Pine Script（選用）", "", "```pine", "//@version=5", f'indicator("{t} research reassess levels", overlay=true)']
        L += [f"hline({lv})" for lv in levels]
        L += [conds, "```"]
    text = "\n".join(L) + "\n"
    if write:
        (base / "monitoring/tradingview-alerts.md").write_text(text, encoding="utf-8")
    return text


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="+")
    args = ap.parse_args(argv)
    for t in args.tickers:
        export(t)
        print(f"research/{t.upper()}/monitoring/tradingview-alerts.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
