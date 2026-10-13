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

Level 4 adds sections 12-22 from the command-center state: research priority changes,
thesis improvements / deteriorations, expectation-gap changes, guidance delivered / missed,
new monitoring triggers, valuation re-rating, research staleness, next-month calendar,
top 5 research tasks (research queue) and deprioritized names.

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


def _next_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    return f"{y + (m == 12)}-{m % 12 + 1:02d}"


def level4_sections(month: str, root: Path, results: List[Dict[str, Any]]) -> str:
    """Level 4 command-center sections (12-22). Every line cites the state file it comes from."""
    import level4_common as l4
    import research_dashboard as dash
    import stale_research as sr
    month_start, month_end = f"{month}-01", f"{_next_month(month)}-01"
    tickers = [r["ticker"] for r in results]
    L = ["", "# Level 4 Research Command Center review", "",
         "> 以下段落引用 state 變化（檔案路徑附在每段），不是摘要報告；優先順序 = 先研究誰，不是買賣建議。",
         "> 口徑：第 1–11 段的 High / Medium / Low 只看本月 snapshot diff；第 12 段起的 HIGH / MEDIUM / LOW 是 Level 4 "
         "研究佇列優先順序，也包含仍未處理的 REASSESS、staleness 與 thesis 重要性，所以兩者可能不同。", ""]
    hist = l4.read_csv(root / "research/queue/priority-history.csv")
    cur_p = {r["ticker"]: r for r in (l4.read_json(root / "research/queue/priorities.json", {}) or {}).get("tickers", [])}
    before = sorted({h["date"] for h in hist if h["date"] < month_start})
    prev_p = {h["ticker"]: h["priority"] for h in hist if before and h["date"] == before[-1]}
    L += ["## 12. Research Priority Changes 研究優先順序變化（research/queue/priority-history.csv）"]
    for t in tickers:
        c = (cur_p.get(t) or {}).get("priority", "n/a")
        p = prev_p.get(t, "（無前期紀錄）")
        L.append(f"- {t}: {p} → {c}" + (f"；{'; '.join((cur_p.get(t) or {}).get('reasons', [])[:2])}" if t in cur_p else ""))
    trends = {t: dash.thesis_trend(t, root) for t in tickers}
    L += ["", "## 13. Thesis Improvements 論點改善（thesis/history.json）"]
    L += [f"- {t}: {'; '.join(v['changes'])}（{v['window']}）" for t, v in trends.items() if v.get("positive")] or ["- 無"]
    L += ["", "## 14. Thesis Deteriorations 論點惡化（thesis/history.json）"]
    L += [f"- {t}: {'; '.join(v['changes'])}（{v['window']}）" for t, v in trends.items() if v.get("negative")] or ["- 無"]
    L += ["", "## 15. Expectation Gap Changes 預期落差變化（valuation/expectation-gap-history.csv）"]
    for t in tickers:
        g = dash.gap_view(t, root)
        L.append(f"- {t}: {g['label']}" + (f"；|gap| 變化 {g['delta_abs_gap']:+.3f}" if g.get("delta_abs_gap") is not None else ""))
    L += ["", "## 16. Guidance Delivered / Missed（management/promises.json，guidance_tracker.py）"]
    for t in tickers:
        prom = l4.read_json(l4.company_dir(t, root) / "management/promises.json", []) or []
        res = [p for p in prom if month_start <= str(p.get("resolved_date") or "") < month_end
               or month_start <= str(p.get("last_checked") or "") < month_end and p.get("status") in ("delayed", "not_evaluable")]
        cnt: Dict[str, int] = {}
        for p in res:
            cnt[p["status"]] = cnt.get(p["status"], 0) + 1
        if not any(p.get("guidance") for p in prom):
            L.append(f"- {t}: No explicit evaluable management guidance found."
                     + (f"（另有 {len(prom)} 個非 guidance 承諾，見 promises.json）" if prom else ""))
        else:
            L.append(f"- {t}: 本月結案 / 檢查 " + (", ".join(f"{k} {v}" for k, v in sorted(cnt.items())) or "無"))
            for p in [p for p in res if p.get("status") in ("missed", "delayed")][:4]:
                L.append(f"  - {p['promise_id']}: {p['status']}（{(p.get('resolution_rule') or '')[:100]}；"
                         f"basis {p.get('comparison_basis')}）")
    q = l4.read_json(root / "research/queue/current.json", {}) or {}
    trig = [i for i in q.get("items", []) if i["event_type"] in ("monitoring_trigger", "thesis_invalidation", "standing_trigger")
            and month_start <= str(i.get("timestamp") or "") < month_end]
    L += ["", "## 17. New Monitoring Triggers 新監控觸發（research/queue/current.json；REASSESS）"]
    L += [f"- {i['ticker']}: {'仍未處理' if i['event_type'] == 'standing_trigger' else '新觸發'}｜{i['reason']}（{i['status']}）"
          for i in trig] or ["- 無"]
    L += ["", "## 18. Valuation Re-Rating 估值重評（snapshots / valuation/historical-percentiles.json）"]
    for r in results:
        d = r["diff"]
        moves = [x for x in d.get("valuation", []) if "percentile" in x or "map" in x.lower() or "區位" in x]
        v = dash.valuation_view(r["ticker"], root)
        L.append(f"- {r['ticker']}: 目前 {v['label']}；最新收盤 {v['latest_close']}（{v['latest_close_date']}），"
                 f"研究價格 {v['research_price']}（{v['research_price_date']}）"
                 + (f"；{'; '.join(moves[:2])}" if moves else ""))
    L += ["", "## 19. Research Staleness 研究過期（stale_research.py）"]
    for x in sr.run(root, write=False, tickers=tickers):
        L.append(f"- {x['ticker']}: {x['severity'] or 'not stale'}" + (f"；{'; '.join(x['reasons'][:2])}" if x["reasons"] else ""))
    nm_start, nm_end = month_end, f"{_next_month(_next_month(month))}-01"
    cal_rows = [r for r in l4.read_csv(root / "research/calendar/upcoming.csv")
                if r.get("status") == "upcoming" and r.get("window_start") and r["window_start"] < nm_end
                and (r.get("window_end") or r["window_start"]) >= nm_start]
    L += ["", "## 20. Next Month Calendar 下月行事曆（research/calendar/upcoming.csv）"]
    L += [f"- {r['ticker']}: {r['event'][:90]}（{r['expected_date']}，{r['date_precision']}，信心 {r['confidence']}）"
          for r in cal_rows] or ["- 無已知事件"]
    open_items = [i for i in q.get("items", []) if i["status"] in ("pending", "processing")]
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    open_items.sort(key=lambda i: (order.get(i.get("priority"), 3), (cur_p.get(i["ticker"]) or {}).get("rank", 99),
                                   i.get("category", "Z")))
    L += ["", "## 21. Top 5 Research Tasks 五項最重要研究任務（research queue）"]
    picked, per = [], {}
    for i in open_items:  # at most two tasks per company so one name cannot fill the list
        if per.get(i["ticker"], 0) < 2:
            picked.append(i)
            per[i["ticker"]] = per.get(i["ticker"], 0) + 1
    L += [f"{n}. {i['ticker']}（{i['priority']}）{i['reason'][:110]} → {i['required_workflow'][:90]}"
          for n, i in enumerate(picked[:5], 1)] or ["1. 佇列無待辦（見第 11 段）"]
    low = [t for t, r in cur_p.items() if r.get("priority") == "LOW"]
    L += ["", "## 22. Deprioritized Names 可降低優先（research/queue/priorities.json）"]
    L += [f"- {t}: {'; '.join(cur_p[t].get('reasons', [])[:2])}" for t in low] or ["- 無"]
    return "\n".join(L) + "\n"


def run(month: Optional[str] = None, root: Path = ROOT, write: bool = True) -> Dict[str, Any]:
    month = month or date.today().strftime("%Y-%m")
    month_start = f"{month}-01"
    results = [review_company(t, root, month_start) for t in rs.tracked_companies(root)]
    text = render(month, results)
    text += level4_sections(month, root, results)
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
