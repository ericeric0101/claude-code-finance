#!/usr/bin/env python3
"""Stale research detector (Level 4).

Flags, per watchlist company (thresholds in config/research-policy.yaml, per research_role):
  - last review too old (latest change / baseline report or live snapshot)
  - a new 10-Q / 10-K exists that the state has not absorbed (SEC submissions vs the
    filing date recorded in the latest snapshot)
  - valuation price too old (valuation/latest.json price_date vs latest stored close)
  - thesis evidence too old (newest component last_updated)
  - management history too old (newest statement date)
  - next catalyst already past due (research/calendar/upcoming.csv)
Severity: HIGH (new filing not absorbed, or review older than full_review_days x
stale_days_multiplier_high), MEDIUM (review older than full_review_days, catalyst past due,
valuation price far out of date), LOW (minor), none.

Outputs: research/dashboard/stale-research.{json,md}
Usage: python3 scripts/stale_research.py [--as-of YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import level4_common as l4  # noqa: E402

SEV = ("LOW", "MEDIUM", "HIGH")


def _bump(cur: Optional[str], new: str) -> str:
    return new if cur is None or SEV.index(new) > SEV.index(cur) else cur


def latest_periodic_filing(base: Path, as_of: str) -> Optional[Dict[str, str]]:
    sub = l4.read_json(base / "raw/submissions.json", {}) or {}
    r = (sub.get("filings") or {}).get("recent") or {}
    best = None
    for f, d, rep in zip(r.get("form") or [], r.get("filingDate") or [], r.get("reportDate") or []):
        if f.split("/")[0] in ("10-Q", "10-K") and d <= as_of and (best is None or d > best["filed"]):
            best = {"form": f, "filed": d, "report_date": rep}
    return best


def check(ticker: str, root: Path = ROOT, as_of: Optional[str] = None,
          calendar: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    t = ticker.upper()
    as_of = l4.today(as_of)
    base = l4.company_dir(t, root)
    policy = l4.load_policy(root)
    th = l4.thesis(t, root)
    limits = l4.staleness_limits(policy, th.get("research_role") or l4.watch_entry(t, root).get("research_role"))
    mult = policy["priority"]["stale_days_multiplier_high"]
    reasons: List[str] = []
    sev: Optional[str] = None
    review = l4.latest_review_date(t, root)
    full = l4.latest_full_review_date(t, root)
    age = l4.days_between(review, as_of)
    full_age = l4.days_between(full, as_of)
    lim = limits["full_review_days"]
    if full_age is None:
        sev = _bump(sev, "HIGH")
        reasons.append("no research review recorded")
    elif full_age > lim * mult:
        sev = _bump(sev, "HIGH")
        reasons.append(f"last full review {full_age} days ago (> {lim * mult:.0f})")
    elif full_age > lim:
        sev = _bump(sev, "MEDIUM")
        reasons.append(f"last full review {full_age} days ago (> {lim})")
    snaps = [l4.read_json(p, {}) for p in sorted((base / "snapshots").glob("*.json"))]
    live = [s for s in snaps if s and not s.get("retrospective")]
    state_filed = ((live[-1].get("financials") or {}).get("latest_filed")) if live else None
    lf = latest_periodic_filing(base, as_of)
    new_filing = bool(lf and state_filed and lf["filed"] > state_filed)
    if new_filing:
        sev = _bump(sev, "HIGH")
        reasons.append(f"new {lf['form']} filed {lf['filed']} (period {lf['report_date']}) not in state "
                       f"(state built from filing {state_filed})")
    latest = l4.read_json(base / "valuation/latest.json", {}) or {}
    px = l4.prices(t, root)
    price_age = l4.days_between(latest.get("price_date"), px[-1]["date"]) if px and latest.get("price_date") else None
    if price_age is not None and price_age > limits["valuation_price_days"]:
        move = (px[-1]["close"] / float(latest["price"]) - 1) * 100 if latest.get("price") else None
        level = "MEDIUM" if price_age > 3 * limits["valuation_price_days"] else "LOW"
        sev = _bump(sev, level)
        reasons.append(f"valuation price {latest.get('price')} dated {latest.get('price_date')} is {price_age} days "
                       f"older than the latest close {px[-1]['close']} ({px[-1]['date']}"
                       + (f", {move:+.1f}%" if move is not None else "") + ")")
    comps = th.get("components") or {}
    ev_dates = [str(c.get("last_updated")) for c in comps.values() if c.get("last_updated")]
    ev_age = l4.days_between(max(ev_dates), as_of) if ev_dates else None
    if ev_age is not None and ev_age > limits["thesis_evidence_days"]:
        sev = _bump(sev, "MEDIUM")
        reasons.append(f"thesis evidence last updated {ev_age} days ago (> {limits['thesis_evidence_days']})")
    stm = l4.read_json(base / "management/statements.json", []) or []
    m_dates = [str(s.get("date")) for s in stm if s.get("date")]
    m_age = l4.days_between(max(m_dates), as_of) if m_dates else None
    if m_age is not None and m_age > limits["management_update_days"]:
        sev = _bump(sev, "LOW")
        reasons.append(f"newest management statement is {m_age} days old (> {limits['management_update_days']})")
    cal = calendar if calendar is not None else l4.read_csv(root / "research/calendar/upcoming.csv")
    past = [r for r in cal if r.get("ticker") == t and r.get("status") == "past_due"]
    for r in past[:3]:
        sev = _bump(sev, "MEDIUM")
        reasons.append(f"catalyst past due: {r['event'][:80]} (window end {r['window_end']})")
    return {"ticker": t, "as_of": as_of, "stale": sev in ("MEDIUM", "HIGH"), "severity": sev, "reasons": reasons,
            "last_review": review, "last_full_review": full, "days_since_review": age,
            "days_since_full_review": full_age, "new_filing_unprocessed": new_filing,
            "latest_periodic_filing": lf, "state_latest_filed": state_filed, "valuation_price_age_days": price_age,
            "thesis_evidence_age_days": ev_age, "management_age_days": m_age, "limits": limits}


def run(root: Path = ROOT, as_of: Optional[str] = None, write: bool = True,
        tickers: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    as_of = l4.today(as_of)
    tickers = tickers or [e["ticker"] for e in l4.load_watchlist(root)]
    rows = [check(t, root, as_of) for t in tickers]
    if write:
        l4.write_json(root / "research/dashboard/stale-research.json", {"as_of": as_of, "companies": rows})
        L = [f"# Stale research（{as_of}）", "", "| Ticker | Severity | 上次檢視 | 上次完整檢視 | 理由 |", "|---|---|---|---|---|"]
        for r in rows:
            L.append(f"| {r['ticker']} | {r['severity'] or '—'} | {r['last_review']}（{r['days_since_review']} 天） | "
                     f"{r['last_full_review']}（{r['days_since_full_review']} 天） | {'; '.join(r['reasons']) or '無'} |")
        L += ["", "門檻來自 config/research-policy.yaml（依 research_role 調整），不是固定天數。"]
        (root / "research/dashboard/stale-research.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--as-of")
    args = ap.parse_args(argv)
    for r in run(as_of=args.as_of):
        print(f"{r['ticker']}: {r['severity'] or 'not stale'} — {'; '.join(r['reasons']) or 'no staleness'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
