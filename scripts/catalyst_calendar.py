#!/usr/bin/env python3
"""Catalyst calendar (Level 4): research/calendar/upcoming.csv.

Sources (all local state; no guessing of exact dates):
  1. Company-announced dates in research/<T>/config/catalysts.yaml       → exact, high confidence
  2. Next earnings release from the company's own cadence (quarter end + median release
     lag of recent 8-K Item 2.02 dates)                                   → month, low confidence
  3. SEC filing deadline for the next 10-Q / 10-K (upper bound: 45 / 90 days after period end)
                                                                          → deadline, medium
  4. thesis/current.yaml next_catalysts: explicit dates or date ranges in the text are used;
     otherwise the item is listed as "unscheduled"
  5. Pending timing promises (management/promises.json milestone targets) → quarter / half / year
  6. Annual meeting: last DEF 14A + one year                              → month, low confidence

Unknown dates are never turned into exact days: expected_date is a day only for announced
dates and regulatory deadlines; otherwise a month ("2026-12"), quarter ("Q4 2026") or
"unscheduled", with date_precision and confidence.
Status: upcoming / past_due (window ended, no completion evidence) / completed.

Usage: python3 scripts/catalyst_calendar.py [--as-of YYYY-MM-DD] [--tickers PL RKLB]
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import level4_common as l4  # noqa: E402

HEADER = ["ticker", "event", "expected_date", "date_precision", "window_start", "window_end", "source",
          "confidence", "importance", "status", "notes"]


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


def _month_end(y: int, m: int) -> date:
    return (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))


def _row(t: str, event: str, expected: str, precision: str, ws: Optional[str], we: Optional[str], source: str,
         conf: str, imp: str, notes: str = "") -> Dict[str, Any]:
    return {"ticker": t, "event": event, "expected_date": expected, "date_precision": precision, "window_start": ws or "",
            "window_end": we or "", "source": source, "confidence": conf, "importance": imp, "status": "upcoming",
            "notes": notes}


def earnings_rows(t: str, base: Path, as_of: str) -> List[Dict[str, Any]]:
    hist = l4.read_json(base / "financials/history.json", {}) or {}
    qs = hist.get("quarters") or []
    if not qs:
        return []
    ends = sorted(q["period_end"] for q in qs)
    fy_ends = sorted(hist.get("fiscal_year_ends") or [])
    rel = sorted(r["event_date"] for r in l4.read_csv(base / "market/events.csv") if "2.02" in r.get("event_type", ""))
    lags = []
    all_ends = sorted(set(ends + fy_ends))
    for r in rel[-8:]:
        prior = [e for e in all_ends if e < r]
        if prior:
            lag = l4.days_between(prior[-1], r)
            if lag is not None and 10 <= lag <= 100:
                lags.append(lag)
    last_end = _d(max(all_ends))
    nxt = _month_end(last_end.year + (last_end.month + 3 > 12), (last_end.month + 3 - 1) % 12 + 1)
    # skip forward over quarters whose release date has already passed
    out = []
    for _ in range(2):
        is_fy = bool(fy_ends) and (nxt.month, nxt.day) == (_d(fy_ends[-1]).month, _d(fy_ends[-1]).day) or (
            bool(fy_ends) and nxt.month == _d(fy_ends[-1]).month)
        lag = int(statistics.median(lags)) if lags else (60 if is_fy else 40)
        est = nxt + timedelta(days=lag)
        ws, we = est - timedelta(days=10), est + timedelta(days=10)
        kind = "fiscal-year results (10-K)" if is_fy else "quarterly results (10-Q)"
        if we.isoformat() >= as_of:
            out.append(_row(t, f"Earnings release: {kind}, fiscal period ending ~{nxt:%Y-%m}", est.strftime("%Y-%m"),
                            "month (approximate)", ws.isoformat(), we.isoformat(),
                            f"Calculation: period end + median release lag {lag}d of {len(lags)} recent 8-K 2.02 releases",
                            "low", "high", "not an announced date"))
            deadline = nxt + timedelta(days=90 if is_fy else 45)
            out.append(_row(t, f"SEC {('10-K' if is_fy else '10-Q')} filing deadline (approx. upper bound), fiscal period ending ~{nxt:%Y-%m}",
                            deadline.isoformat(), "deadline (upper bound)", nxt.isoformat(), deadline.isoformat(),
                            "SEC rule: 10-Q within 40/45 days, 10-K within 60/75/90 days of period end (filer status not checked)",
                            "medium", "high", "upper bound; large accelerated filers file earlier"))
            break
        nxt = _month_end(nxt.year + (nxt.month + 3 > 12), (nxt.month + 3 - 1) % 12 + 1)
    return out


_ISO = re.compile(r"(20\d\d-\d\d-\d\d)")


PAST = re.compile(r"(?i)(launched|filed|announced|issued|reported|as of|since|dated)\s*$")


def scheduled_dates(text: str) -> List[str]:
    """Dates that schedule the catalyst; citation dates in parentheses and past-tense facts are ignored."""
    body = re.sub(r"\([^)]*\)", " ", text)
    out = []
    for m in _ISO.finditer(body):
        if PAST.search(body[max(0, m.start() - 25):m.start()]):
            continue
        out.append(m.group(1))
    return out


def thesis_rows(t: str, base: Path) -> List[Dict[str, Any]]:
    th = l4.read_yaml(base / "thesis/current.yaml", {}) or {}
    out = []
    for c in th.get("next_catalysts") or []:
        text = str(c)
        dates = scheduled_dates(text)
        if re.search(r"(?i)results|10-q|10-k|earnings release", text) and not dates:
            continue  # covered by the cadence-based earnings row
        if dates:
            ws, we = min(dates), max(dates)
            out.append(_row(t, text[:160], we, "date (stated)" if ws == we else "window end (stated)", ws, we,
                            "thesis/current.yaml next_catalysts (cites its source)", "high", "medium"))
        else:
            out.append(_row(t, text[:160], "unscheduled", "unknown", None, None,
                            "thesis/current.yaml next_catalysts", "low", "medium", "no date disclosed"))
    return out


def promise_rows(t: str, base: Path) -> List[Dict[str, Any]]:
    out = []
    for p in l4.read_json(base / "management/promises.json", []) or []:
        if p.get("status") != "pending" or "milestone" not in p.get("promise_id", ""):
            continue
        claim = next((c for c in l4.read_json(base / "management/claims.json", []) or []
                      if p["promise_id"].endswith(c.get("source_date", "")) and c.get("timing") == p.get("target_date")), {})
        we = claim.get("timing_end")
        prec = claim.get("timing_precision") or "quarter"
        ws = None
        if we:
            months = {"quarter": 3, "half": 6, "year": 12}.get(prec, 3)
            e = _d(we)
            sm = e.month - months + 1
            ws = date(e.year + (sm <= 0) * -1, (sm - 1) % 12 + 1, 1).isoformat()
        out.append(_row(t, f"Company target: {p['expected_result']}", p.get("target_date") or "unscheduled", prec, ws, we,
                        p.get("source", ""), "medium", "high", "management timing promise; not a confirmed date"))
    return out


def meeting_rows(t: str, base: Path) -> List[Dict[str, Any]]:
    sub = l4.read_json(base / "raw/submissions.json", {}) or {}
    r = (sub.get("filings") or {}).get("recent") or {}
    proxies = sorted(d for f, d in zip(r.get("form") or [], r.get("filingDate") or []) if f == "DEF 14A")
    if not proxies:
        return []
    last = _d(proxies[-1])
    nxt = date(last.year + 1, last.month, 1)
    return [_row(t, "Annual meeting / proxy statement (DEF 14A)", nxt.strftime("%Y-%m"), "month (approximate)",
                 nxt.isoformat(), _month_end(nxt.year, nxt.month).isoformat(),
                 f"Calculation: last DEF 14A filed {proxies[-1]} + 1 year", "low", "low")]


def manual_rows(t: str, base: Path) -> List[Dict[str, Any]]:
    out = []
    for c in (l4.read_yaml(base / "config/catalysts.yaml", {}) or {}).get("catalysts") or []:
        exp = str(c.get("expected_date", "unscheduled"))
        out.append(_row(t, c.get("event", ""), exp, c.get("precision", "date (announced)"), c.get("window_start", exp),
                        c.get("window_end", exp), c.get("source", ""), c.get("confidence", "high"),
                        c.get("importance", "high"), c.get("notes", "")))
    return out


def build(tickers: Optional[List[str]] = None, root: Path = ROOT, as_of: Optional[str] = None,
          write: bool = True) -> List[Dict[str, Any]]:
    as_of = l4.today(as_of)
    tickers = tickers or [e["ticker"] for e in l4.load_watchlist(root)]
    rows: List[Dict[str, Any]] = []
    for t in tickers:
        base = l4.company_dir(t, root)
        rel = sorted(r["event_date"] for r in l4.read_csv(base / "market/events.csv") if "2.02" in r.get("event_type", ""))
        trows = manual_rows(t, base) + earnings_rows(t, base, as_of) + thesis_rows(t, base) + \
            promise_rows(t, base) + meeting_rows(t, base)
        for r in trows:
            if r["window_end"] and r["window_end"] < as_of:
                done = "Earnings" in r["event"] and any(x >= r["window_start"] for x in rel)
                r["status"] = "completed" if done else "past_due"
        rows += trows
    rows.sort(key=lambda r: (r["window_start"] or "9999", r["ticker"], r["event"]))
    if write:
        l4.write_csv(root / "research/calendar/upcoming.csv", HEADER, rows)
    return rows


def next_catalyst(rows: List[Dict[str, Any]], ticker: str) -> Optional[Dict[str, Any]]:
    cands = [r for r in rows if r["ticker"] == ticker and r["status"] == "upcoming" and r["window_start"]
             and "deadline" not in r["date_precision"]]
    return min(cands, key=lambda r: r["window_start"]) if cands else None


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--as-of")
    ap.add_argument("--tickers", nargs="*")
    args = ap.parse_args(argv)
    for r in build(args.tickers, as_of=args.as_of):
        print(f"{r['ticker']:5s} {r['expected_date']:12s} {r['date_precision']:22s} {r['confidence']:6s} {r['status']:9s} {r['event'][:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
