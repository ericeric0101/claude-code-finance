#!/usr/bin/env python3
"""Monthly multi-company research review (minimum viable, rule-based, no ML score).

For every company with research state it compares the latest state snapshot with
the latest snapshot from before the review window (state_diff.diff_states) and
summarizes, across companies:

  1 companies reviewed            7 management promises missed
  2 largest positive thesis moves 8 newly triggered monitoring rules
  3 largest negative thesis moves 9 companies to prioritize next month
  4 valuation gaps widening      10 companies to deprioritize
  5 valuation gaps narrowing     11 five most important research tasks
  6 management promises delivered

Priority framework (transparent rules):
  High   : thesis status changed, guidance changed, new filing, expectation gap
           moved materially, promise missed, or a monitoring rule newly triggered
  Medium : price moved materially (>= 15%) while fundamentals are unchanged
  Low    : no meaningful state change
Price outcomes are never used to grade whether an earlier thesis was right.

Output: research/reviews/YYYY-MM-monthly-review.md (Traditional Chinese prose).
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import research_state as rs  # noqa: E402
import state_diff  # noqa: E402

PRICE_MOVE_PCT = 15.0
GAP_MOVE = 0.03  # 3 pp change in |market - base| counts as material


def _window_pair(snaps: List[Dict[str, Any]], month_start: str) -> tuple:
    if not snaps:
        return None, None
    cur = snaps[-1]
    before = [s for s in snaps[:-1] if s["as_of"] < month_start]
    prev = before[-1] if before else (snaps[-2] if len(snaps) >= 2 else None)
    return prev, cur


def review_company(ticker: str, root: Path, month_start: str) -> Dict[str, Any]:
    snaps = state_diff.list_snapshots(ticker, root)
    if not snaps:
        cur = state_diff.build_snapshot(ticker, root)
        prev = None
    else:
        prev, cur = _window_pair(snaps, month_start)
    d = state_diff.diff_states(prev, cur)
    reasons, tasks = [], []
    thesis_moves = [x for x in d["thesis"] if x.startswith(("[positive]", "[negative]"))]
    if thesis_moves:
        reasons.append("thesis status changed")
    if any("guidance raised" in x or "guidance lowered" in x for x in d["management"]):
        reasons.append("guidance changed")
    pf, cf = (prev or {}).get("financials") or {}, cur.get("financials") or {}
    if prev and pf.get("latest_quarter") != cf.get("latest_quarter"):
        reasons.append(f"new filing ({cf.get('latest_quarter')})")
    gaps = {}
    for k, g in (cur.get("expectation_gap") or {}).items():
        o = ((prev or {}).get("expectation_gap") or {}).get(k)
        if o:
            delta = abs(g["gap_vs_base"]) - abs(o["gap_vs_base"])
            gaps[k] = delta
            if abs(delta) >= GAP_MOVE:
                reasons.append(f"expectation gap {'widened' if delta > 0 else 'narrowed'} ({k})")
    missed = [x for x in d["promises"] if "→ missed" in x or "→ partially_delivered" in x]
    delivered = [x for x in d["promises"] if "→ delivered" in x]
    if missed:
        reasons.append("promise missed")
    new_trig = [x for x in d["monitoring"] if "newly triggered" in x]
    if new_trig:
        reasons.append("monitoring rule newly triggered")
    pv, cv = (prev or {}).get("valuation") or {}, cur.get("valuation") or {}
    p0, p1 = pv.get("latest_close") or pv.get("price"), cv.get("latest_close") or cv.get("price")
    move = (p1 / p0 - 1) * 100 if p0 and p1 else None
    if reasons:
        priority = "High"
    elif move is not None and abs(move) >= PRICE_MOVE_PCT:
        priority, reasons = "Medium", [f"price moved {move:+.1f}% with fundamentals unchanged"]
    else:
        priority, reasons = "Low", ["no meaningful state change"]
    for x in new_trig:
        tasks.append(f"{ticker}: 重新評估 {x.split('REASSESS: ')[-1]}")
    for x in missed:
        tasks.append(f"{ticker}: 檢查未達成承諾的原因 {x.split(']')[-1].strip()}")
    pending = [pid for pid, p in ((cur.get("management") or {}).get("promises") or {}).items()
               if p["status"] == "pending"]
    if pending:
        tasks.append(f"{ticker}: 下次財報後結案 {len(pending)} 個 pending 承諾")
    for c in (cur.get("next_catalysts") or [])[:1]:
        tasks.append(f"{ticker}: 追蹤催化劑 — {c}")
    if prev is None:
        tasks.insert(0, f"{ticker}: 尚無先前狀態，下次更新時建立比較基準")
    return {"ticker": ticker, "prev": (prev or {}).get("as_of"), "cur": cur.get("as_of"),
            "prev_retrospective": (prev or {}).get("retrospective"), "diff": d, "priority": priority,
            "reasons": reasons, "tasks": tasks, "gaps": gaps, "missed": missed, "delivered": delivered,
            "new_triggers": new_trig, "price_move": move, "action": cur.get("action")}


def render(month: str, results: List[Dict[str, Any]]) -> str:
    L = [f"# {month} 月度研究檢視（Monthly Research Review）", "",
         "> 規則式排序，非模型分數。股價事後表現不用來評斷當初論點對錯；監控規則觸發只代表需要重新評估（REASSESS）。", ""]
    L += ["## 1. Companies reviewed 檢視公司", "", "| Ticker | 比較區間 | Action | Priority | 理由 |", "|---|---|---|---|---|"]
    for r in results:
        rng = f"{r['prev'] or '（無）'} → {r['cur']}" + ("（前為 retrospective）" if r["prev_retrospective"] else "")
        L.append(f"| {r['ticker']} | {rng} | {r['action']} | {r['priority']} | {'; '.join(r['reasons'])} |")
    pos = [(r["ticker"], x) for r in results for x in r["diff"]["thesis"] if x.startswith("[positive]")]
    neg = [(r["ticker"], x) for r in results for x in r["diff"]["thesis"] if x.startswith("[negative]")]
    L += ["", "## 2. Largest positive thesis changes 最大正面論點變化"] + ([f"- {t}: {x[11:]}" for t, x in pos] or ["- 無"])
    L += ["", "## 3. Largest negative thesis changes 最大負面論點變化"] + ([f"- {t}: {x[11:]}" for t, x in neg] or ["- 無"])
    wid = sorted(((r["ticker"], k, v) for r in results for k, v in r["gaps"].items() if v > 0.005), key=lambda x: -x[2])
    nar = sorted(((r["ticker"], k, v) for r in results for k, v in r["gaps"].items() if v < -0.005), key=lambda x: x[2])
    L += ["", "## 4. Valuation gaps widening 預期落差擴大"] + ([f"- {t} {k}: |gap| {v:+.3f}" for t, k, v in wid] or ["- 無"])
    L += ["", "## 5. Valuation gaps narrowing 預期落差收斂"] + ([f"- {t} {k}: |gap| {v:+.3f}" for t, k, v in nar] or ["- 無"])
    L += ["", "## 6. Management promises delivered 已兌現承諾"] + (
        [f"- {r['ticker']}: {x.split(']', 1)[1].strip()}" for r in results for x in r["delivered"]] or ["- 本期無新結案的兌現承諾"])
    L += ["", "## 7. Management promises missed 未兌現承諾"] + (
        [f"- {r['ticker']}: {x.split(']', 1)[1].strip()}" for r in results for x in r["missed"]] or ["- 無"])
    L += ["", "## 8. Newly triggered monitoring rules 新觸發監控規則（REASSESS）"] + (
        [f"- {r['ticker']}: {x.split(']', 1)[1].strip()}" for r in results for x in r["new_triggers"]] or ["- 無"])
    hi = [r for r in results if r["priority"] == "High"]
    med = [r for r in results if r["priority"] == "Medium"]
    low = [r for r in results if r["priority"] == "Low"]
    L += ["", "## 9. Companies to prioritize next month 下月優先"] + (
        [f"- {r['ticker']}（High）：{'; '.join(r['reasons'])}" for r in hi] +
        [f"- {r['ticker']}（Medium）：{'; '.join(r['reasons'])}" for r in med] or ["- 無"])
    L += ["", "## 10. Companies to deprioritize 可降低優先"] + (
        [f"- {r['ticker']}：{'; '.join(r['reasons'])}" for r in low] or ["- 無"])
    tasks = [t for r in sorted(results, key=lambda r: ("High", "Medium", "Low").index(r["priority"])) for t in r["tasks"]]
    L += ["", "## 11. Five most important research tasks 五項最重要研究任務"] + (
        [f"{i}. {t}" for i, t in enumerate(tasks[:5], 1)] or ["1. 無待辦"])
    L += ["", "## Priority framework", "- High：論點狀態改變、guidance 改變、新財報、預期落差顯著變化、承諾未兌現、監控規則新觸發",
          f"- Medium：股價變動 ≥ {PRICE_MOVE_PCT:.0f}% 但基本面未變", "- Low：無有意義的狀態變化", ""]
    return "\n".join(L)


def run(month: Optional[str] = None, root: Path = ROOT, write: bool = True) -> Dict[str, Any]:
    month = month or date.today().strftime("%Y-%m")
    month_start = f"{month}-01"
    results = [review_company(t, root, month_start) for t in rs.tracked_companies(root)]
    text = render(month, results)
    out = root / "research/reviews" / f"{month}-monthly-review.md"
    if write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    return {"path": str(out), "companies": [r["ticker"] for r in results],
            "priorities": {r["ticker"]: r["priority"] for r in results}, "text": text}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--month", help="YYYY-MM (default: current month)")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args(argv)
    res = run(args.month, args.root)
    print(res["path"])
    print(res["priorities"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
