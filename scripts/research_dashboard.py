#!/usr/bin/env python3
"""Research command-center dashboard (Level 4): research/dashboard/current.{md,json}.

One row per watchlist company:
| Ticker | Action | Priority | Thesis trend | Valuation | Expectation gap | Triggers | Next catalyst | Last review |
plus research confidence (explainable), staleness, KPI / guidance coverage and the open
research queue. It answers:
  - which company's thesis improved / deteriorated the most
  - whose expectation gap narrowed the most
  - whose valuation became cheaper (vs its OWN model and history; raw EV/Sales is never
    compared across sectors)
  - which stocks rose without fundamentals following
  - which research is stale
Only relative state, trend, priority and confidence are compared across companies.
Action labels are copied from thesis/current.yaml (WATCH is not "wait for a price");
nothing here is a buy / sell instruction.

Usage: python3 scripts/research_dashboard.py [--as-of YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalyst_calendar as cal  # noqa: E402
import level4_common as l4  # noqa: E402
import research_confidence as rconf  # noqa: E402
import research_queue as rq  # noqa: E402
import research_state as rs  # noqa: E402
import stale_research as sr  # noqa: E402

WEIGHT = {"high": 2, "medium": 1, "low": 1}


def thesis_trend(ticker: str, root: Path) -> Dict[str, Any]:
    hist = l4.read_json(l4.company_dir(ticker, root) / "thesis/history.json", []) or []
    hist = [h for h in hist if not h.get("retrospective")]
    if len(hist) < 2:
        return {"label": "Baseline（無前期）", "net": 0, "changes": []}
    cur = hist[-1]
    prev = next((h for h in reversed(hist[:-1]) if h.get("components") != cur.get("components")), hist[-2])
    pos = neg = 0
    changes = []
    for k, c in (cur.get("components") or {}).items():
        p = (prev.get("components") or {}).get(k)
        if not p or p.get("status") == c.get("status"):
            continue
        kind = rs.classify_transition(p.get("status"), c.get("status"))
        w = WEIGHT.get(c.get("importance"), 1)
        if kind == "positive":
            pos += w
        elif kind == "negative":
            neg += w
        changes.append(f"{k}: {p.get('status')} → {c.get('status')} ({kind})")
    label = ("Improving" if pos > neg else "Deteriorating" if neg > pos else "Mixed" if pos else "Stable")
    return {"label": label, "net": pos - neg, "positive": pos, "negative": neg, "changes": changes,
            "window": f"{prev.get('as_of')} → {cur.get('as_of')}"}


def valuation_view(ticker: str, root: Path) -> Dict[str, Any]:
    base = l4.company_dir(ticker, root)
    lat = l4.read_json(base / "valuation/latest.json", {}) or {}
    px = l4.prices(ticker, root)
    close = px[-1] if px else None
    zones = (lat.get("valuation_map") or {}).get("zones") or []
    pos = (lat.get("valuation_map") or {}).get("current_position")
    if close and zones:
        for z in zones:
            lo, hi = z.get("low"), z.get("high")
            if (lo is None or close["close"] >= lo) and (hi is None or close["close"] < hi):
                pos = z.get("interpretation")
    p = (pos or "").lower()
    label = ("Expensive（高於所有 bull 值）" if "above all" in p else
             "Demanding（介於 base 與 bull）" if "base and bull" in p or "base-value spread" in p else
             "Below base（介於 bear 與 base）" if "bear and base" in p or "bear-value spread" in p else
             "Below all bear values" if "below all" in p else "Not modeled")
    ref = lat.get("price")
    move = (close["close"] / float(ref) - 1) * 100 if close and ref else None
    return {"label": label, "position": pos, "latest_close": close["close"] if close else None,
            "latest_close_date": close["date"] if close else None, "research_price": ref,
            "research_price_date": lat.get("price_date"), "move_since_research_pct": round(move, 2) if move is not None else None,
            "valuation_confidence": lat.get("valuation_confidence")}


def gap_view(ticker: str, root: Path) -> Dict[str, Any]:
    rows = l4.read_csv(l4.company_dir(ticker, root) / "valuation/expectation-gap-history.csv")
    if not rows:
        return {"label": "Not quantified", "delta": None}
    dates = sorted({r["date"] for r in rows})
    cur = [r for r in rows if r["date"] == dates[-1]]
    r = cur[0]
    try:
        gap = float(r["gap_vs_base"])
    except (TypeError, ValueError):
        return {"label": "Not quantified", "delta": None}
    delta = None
    if len(dates) >= 2:
        prev = next((x for x in rows if x["date"] == dates[-2] and x["metric"] == r["metric"]), None)
        if prev and prev.get("gap_vs_base"):
            delta = round(abs(gap) - abs(float(prev["gap_vs_base"])), 4)
    width = "Wide" if abs(gap) >= 0.05 else "Narrow"
    direction = r.get("direction") or "n/a"
    return {"label": f"{width}（market {float(r['market_implied']):.1%} vs base {float(r['base']):.1%}，{direction}）",
            "metric": r["metric"], "gap_vs_base": gap, "delta_abs_gap": delta, "direction": direction,
            "date": dates[-1]}


def _close_on_or_before(px: List[Dict[str, Any]], d: str) -> Optional[float]:
    c = [p["close"] for p in px if p["date"] <= d]
    return c[-1] if c else None


def build(root: Path = ROOT, as_of: Optional[str] = None, write: bool = True) -> Dict[str, Any]:
    as_of = l4.today(as_of)
    policy = l4.load_policy(root)
    pri = {r["ticker"]: r for r in (l4.read_json(root / "research/queue/priorities.json", {}) or {}).get("tickers", [])}
    calendar = l4.read_csv(root / "research/calendar/upcoming.csv")
    queue = rq.load(root)
    rows = []
    for e in l4.load_watchlist(root):
        t = e["ticker"]
        base = l4.company_dir(t, root)
        if not (base / "thesis/current.yaml").exists():
            continue
        th = l4.thesis(t, root)
        stale = sr.check(t, root, as_of, calendar)
        trend = thesis_trend(t, root)
        val = valuation_view(t, root)
        gap = gap_view(t, root)
        rules = rs.check_rules(t, root)
        trig = [r["rule"] for r in rules if r["state"] == "triggered"]
        nc = cal.next_catalyst(calendar, t)
        conf = rconf.assess(t, root, stale)
        px = l4.prices(t, root)
        full = stale.get("last_full_review")
        p_full = _close_on_or_before(px, full) if full else None
        move_full = (px[-1]["close"] / p_full - 1) * 100 if px and p_full else None
        p_3m = px[-64]["close"] if len(px) > 64 else None
        move_3m = (px[-1]["close"] / p_3m - 1) * 100 if p_3m else None
        open_items = [i for i in queue["items"] if i["ticker"] == t and i["status"] in rq.OPEN]
        gva = l4.read_json(base / "management/guidance-vs-actual.json", {}) or {}
        kc = l4.read_json(base / "financials/kpi-coverage.json", {}) or {}
        rows.append({
            "ticker": t, "action": th.get("action"), "draft_auto": bool(th.get("draft_auto")),
            "priority": (pri.get(t) or {}).get("priority", "n/a"), "priority_reasons": (pri.get(t) or {}).get("reasons", []),
            "rank": (pri.get(t) or {}).get("rank"),
            "thesis_trend": trend, "valuation": val, "expectation_gap": gap, "triggers": trig,
            "next_catalyst": nc, "last_review": stale.get("last_review"), "days_since_review": stale.get("days_since_review"),
            "stale": stale, "confidence": conf, "price_move_since_full_review_pct": round(move_full, 1) if move_full is not None else None,
            "price_move_3m_pct": round(move_3m, 1) if move_3m is not None else None,
            "open_queue_items": len(open_items), "immediate_alerts": [i["event_id"] for i in open_items if i.get("immediate_alert")],
            "guidance": {k: gva.get(k) for k in ("counts", "evaluated", "not_evaluable", "message")},
            "kpi": {k: kc.get(k) for k in ("sector", "required_unavailable", "optional_available")},
        })
    big = policy["market"]["large_move_pct"]
    answers = {
        "thesis_improved_most": _pick(rows, lambda r: r["thesis_trend"]["net"], positive=True,
                                      fmt=lambda r: f"{r['ticker']}（{'; '.join(r['thesis_trend']['changes'])}）"),
        "thesis_deteriorated_most": _pick(rows, lambda r: -r["thesis_trend"]["net"], positive=True,
                                          fmt=lambda r: f"{r['ticker']}（{'; '.join(r['thesis_trend']['changes'])}）"),
        "expectation_gap_narrowed_most": _pick(rows, lambda r: -(r["expectation_gap"].get("delta_abs_gap") or 0), positive=True,
                                               fmt=lambda r: f"{r['ticker']}（|gap| {r['expectation_gap']['delta_abs_gap']:+.3f}）"),
        "valuation_cheaper": _pick(rows, lambda r: -(r["valuation"].get("move_since_research_pct") or 0), positive=True,
                                   fmt=lambda r: f"{r['ticker']}（最新收盤較研究價格 {r['valuation']['move_since_research_pct']:+.1f}%，"
                                                 f"相對自身估值地圖：{r['valuation']['label']}）"),
        "price_up_fundamentals_lagging": [
            f"{r['ticker']}（自上次完整檢視 {r['price_move_since_full_review_pct']:+.1f}%，thesis {r['thesis_trend']['label']}）"
            for r in rows if (r["price_move_since_full_review_pct"] or 0) >= big and r["thesis_trend"]["net"] <= 0],
        "stale_research": [f"{r['ticker']}（{r['stale']['severity']}：{'; '.join(r['stale']['reasons'][:2])}）"
                           for r in rows if r["stale"]["stale"]],
    }
    doc = {"as_of": as_of, "generated_at": l4.now_iso(), "companies": rows, "answers": answers,
           "note": "Command center compares relative state, trend, priority and confidence only; "
                   "raw multiples are not compared across sectors. Not a buy / sell list."}
    if write:
        l4.write_json(root / "research/dashboard/current.json", doc)
        (root / "research/dashboard/current.md").write_text(render(doc, queue), encoding="utf-8")
    return doc


def _pick(rows: List[Dict[str, Any]], key, positive: bool, fmt) -> List[str]:
    cands = sorted(rows, key=key, reverse=True)
    out = [fmt(r) for r in cands if key(r) > 0] if positive else [fmt(r) for r in cands]
    return out[:3]


def render(doc: Dict[str, Any], queue: Dict[str, Any]) -> str:
    L = [f"# Research Command Center（{doc['as_of']}）", "",
         "> 研究優先順序儀表板。Action 取自 thesis/current.yaml；觸發 = REASSESS，不是買賣指令；"
         "估值只和公司自己的估值地圖 / 歷史比較，不跨產業比較 EV/Sales。", "",
         "| Ticker | Action | Priority | Thesis trend | Valuation | Expectation gap | Triggers | Next catalyst | Last review |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(doc["companies"], key=lambda r: r.get("rank") or 99):
        nc = r["next_catalyst"]
        ncs = f"{nc['event'][:48]}（{nc['expected_date']}）" if nc else "—"
        lr = f"{r['days_since_review']} 天前" if r["days_since_review"] is not None else "—"
        L.append(f"| {r['ticker']} | {r['action']}{'（draft_auto）' if r['draft_auto'] else ''} | {r['priority']} | "
                 f"{r['thesis_trend']['label']} | {r['valuation']['label']} | {r['expectation_gap']['label']} | "
                 f"{len(r['triggers'])} | {ncs} | {lr} |")
    a = doc["answers"]
    L += ["", "## Command center 問答", "",
          "- Thesis 改善最大：" + ("；".join(a["thesis_improved_most"]) or "無（本期沒有 thesis 狀態改善）"),
          "- Thesis 惡化最大：" + ("；".join(a["thesis_deteriorated_most"]) or "無（本期沒有 thesis 狀態惡化）"),
          "- Expectation gap 縮小最多：" + ("；".join(a["expectation_gap_narrowed_most"]) or "無（gap 未縮小或無前期）"),
          "- 估值變便宜（相對自身研究價格 / 估值地圖）：" + ("；".join(a["valuation_cheaper"]) or "無"),
          "- 股價上漲但基本面未跟上：" + ("；".join(a["price_up_fundamentals_lagging"]) or "無"),
          "- 研究已 stale：" + ("；".join(a["stale_research"]) or "無"), ""]
    L += ["## 優先順序理由", ""]
    for r in sorted(doc["companies"], key=lambda r: r.get("rank") or 99):
        L.append(f"- **{r['ticker']}**（{r['priority']}）：" + "；".join(r["priority_reasons"][:5]))
    L += ["", "## Research confidence（可解釋組成，非公司評分）", ""]
    for r in doc["companies"]:
        c = r["confidence"]
        L.append(f"- **{r['ticker']}** overall: {c['overall']}")
        L += [f"  - {k}: {v['grade']} — {v['reason']}" for k, v in c["components"].items()]
    L += ["", "## Triggered rules（REASSESS）", ""]
    for r in doc["companies"]:
        L.append(f"- {r['ticker']}: " + (", ".join(r["triggers"]) or "無"))
    L += ["", "## Guidance vs actual / KPI coverage", ""]
    for r in doc["companies"]:
        g = r["guidance"]
        L.append(f"- {r['ticker']}: guidance {g.get('message') or g.get('counts')}；KPI sector {r['kpi'].get('sector')}，"
                 f"required unavailable {r['kpi'].get('required_unavailable') or '無'}")
    open_items = [i for i in queue["items"] if i["status"] in rq.OPEN]
    L += ["", f"## Open research queue（{len(open_items)}）", "", rq.render(queue), ""]
    return "\n".join(L)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--as-of")
    args = ap.parse_args(argv)
    doc = build(as_of=args.as_of)
    print((ROOT / "research/dashboard/current.md").read_text()[:3000])
    return 0 if doc else 1


if __name__ == "__main__":
    raise SystemExit(main())
