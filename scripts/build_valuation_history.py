#!/usr/bin/env python3
"""Historical valuation multiples without look-ahead, plus the fundamental-price timeline.

For every valuation date (month-ends, and the session before / after each earnings
release) the script uses only financial facts filed on or before that date: the
fundamental history is rebuilt from SEC companyfacts with an as_of cutoff at each
distinct 10-Q / 10-K filing date (build_fundamental_history.build_history), and each
valuation date takes the latest build whose filing date is <= the valuation date.

Per date: price, shares (latest cover-page shares outstanding filed by then, else the
latest weighted diluted shares), market cap, cash + short-term investments, debt,
EV = market cap + debt - cash/investments (leases excluded), TTM revenue / operating
income / net income / FCF (sum of the last four reported quarters), and
EV/Sales, EV/EBIT, P/E, P/FCF (null when the denominator is <= 0: "n/m").

Outputs
  valuation/historical-multiples.csv     one row per valuation date
  valuation/historical-percentiles.json  current multiple vs 1Y / 3Y / since-listing
                                         distributions of month-end values (flagged if thin)
  market/fundamental-price-timeline.csv  per earnings release: price before / after,
                                         benchmark-adjusted move, fundamentals, EV/Sales,
                                         and the research state recorded at that date

Usage: python3 scripts/build_valuation_history.py PL [--listing-date 2021-12-08]
(offline: needs raw/companyfacts.json, market/prices.csv, market/events.csv)
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_fundamental_history as bfh  # noqa: E402
import price_reaction  # noqa: E402

MULTIPLES = ("ev_sales", "ev_ebit", "pe", "p_fcf")
MIN_OBS = {"1y": 9, "3y": 24, "since_listing": 12}
HEADER = ["date", "kind", "price", "price_date", "shares_m", "share_basis", "market_cap_m", "cash_m", "debt_m",
          "ev_m", "revenue_ttm_m", "ebit_ttm_m", "net_income_ttm_m", "fcf_ttm_m", "ev_sales", "ev_ebit", "pe",
          "p_fcf", "fundamentals_period", "fundamentals_filed", "note"]


def filing_dates(facts: Dict[str, Any]) -> List[str]:
    dates = set()
    for node in facts.get("facts", {}).get("us-gaap", {}).values():
        for entries in node.get("units", {}).values():
            for x in entries:
                if x.get("form") in ("10-K", "10-Q", "10-K/A", "10-Q/A"):
                    dates.add(x["filed"])
    return sorted(dates)


def cover_shares(facts: Dict[str, Any]) -> List[Tuple[str, float, str]]:
    """(filed, shares, end) from dei:EntityCommonStockSharesOutstanding in periodic filings."""
    node = facts.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding", {})
    out = []
    for x in node.get("units", {}).get("shares", []):
        if x.get("form") in ("10-K", "10-Q", "10-K/A", "10-Q/A"):
            out.append((x["filed"], x["val"] / 1e6, x["end"]))
    # multiple share classes on one cover page are summed per filing
    agg: Dict[Tuple[str, str], float] = {}
    for filed, v, end in out:
        agg[(filed, end)] = agg.get((filed, end), 0.0) + v
    return sorted((f, v, e) for (f, e), v in agg.items())


def _ttm(qs: List[Dict[str, Any]], key: str) -> Optional[float]:
    vals = [bfh._v(q["metrics"], key) for q in qs[-4:]]
    if len(vals) < 4 or any(v is None for v in vals):
        return None
    ends = [date.fromisoformat(q["period_end"]) for q in qs[-4:]]
    if (ends[-1] - ends[0]).days > 300:  # four quarters must be consecutive
        return None
    return sum(vals)


def snapshot_at(builds: List[Tuple[str, Dict[str, Any]]], shares: List[Tuple[str, float, str]],
                d: str) -> Optional[Dict[str, Any]]:
    """Fundamentals public on date d (no look-ahead)."""
    keys = [b[0] for b in builds]
    i = bisect.bisect_right(keys, d) - 1
    if i < 0:
        return None
    filed, hist = builds[i]
    qs = [q for q in hist["quarters"] if bfh._v(q["metrics"], "revenue") is not None]
    if not qs:
        return None
    last = qs[-1]["metrics"]
    sh = [s for s in shares if s[0] <= d]
    if sh:
        share_m, basis = sh[-1][1], f"cover-page shares outstanding as of {sh[-1][2]} (filed {sh[-1][0]})"
    else:
        share_m = next((bfh._v(q["metrics"], "diluted_shares") for q in reversed(qs)
                        if bfh._v(q["metrics"], "diluted_shares")), None)
        basis = "latest weighted diluted shares (no cover-page count filed yet)"
    return {"filed": filed, "period": qs[-1]["period"], "period_end": qs[-1]["period_end"],
            "shares_m": share_m, "share_basis": basis,
            "cash_m": bfh._v(last, "cash_and_investments"), "debt_m": bfh._v(last, "debt"),
            "revenue_ttm": _ttm(qs, "revenue"), "ebit_ttm": _ttm(qs, "operating_income"),
            "ni_ttm": _ttm(qs, "net_income"), "fcf_ttm": _ttm(qs, "fcf")}


def _ratio(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den is None or den <= 0 or num <= 0:
        return None
    return round(num / den, 2)


def row_for(d: str, kind: str, price: Tuple[str, float], f: Dict[str, Any]) -> Dict[str, Any]:
    mcap = price[1] * f["shares_m"] if f.get("shares_m") else None
    debt = f["debt_m"] if f["debt_m"] is not None else 0.0
    note = [] if f["debt_m"] is not None else ["debt not reported in XBRL for this period; treated as 0"]
    ev = mcap + debt - f["cash_m"] if mcap is not None and f["cash_m"] is not None else None
    return {"date": d, "kind": kind, "price": price[1], "price_date": price[0],
            "shares_m": round(f["shares_m"], 3) if f.get("shares_m") else None, "share_basis": f["share_basis"],
            "market_cap_m": round(mcap, 1) if mcap else None, "cash_m": f["cash_m"], "debt_m": f["debt_m"],
            "ev_m": round(ev, 1) if ev is not None else None,
            "revenue_ttm_m": f["revenue_ttm"], "ebit_ttm_m": f["ebit_ttm"], "net_income_ttm_m": f["ni_ttm"],
            "fcf_ttm_m": f["fcf_ttm"], "ev_sales": _ratio(ev, f["revenue_ttm"]), "ev_ebit": _ratio(ev, f["ebit_ttm"]),
            "pe": _ratio(mcap, f["ni_ttm"]), "p_fcf": _ratio(mcap, f["fcf_ttm"]),
            "fundamentals_period": f["period"], "fundamentals_filed": f["filed"], "note": "; ".join(note)}


def month_ends(prices: List[Dict[str, Any]], start: str) -> List[str]:
    by_month: Dict[str, str] = {}
    for p in prices:
        if p["date"] >= start:
            by_month[p["date"][:7]] = p["date"]
    return sorted(by_month.values())


def percentile_rank(values: List[float], current: float) -> float:
    return round(sum(v <= current for v in values) / len(values) * 100, 1)


def percentiles(rows: List[Dict[str, Any]], as_of_row: Dict[str, Any], listing: str) -> Dict[str, Any]:
    monthly = [r for r in rows if r["kind"] == "month_end"]
    end = as_of_row["date"]
    out = {}
    for mult in MULTIPLES:
        cur = as_of_row.get(mult)
        res: Dict[str, Any] = {"current": cur, "as_of": end}
        for label, years in (("1y", 1), ("3y", 3), ("since_listing", None)):
            start = listing if years is None else (date.fromisoformat(end) - timedelta(days=365 * years)).isoformat()
            vals = [r[mult] for r in monthly if start <= r["date"] <= end and r.get(mult) is not None]
            if cur is None:
                res[label] = None
                res[f"{label}_note"] = "current multiple not meaningful (denominator <= 0)"
            elif len(vals) < MIN_OBS[label]:
                res[label] = None
                res[f"{label}_note"] = f"insufficient data ({len(vals)} month-end observations)"
            else:
                res[label] = percentile_rank(vals, cur)
                res[f"{label}_range"] = [min(vals), max(vals)]
                res[f"{label}_n"] = len(vals)
        out[mult] = res
    return out


def _price_on_or_before(prices: List[Dict[str, Any]], d: str) -> Optional[Tuple[str, float]]:
    dates = [p["date"] for p in prices]
    i = bisect.bisect_right(dates, d) - 1
    return (prices[i]["date"], prices[i]["close"]) if i >= 0 else None


def research_state_at(base: Path, d: str) -> str:
    """Thesis / action recorded on or before d; never invented for earlier dates."""
    snaps = sorted((base / "snapshots").glob("*.json")) if (base / "snapshots").exists() else []
    cand = [json.loads(p.read_text()) for p in snaps if p.stem <= d]
    if cand:
        s = cand[-1]
        if s.get("retrospective"):
            return f"retrospective snapshot {s['as_of']} (no recommendation at the time)"
        counts: Dict[str, int] = {}
        for c in (s.get("thesis") or {}).values():
            counts[c["status"]] = counts.get(c["status"], 0) + 1
        return f"{s.get('action')} ({s['as_of']}; " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ")"
    hist = json.loads((base / "thesis/history.json").read_text()) if (base / "thesis/history.json").exists() else []
    cand = [h for h in hist if str(h.get("as_of")) <= d]
    if cand:
        return f"{cand[-1].get('action')} ({cand[-1]['as_of']})"
    return "no research coverage at this date"


TIMELINE_HEADER = ["earnings_date", "timing", "period_reported", "price_before", "price_before_date", "price_after",
                   "price_after_date", "return_1d_pct", "abnormal_1d_pct", "abnormal_20d_pct", "revenue_q_m",
                   "revenue_yoy_pct", "gross_margin_pct", "operating_margin_pct", "rpo_m", "rpo_yoy_pct",
                   "fcf_ttm_m", "ev_sales_before", "ev_sales_after", "research_state", "source"]


def build(ticker: str, root: Path = ROOT, listing_date: Optional[str] = None,
          benchmark: str = "SPY") -> Dict[str, Any]:
    t = ticker.upper()
    base = root / "research" / t
    facts = json.loads((base / "raw/companyfacts.json").read_text())
    prices = price_reaction.load_prices(base / "market/prices.csv")
    overrides_p = base / "financials/tag-overrides.json"
    overrides = json.loads(overrides_p.read_text()) if overrides_p.exists() else {}
    fdates = filing_dates(facts)
    builds = [(fd, bfh.build_history(facts, as_of=fd, n_years=6, n_quarters=8, overrides=overrides)) for fd in fdates]
    builds = [(fd, h) for fd, h in builds if h["quarters"]]
    shares = cover_shares(facts)
    first_fund = builds[0][0] if builds else None
    listing = max(listing_date or prices[0]["date"], first_fund or "")
    rows: List[Dict[str, Any]] = []
    for d in month_ends(prices, listing):
        f = snapshot_at(builds, shares, d)
        p = _price_on_or_before(prices, d)
        if f and p:
            rows.append(row_for(d, "month_end", p, f))
    events = []
    ev_path = base / "market/events.csv"
    if ev_path.exists():
        with ev_path.open(newline="", encoding="utf-8") as fh:
            events = [e for e in csv.DictReader(fh) if "earnings" in e.get("event_type", "")]
    bench_path = price_reaction.benchmark_path(benchmark, root)
    bench = price_reaction.load_prices(bench_path) if bench_path.exists() else []
    timeline = []
    for e in sorted(events, key=lambda e: e["event_date"]):
        r = price_reaction.event_reaction(prices, e["event_date"], after_close=e.get("timing", "").startswith("amc"),
                                          benchmark=bench or None)
        if not r:
            continue
        before_d = prices[[p["date"] for p in prices].index(r["t0"]) - 1]["date"]
        f_before = snapshot_at(builds, shares, before_d)
        f_after = snapshot_at(builds, shares, r["t0"])
        if f_before:
            rows.append(row_for(before_d, "pre_earnings", _price_on_or_before(prices, before_d), f_before))
        if f_after:
            rows.append(row_for(r["t0"], "post_earnings", _price_on_or_before(prices, r["t0"]), f_after))
        # Fundamentals of the quarter the release reports: from the first periodic filing that
        # contains it (the release itself is public at t0; XBRL for a Q4 arrives with the 10-K).
        label = " ".join(e.get("description", "").split(" ")[:2])
        q = None
        for fd, h in builds:
            if fd < e["event_date"]:
                continue
            q = next((x for x in h["quarters"] if x["period"] == label), None)
            if q:
                break
        if q is None:
            hist_at = next((h for fd, h in reversed(builds) if fd <= r["t0"]), None)
            qs = [x for x in (hist_at or {}).get("quarters", []) if bfh._v(x["metrics"], "revenue") is not None]
            q = qs[-1] if qs else None
        m = q["metrics"] if q else {}
        rb = row_for(before_d, "x", _price_on_or_before(prices, before_d), f_before) if f_before else {}
        ra = row_for(r["t0"], "x", _price_on_or_before(prices, r["t0"]), f_after) if f_after else {}
        timeline.append({
            "earnings_date": e["event_date"], "timing": e.get("timing", ""),
            "period_reported": q["period"] if q else "", "price_before": rb.get("price"),
            "price_before_date": before_d, "price_after": ra.get("price"), "price_after_date": r["t0"],
            "return_1d_pct": r.get("day_return_pct"), "abnormal_1d_pct": r.get("abnormal_1d_pct"),
            "abnormal_20d_pct": r.get("abnormal_20d_pct"),
            "revenue_q_m": bfh._v(m, "revenue"), "revenue_yoy_pct": _r(bfh._v(m, "revenue_yoy_pct")),
            "gross_margin_pct": _r(bfh._v(m, "gross_margin_pct")),
            "operating_margin_pct": _r(bfh._v(m, "operating_margin_pct")), "rpo_m": bfh._v(m, "rpo"),
            "rpo_yoy_pct": _r(bfh._v(m, "rpo_yoy_pct")), "fcf_ttm_m": _r(ra.get("fcf_ttm_m")),
            "ev_sales_before": rb.get("ev_sales"), "ev_sales_after": ra.get("ev_sales"),
            "research_state": research_state_at(base, r["t0"]), "source": e.get("source", "")})
    # latest close row for "current" percentiles
    if prices and builds:
        f = snapshot_at(builds, shares, prices[-1]["date"])
        if f:
            rows.append(row_for(prices[-1]["date"], "latest_close", (prices[-1]["date"], prices[-1]["close"]), f))
    rows = sorted({(r["date"], r["kind"]): r for r in rows}.values(), key=lambda r: (r["date"], r["kind"]))
    vdir = base / "valuation"
    vdir.mkdir(parents=True, exist_ok=True)
    with (vdir / "historical-multiples.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    cur = [r for r in rows if r["kind"] == "latest_close"]
    pct = {"ticker": t, "listing_date_used": listing, "method": "percentile rank of the current multiple within "
           "month-end values (no look-ahead fundamentals); EV excludes leases",
           "percentiles": percentiles(rows, cur[-1], listing) if cur else {}}
    (vdir / "historical-percentiles.json").write_text(json.dumps(pct, indent=2) + "\n", encoding="utf-8")
    with (base / "market/fundamental-price-timeline.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=TIMELINE_HEADER)
        w.writeheader()
        w.writerows(timeline)
    return {"rows": len(rows), "month_ends": len([r for r in rows if r["kind"] == "month_end"]),
            "first": rows[0]["date"] if rows else None, "timeline_events": len(timeline),
            "percentiles": {k: {w: v.get(w) for w in ("current", "1y", "3y", "since_listing")}
                            for k, v in pct["percentiles"].items()}}


def _r(v: Optional[float]) -> Optional[float]:
    return None if v is None else round(v, 2)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--listing-date", help="first date to value (e.g. de-SPAC close); default first price/filing")
    ap.add_argument("--benchmark", default="SPY")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args(argv)
    print(json.dumps(build(args.ticker, args.root, args.listing_date, args.benchmark), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
