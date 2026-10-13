#!/usr/bin/env python3
"""Research event classifier (Level 4): which workflow does an event require?

Categories
  A FULL_UPDATE_REQUIRED      new 10-Q / 10-K, earnings release, major guidance cut,
                              thesis invalidation triggered        → /update-stock TICKER
  B TARGETED_UPDATE           contract award, product launch, management change, capital
                              raise, acquisition, monitoring trigger, promise missed /
                              delayed, guidance raise, expectation-gap / valuation move
                              → the one skill that owns the affected state
  C MARKET_REACTION_ONLY      price / volume / drawdown / 52-week events with no new filing
                              → market-reaction (price_reaction.py analyze); no full DCF
                              unless the state changed
  D LOW_PRIORITY_INFORMATIONAL routine Form 4 / 144, proxy, other 8-K items → log only

Each classified event carries: event_type, ticker, timestamp, source, severity
(high / medium / low), category, required_workflow, reason, immediate_alert.
An immediate alert still only means REASSESS: no output of this engine is a buy or
sell instruction.

Usage: python3 scripts/research_event_classifier.py PL [--as-of YYYY-MM-DD]   (detect + classify, dry run)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import level4_common as l4  # noqa: E402

CATEGORY_NAMES = {"A": "FULL_UPDATE_REQUIRED", "B": "TARGETED_UPDATE", "C": "MARKET_REACTION_ONLY",
                  "D": "LOW_PRIORITY_INFORMATIONAL"}
MARKET_TYPES = ("major_price_move", "abnormal_volume", "major_drawdown", "new_52w_high", "new_52w_low",
                "large_move_since_review")
FILING_TYPES = ("sec_10q", "sec_10k", "earnings_release", "guidance_update", "major_contract", "acquisition",
                "capital_raise", "management_change", "product_launch", "investor_presentation")
TARGETED = {  # event_type → (owning workflow, default severity)
    "major_contract": ("thesis-monitor: update demand / backlog components with the award (management-change for wording)", "medium"),
    "product_launch": ("thesis-monitor: update the product / execution component; KPI registry milestone", "medium"),
    "management_change": ("management-change: record the change; thesis-monitor if a component depends on the person", "medium"),
    "capital_raise": ("valuation-monitor: share count / dilution; thesis-monitor per-share component", "medium"),
    "acquisition": ("thesis-monitor + valuation-monitor: deal terms, dilution and strategy fit", "medium"),
    "investor_presentation": ("management-change: compare new targets / wording with management history", "low"),
    "monitoring_trigger": ("research-monitor: REASSESS the triggered rule against fresh evidence", "medium"),
    "standing_trigger": ("thesis-monitor / research-monitor: the REASSESS is still open — record the outcome "
                         "(keep, change status with evidence, or adjust the rule with a stated reason)", "medium"),
    "promise_missed": ("management-change: why the promise was missed; thesis-monitor if it maps to a component", "high"),
    "promise_delayed": ("management-change: timing slip; thesis-monitor for the affected milestone component", "medium"),
    "guidance_update": ("management-change + valuation-monitor: compare new range with base case", "medium"),
    "expectation_gap_change": ("valuation-monitor: reverse DCF / expectation gap review", "medium"),
    "valuation_rerating": ("valuation-monitor: historical percentiles and valuation map", "medium"),
    "management_wording_change": ("management-change: review the semantic diff finding", "low"),
    "macro_thesis_link": ("thesis-monitor: check only the linked component", "low"),
    "activist_stake": ("thesis-monitor: governance / capital allocation check", "medium"),
    "restructuring": ("thesis-monitor + valuation-monitor: restructuring cost and margin path", "medium"),
    "impairment": ("valuation-monitor: asset base / impairment drivers", "medium"),
    "company_announcement": ("thesis-monitor: read and decide relevance", "low"),
}
FULL_UPDATE = "/update-stock {t} (Level 3 UPDATE pipeline: research_pipeline.py update)"
MARKET_WORKFLOW = ("market-reaction: price_reaction.py analyze {t} (event window, abnormal return); "
                   "no full DCF unless the state changed")


def _dilution_is_core(thesis: Dict[str, Any]) -> bool:
    for name, c in (thesis.get("components") or {}).items():
        if ("dilution" in name or "per_share" in name) and c.get("importance") == "high":
            return True
    return False


def classify(event: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Add category / severity / required_workflow / reason / immediate_alert to a detected event."""
    ctx = context or {}
    e = dict(event)
    t, et, d = e["ticker"], e["event_type"], e.get("details") or {}
    same_day_filing = ctx.get("filing_dates") or set()
    cat, sev, wf, reason, alert = "D", "low", "log only (no research action)", "", False
    if et in ("sec_10q", "sec_10k"):
        cat, sev, wf = "A", "high", FULL_UPDATE.format(t=t)
        reason = f"new {d.get('form')} (report date {d.get('report_date')})" + \
            ("; filed after the filing the state was built from" if d.get("newer_than_state") else "")
        if d.get("amendment"):
            cat, sev, reason = "B", "medium", f"amended {d.get('form')}: check what changed before a full update"
            wf = "stock-analysis verify_data on the amended items; full UPDATE only if financials changed"
    elif et == "earnings_release":
        cat, sev, wf, reason = "A", "high", FULL_UPDATE.format(t=t), "earnings release (8-K Item 2.02)"
    elif et == "thesis_invalidation":
        cat, sev, wf, alert = "A", "high", FULL_UPDATE.format(t=t) + "; thesis-monitor REASSESS", True
        reason = f"thesis invalidation rule '{d.get('rule')}' triggered → REASSESS (not an order)"
    elif et == "guidance_update":
        cut = d.get("direction") == "lowered" and not d.get("spending_plan")
        if cut:
            cat, sev, wf, alert = "A", "high", FULL_UPDATE.format(t=t), True
            reason = f"guidance cut: {d.get('metric')} {d.get('period')} {d.get('previous')} → {d.get('current')}"
        else:
            cat, sev = "B", "medium"
            wf = TARGETED[et][0]
            kind = "spending plan changed" if d.get("spending_plan") else "guidance raised"
            reason = f"{kind}: {d.get('metric')} {d.get('period')} {d.get('previous')} → {d.get('current')}"
    elif et in TARGETED:
        cat = "B"
        wf, sev = TARGETED[et]
        reason = {
            "monitoring_trigger": f"monitoring rule '{d.get('rule')}' triggered (value {d.get('value')}, warning {d.get('warning')}) → REASSESS",
            "standing_trigger": f"{d.get('rule_type')} rule '{d.get('rule')}' still triggered since {d.get('triggered_since')} → REASSESS still open",
            "promise_missed": f"promise {d.get('promise_id')} missed ({d.get('rule')})",
            "promise_delayed": f"promise {d.get('promise_id')} delayed ({d.get('rule')})",
            "capital_raise": f"capital raise filing ({d.get('form', 'release')})",
            "acquisition": f"acquisition / merger filing ({d.get('form', 'release')})",
            "expectation_gap_change": f"expectation gap {d.get('direction')} ({d.get('metric')}, {d.get('change')})",
            "valuation_rerating": f"{d.get('multiple')} {d.get('window')} percentile {d.get('previous')} → {d.get('current')}",
            "management_wording_change": f"management {d.get('dimension')}: {d.get('change')}",
        }.get(et, d.get("description") or et.replace("_", " "))
        if et == "capital_raise" and ctx.get("dilution_core"):
            sev, reason = "high", reason + "; dilution is a high-importance thesis component"
        if et == "promise_missed" and d.get("spending_plan"):
            sev, reason = "medium", reason + " (spending-plan deviation)"
        if et == "management_wording_change" and d.get("dimension") == "timing":
            sev = "medium"
    elif et in MARKET_TYPES:
        cat, wf = "C", MARKET_WORKFLOW.format(t=t)
        big = abs(d.get("move_pct") or 0) >= ctx.get("large_move_pct", 15) or et in ("major_drawdown", "large_move_since_review")
        sev = "medium" if big else "low"
        near = [x for x in same_day_filing if abs((l4.days_between(x, e["timestamp"]) or 99)) <= 2]
        reason = {
            "major_price_move": f"1-day move {d.get('move_pct')}%",
            "abnormal_volume": f"volume {d.get('volume_ratio')}x 50-day average",
            "major_drawdown": f"drawdown {d.get('drawdown_pct')}% from 52-week high {d.get('high_252')}",
            "new_52w_high": f"new 52-week closing high {d.get('close')}",
            "new_52w_low": f"new 52-week closing low {d.get('close')}",
            "large_move_since_review": f"{d.get('move_pct')}% since the research price {d.get('reference_price')} ({d.get('reference_date')})",
        }[et]
        if near:
            sev, reason = "low", reason + f"; coincides with a filing on {sorted(near)[-1]} (covered by that event)"
        else:
            reason += "; no new filing — price action alone is not evidence of a fundamental change"
    elif et == "insider_filings":
        cat, sev = "D", "low"
        reason = f"routine insider filings: {d.get('form4')} Form 4, {d.get('form144')} Form 144 ({d.get('first')}..{d.get('last')})"
    elif et in ("proxy_statement", "shareholder_vote", "other_event", "non_reliance", "bankruptcy"):
        if et in ("non_reliance", "bankruptcy"):
            cat, sev, wf, alert = "A", "high", FULL_UPDATE.format(t=t), True
            reason = f"{et.replace('_', ' ')} (8-K) → REASSESS"
        else:
            reason = {"proxy_statement": "proxy statement (DEF 14A): governance / compensation reference",
                      "shareholder_vote": "shareholder vote results", "other_event": "8-K other event"}[et]
    e.update({"category": cat, "category_name": CATEGORY_NAMES[cat], "severity": sev, "required_workflow": wf,
              "reason": reason, "immediate_alert": alert, "alert_meaning": l4.REASSESS if alert else None})
    l4.assert_no_orders(e)
    return e


