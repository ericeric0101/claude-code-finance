#!/usr/bin/env python3
"""Research priority engine (Level 4): transparent rules, no ML, every level explained.

Event level (HIGH / MEDIUM / LOW)
  HIGH    new earnings filing (10-Q / 10-K / 8-K 2.02), thesis invalidation triggered,
          guidance cut, promise missed (not a spending-plan deviation), major dilution
          (capital raise when dilution is a high-importance component), expectation gap
          materially changed, multiple monitoring rules triggered for the ticker
  MEDIUM  major contract, product launch, large market move, valuation percentile moved
          materially, management wording / timing change, other targeted updates
  LOW     routine insider filings, price move without fundamental evidence, informational
Modifiers (each one is listed in priority_reasons):
  thesis importance   MEDIUM → HIGH when the event maps to a high-importance thesis component
                      AND its evidence quality is HIGH
  evidence quality    LOW evidence lowers one level (confidence, not truth)
  last review age     B / C events → one level up when the last review is older than
                      full_review_days x stale_days_multiplier_high
  research confidence low valuation confidence is listed as a reason (tie-break only)
Ticker level = highest open event level, raised to HIGH when stale_research reports a new
filing the state has not absorbed; LOW with "no meaningful state change" when nothing is
open. A watchlist priority_override is applied last and labelled as an analyst override.
Cross-company order: level, number of HIGH items, high-importance links, review age, low
research confidence. Raw multiples are never compared across sectors.

Outputs: research/queue/priorities.json, research/queue/priority-history.csv
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import level4_common as l4  # noqa: E402

LEVELS = ("LOW", "MEDIUM", "HIGH")
COMPONENT_HINTS = {  # event / rule tokens → thesis component name tokens
    "dilution": ("dilution", "per_share"), "capital_raise": ("dilution", "per_share", "liquidity"),
    "capex": ("margin", "cash", "constellation"), "rpo": ("backlog", "visibility"), "backlog": ("backlog", "visibility"),
    "revenue": ("revenue", "growth"), "margin": ("margin",), "receivables": ("earnings_quality", "working_capital"),
    "contract": ("demand", "backlog", "diversification", "defense"), "launch": ("constellation", "execution", "product", "launch"),
    "management": ("management",), "services": ("services",), "fcf": ("cash",), "cash": ("cash", "liquidity"),
}
EVENT_TOKENS = {"major_contract": "contract", "product_launch": "launch", "capital_raise": "capital_raise",
                "management_change": "management", "promise_delayed": "launch"}


def _up(level: str) -> str:
    return LEVELS[min(LEVELS.index(level) + 1, 2)]


def _down(level: str) -> str:
    return LEVELS[max(LEVELS.index(level) - 1, 0)]


def linked_components(event: Dict[str, Any], thesis: Dict[str, Any]) -> List[str]:
    comps = thesis.get("components") or {}
    d = event.get("details") or {}
    if d.get("thesis_component") and d["thesis_component"] in comps:
        return [d["thesis_component"]]
    text = " ".join(str(x) for x in (event["event_type"], d.get("rule"), d.get("metric"), d.get("promise_id"),
                                     EVENT_TOKENS.get(event["event_type"], ""))).lower()
    hits = []
    for tok, comp_tokens in COMPONENT_HINTS.items():
        if re.search(rf"{tok}", text):
            hits += [n for n in comps if any(ct in n for ct in comp_tokens)]
    return sorted(set(hits))


def event_priority(e: Dict[str, Any], thesis: Dict[str, Any], review_age: Optional[int], limits: Dict[str, Any],
                   policy: Dict[str, Any], n_triggers: int) -> Dict[str, Any]:
    et, cat, d = e["event_type"], e.get("category"), e.get("details") or {}
    reasons: List[str] = []
    if cat == "A":
        level = "HIGH"
        reasons.append({"sec_10q": "new 10-Q", "sec_10k": "new 10-K", "earnings_release": "new earnings release",
                        "thesis_invalidation": "thesis invalidation triggered", "guidance_update": "guidance cut"}
                       .get(et, e.get("reason", "full update required")))
    elif et == "promise_missed" and not d.get("spending_plan"):
        level, reasons = "HIGH", ["promise missed"]
    elif et == "capital_raise" and e.get("severity") == "high":
        level, reasons = "HIGH", ["capital raise with dilution as a high-importance thesis component (major dilution risk)"]
    elif et == "expectation_gap_change":
        level, reasons = "HIGH", [f"expectation gap materially {d.get('direction')}"]
    elif et in ("monitoring_trigger", "standing_trigger") and n_triggers >= 2:
        level, reasons = "HIGH", [f"multiple monitoring rules triggered ({n_triggers} distinct conditions)"]
    elif cat == "B":
        level = "LOW" if e.get("severity") == "low" else "MEDIUM"
        reasons.append({"major_contract": "major contract", "product_launch": "product launch",
                        "valuation_rerating": "valuation percentile changed materially",
                        "management_wording_change": "management wording / timing changed",
                        "promise_missed": "spending-plan deviation"}.get(et, e.get("reason", "targeted update")))
    elif cat == "C":
        level = "MEDIUM" if e.get("severity") == "medium" else "LOW"
        reasons.append("large market move without a new filing" if level == "MEDIUM"
                       else "price move without fundamental evidence")
    else:
        level = "LOW"
        reasons.append("routine insider transaction" if et == "insider_filings" else "informational")
    links = linked_components(e, thesis)
    comps = thesis.get("components") or {}
    high_links = [c for c in links if (comps.get(c) or {}).get("importance") == "high"]
    if high_links:
        reasons.append(f"maps to high-importance thesis component(s): {', '.join(high_links)}")
        if level == "MEDIUM" and e.get("evidence_quality") == "HIGH" and cat in ("A", "B"):
            level = "HIGH"
            reasons.append("raised: high-importance component and HIGH evidence quality")
    if e.get("evidence_quality") == "LOW" and level != "LOW" and cat != "A":
        level = _down(level)
        reasons.append("lowered: LOW evidence quality (lower confidence, not false)")
    stale_after = limits.get("full_review_days", 100) * policy["priority"]["stale_days_multiplier_high"]
    if review_age is not None and review_age > stale_after and cat in ("B", "C") and level != "HIGH":
        level = _up(level)
        reasons.append(f"raised: last review {review_age} days ago (> {stale_after:.0f})")
    if (thesis.get("valuation_confidence") or "").lower() == "low" and cat in ("A", "B"):
        reasons.append("current research confidence is low (tie-break)")
    return {"priority": level, "priority_reasons": reasons, "linked_components": links,
            "high_importance_links": high_links}


def prioritize_events(ticker: str, events: List[Dict[str, Any]], root: Path = ROOT,
                      as_of: Optional[str] = None) -> List[Dict[str, Any]]:
    policy = l4.load_policy(root)
    th = l4.thesis(ticker, root)
    limits = l4.staleness_limits(policy, th.get("research_role") or l4.watch_entry(ticker, root).get("research_role"))
    age = l4.days_between(l4.latest_review_date(ticker, root), l4.today(as_of))
    n_trig = len({(e.get("details") or {}).get("condition") or e["event_id"] for e in events
                  if e["event_type"] in ("monitoring_trigger", "thesis_invalidation", "standing_trigger")})
    out = []
    for e in events:
        x = dict(e)
        x.update(event_priority(e, th, age, limits, policy, n_trig))
        out.append(x)
    return out


def ticker_priority(ticker: str, open_items: List[Dict[str, Any]], stale: Optional[Dict[str, Any]],
                    root: Path = ROOT, as_of: Optional[str] = None) -> Dict[str, Any]:
    th = l4.thesis(ticker, root)
    entry = l4.watch_entry(ticker, root)
    reasons: List[str] = []
    level = "LOW"
    if open_items:
        level = max((i.get("priority", "LOW") for i in open_items), key=LEVELS.index)
        top = [i for i in open_items if i.get("priority") == level]
        for i in top:
            r = f"{i['event_type']}: {(i.get('priority_reasons') or [i.get('reason', '')])[0]}"
            if r not in reasons:
                reasons.append(r)
        reasons = reasons[:4]
    if stale and stale.get("new_filing_unprocessed"):
        if level != "HIGH":
            reasons.append("raised: new filing not yet absorbed into state (stale research)")
        level = "HIGH"
    elif stale and stale.get("severity") in ("HIGH", "MEDIUM") and level == "LOW":
        level = "MEDIUM"
        reasons.append("raised: research is stale — " + "; ".join(stale.get("reasons", [])[:2]))
    if not reasons:
        reasons.append("no meaningful state change")
    override = entry.get("priority_override")
    if override and str(override).upper() in LEVELS:
        reasons.append(f"analyst override {level} → {str(override).upper()} (config/watchlist.yaml)")
        level = str(override).upper()
    n_high = sum(i.get("priority") == "HIGH" for i in open_items)
    high_links = sorted({c for i in open_items for c in i.get("high_importance_links", [])})
    return {"ticker": ticker, "priority": level, "reasons": reasons, "open_items": len(open_items),
            "high_items": n_high, "high_importance_links": high_links,
            "days_since_review": stale.get("days_since_review") if stale else None,
            "research_confidence": th.get("valuation_confidence"),
            "immediate_alerts": [i["event_id"] for i in open_items if i.get("immediate_alert")]}


def rank(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def key(r: Dict[str, Any]):
        return (-LEVELS.index(r["priority"]), -r["high_items"], -len(r["high_importance_links"]),
                -(r.get("days_since_review") or 0), 0 if (r.get("research_confidence") or "") == "low" else 1, r["ticker"])
    out = sorted(rows, key=key)
    for n, r in enumerate(out, 1):
        r["rank"] = n
    return out


def write(rows: List[Dict[str, Any]], root: Path = ROOT, as_of: Optional[str] = None) -> Dict[str, Any]:
    as_of = l4.today(as_of)
    doc = {"as_of": as_of, "generated_at": l4.now_iso(), "method": "transparent rules (scripts/research_priority.py)",
           "note": "Priority = what to research first. It is not a rating and never a buy / sell instruction.",
           "tickers": rows}
    l4.write_json(root / "research/queue/priorities.json", doc)
    path = root / "research/queue/priority-history.csv"
    hist = [r for r in l4.read_csv(path) if r.get("date") != as_of]
    hist += [{"date": as_of, "ticker": r["ticker"], "priority": r["priority"], "rank": r["rank"],
              "reasons": " | ".join(r["reasons"])[:400]} for r in rows]
    l4.write_csv(path, ["date", "ticker", "priority", "rank", "reasons"], sorted(hist, key=lambda r: (r["date"], int(r["rank"]))))
    return doc


def previous_priorities(root: Path = ROOT, before: Optional[str] = None) -> Dict[str, str]:
    hist = l4.read_csv(root / "research/queue/priority-history.csv")
    dates = sorted({r["date"] for r in hist if not before or r["date"] < before})
    if not dates:
        return {}
    return {r["ticker"]: r["priority"] for r in hist if r["date"] == dates[-1]}


def main(argv: Optional[List[str]] = None) -> int:
    import research_command_center as cc
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--as-of")
    args = ap.parse_args(argv)
    doc = cc.prioritize(as_of=args.as_of)
    for r in doc["tickers"]:
        print(f"{r['rank']}. {r['ticker']} {r['priority']}: {'; '.join(r['reasons'])[:150]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