def context_for(ticker: str, events: List[Dict[str, Any]], root: Path = ROOT) -> Dict[str, Any]:
    policy = l4.load_policy(root)
    return {"filing_dates": {e["timestamp"] for e in events if e["event_type"] in FILING_TYPES},
            "dilution_core": _dilution_is_core(l4.thesis(ticker, root)),
            "large_move_pct": policy["market"]["large_move_pct"]}


def classify_all(ticker: str, events: List[Dict[str, Any]], root: Path = ROOT) -> List[Dict[str, Any]]:
    ctx = context_for(ticker, events, root)
    return [classify(e, ctx) for e in events]


def main(argv: Optional[List[str]] = None) -> int:
    import research_event_detector as det
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--as-of")
    ap.add_argument("--since", help="replay window start (dry run)")
    args = ap.parse_args(argv)
    import research_priority as prio
    res = det.detect(args.ticker, as_of=args.as_of, save_state=False, since_override=args.since)
    events = prio.prioritize_events(res["ticker"], classify_all(res["ticker"], res["events"]), as_of=args.as_of)
    print("| Date | Event | Cat | Severity | Priority | Workflow | Reason |")
    print("|---|---|---|---|---|---|---|")
    for e in events:
        print(f"| {e['timestamp']} | {e['event_type']} | {e['category']} | {e['severity']} | {e['priority']} | "
              f"{e['required_workflow'][:60]} | {e['reason'][:110]} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
