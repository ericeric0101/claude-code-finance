#!/usr/bin/env python3
"""US equity price / volume reaction analyzer (replaces the Taiwan FinMind workflow).

Reads research/<TICKER>/market/prices.csv (date,open,high,low,close,volume,...)
and an events CSV (event_date,event_type,description,source[,timing]), typically SEC
filing dates, earnings dates and 8-K guidance changes. timing "amc" (after market
close) moves t0 to the next session. Output columns are
observations only; the `interpretation` column is left for the analyst.
Volume alone is never read as "smart money".

Optional price refresh (network, uses the finance-skill clients):
  uv run --project .claude/skills/finance-skill/scripts python \
      scripts/price_reaction.py fetch PL          # auto: Alpha Vantage + yfinance backfill
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from research_state import EVENT_REACTION_HEADER, company_dir  # noqa: E402

GAP_FLAG_PCT = 3.0
VOLUME_FLAG_RATIO = 2.0


def load_prices(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r.get("close"):
                continue
            rows.append({"date": r["date"][:10],
                         "open": float(r["open"]) if r.get("open") else None,
                         "close": float(r["close"]),
                         "volume": float(r["volume"]) if r.get("volume") else None})
    return sorted(rows, key=lambda r: r["date"])


def _pct(a: float, b: float) -> float:
    return round((b / a - 1) * 100, 2)


def event_reaction(prices: List[Dict[str, Any]], event_date: str,
                   drift_days: int = 20, after_close: bool = False) -> Optional[Dict[str, Any]]:
    """Reaction on t0 = first session on/after event_date, or the next session when
    the event was released after the close. Returns None if no data."""
    idx = next((i for i, r in enumerate(prices)
                if (r["date"] > event_date if after_close else r["date"] >= event_date)), None)
    if idx is None or idx == 0:
        return None
    t0, prev = prices[idx], prices[idx - 1]
    out: Dict[str, Any] = {"t0": t0["date"], "day_return_pct": _pct(prev["close"], t0["close"])}
    out["gap_pct"] = _pct(prev["close"], t0["open"]) if t0["open"] else None
    window = [r["volume"] for r in prices[max(0, idx - 20):idx] if r["volume"]]
    out["volume_ratio_20d"] = (round(t0["volume"] / statistics.median(window), 2)
                               if window and t0["volume"] else None)
    if idx + 1 < len(prices):
        out["return_m1_p1_pct"] = _pct(prev["close"], prices[idx + 1]["close"])
    end = min(len(prices) - 1, idx + drift_days)
    if idx + 2 <= end:
        out["drift_p2_p20_pct"] = _pct(prices[idx + 1]["close"], prices[end]["close"])
        peak, mdd = t0["close"], 0.0
        for r in prices[idx:end + 1]:
            peak = max(peak, r["close"])
            mdd = min(mdd, r["close"] / peak - 1)
        out["max_drawdown_20d_pct"] = round(mdd * 100, 2)
    flags = []
    if out["gap_pct"] is not None and abs(out["gap_pct"]) >= GAP_FLAG_PCT:
        flags.append(f"gap {out['gap_pct']:+.1f}%")
    if out["volume_ratio_20d"] and out["volume_ratio_20d"] >= VOLUME_FLAG_RATIO:
        flags.append(f"volume {out['volume_ratio_20d']:.1f}x 20-day median")
    out["observation"] = "; ".join(flags) or "no gap/volume anomaly above thresholds"
    return out


def analyze(ticker: str, events_path: Path, root: Path = ROOT) -> List[Dict[str, Any]]:
    base = company_dir(ticker, root)
    prices = load_prices(base / "market/prices.csv")
    rows = []
    with events_path.open(newline="", encoding="utf-8") as fh:
        for ev in csv.DictReader(fh):
            r = event_reaction(prices, ev["event_date"],
                               after_close=ev.get("timing", "").lower().startswith("amc"))
            row = {k: "" for k in EVENT_REACTION_HEADER}
            row.update({k: ev.get(k, "") for k in ("event_date", "event_type", "description", "source")})
            if r is None:
                row["observation"] = "insufficient local price data"
            else:
                row.update({k: ("" if r.get(k) is None else r[k]) for k in EVENT_REACTION_HEADER if k in r})
            row["interpretation"] = ""  # analyst-owned; never auto-filled
            rows.append(row)
    return rows


def _alphavantage_rows(ticker: str, retrieved: str) -> List[List[Any]]:
    import alphavantage
    # outputsize=full is a premium feature; compact returns the latest ~100 sessions.
    series = alphavantage.get_daily_prices(ticker, "compact").get("Time Series (Daily)", {})
    return [[d, v["1. open"], v["2. high"], v["3. low"], v["4. close"], v["5. volume"],
             "Alpha Vantage TIME_SERIES_DAILY compact (tier 3, unadjusted)", retrieved]
            for d, v in series.items()]


def _yfinance_rows(ticker: str, retrieved: str, period: str) -> List[List[Any]]:
    import yfinance
    hist = yfinance.Ticker(ticker).history(period=period, auto_adjust=False)
    return [[idx.strftime("%Y-%m-%d"), round(v["Open"], 4), round(v["High"], 4), round(v["Low"], 4),
             round(v["Close"], 4), int(v["Volume"]),
             "yfinance history auto_adjust=False (tier 4, backfill / cross-check)", retrieved]
            for idx, v in hist.iterrows()]


def fetch(ticker: str, source: str, root: Path = ROOT, period: str = "2y") -> int:
    """Refresh prices.csv (network). auto = Alpha Vantage for recent sessions,
    yfinance only to backfill older dates; higher-tier rows win on overlap and
    previously stored rows for other dates are kept."""
    sys.path.insert(0, str(ROOT / ".claude/skills/finance-skill/scripts"))
    retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")
    primary: List[List[Any]] = []
    backfill: List[List[Any]] = []
    if source in ("auto", "alphavantage"):
        try:
            primary = _alphavantage_rows(ticker, retrieved)
        except Exception as exc:  # report and fall back; never silent
            print(f"Alpha Vantage unavailable ({type(exc).__name__}); using yfinance", file=sys.stderr)
    if source == "yfinance" or (source == "auto"):
        backfill = _yfinance_rows(ticker, retrieved, period)
    if not primary and not backfill:
        print("ERROR: no price rows returned; prices.csv left unchanged", file=sys.stderr)
        return 2
    header = ["date", "open", "high", "low", "close", "volume", "source", "retrieved_at"]
    path = company_dir(ticker, root) / "market/prices.csv"
    # A row for today's US session before the close is an intraday snapshot, not a
    # completed daily bar: keep it out of prices.csv and store it as latest-quote.json.
    now_et = datetime.now(ZoneInfo("America/New_York"))
    today = now_et.strftime("%Y-%m-%d")
    session_open = now_et.time() < time(16, 15) and now_et.weekday() < 5
    intraday = [r for r in primary + backfill if r[0] == today] if session_open else []
    if session_open:
        primary = [r for r in primary if r[0] != today]
        backfill = [r for r in backfill if r[0] != today]
    if intraday:
        q = intraday[-1]
        quote = {"ticker": ticker, "session_date": today, "price": float(q[4]),
                 "status": "intraday, session not closed", "as_of_et": now_et.isoformat(timespec="minutes"),
                 "source": q[6], "classification": "Fact (dated market source, intraday)"}
        (path.parent / "latest-quote.json").write_text(json.dumps(quote, indent=2) + "\n", encoding="utf-8")
        print(f"{ticker}: intraday {today} price {quote['price']:.2f} as of {quote['as_of_et']} ET "
              "(stored in latest-quote.json, not as a daily bar)")
    merged: Dict[str, List[Any]] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                merged[r["date"][:10]] = [r.get(h, "") for h in header]
    av_close = {r[0]: float(r[4]) for r in primary}
    diffs = [d for d, *_v in backfill if d in av_close
             and abs(float(_v[3]) / av_close[d] - 1) > 0.005]
    for row in backfill:
        merged[row[0]] = row
    for row in primary:
        merged[row[0]] = row
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(merged[d] for d in sorted(merged))
    last = merged[max(merged)]
    print(f"{ticker}: {len(merged)} rows ({len(primary)} Alpha Vantage, {len(backfill)} yfinance) -> "
          f"{path.relative_to(root)}; latest {last[0]} close {float(last[4]):.2f} [{last[6]}]")
    if diffs:
        print(f"WARNING: {len(diffs)} overlapping closes differ >0.5% between sources (Alpha Vantage kept)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze"); a.add_argument("ticker"); a.add_argument("events", type=Path)
    a.add_argument("--write", action="store_true", help="write market/event-reactions.csv")
    f = sub.add_parser("fetch"); f.add_argument("ticker")
    f.add_argument("--source", choices=("auto", "alphavantage", "yfinance"), default="auto")
    f.add_argument("--period", default="2y", help="yfinance backfill period")
    args = parser.parse_args()
    if args.cmd == "fetch":
        return fetch(args.ticker.upper(), args.source, period=args.period)
    rows = analyze(args.ticker, args.events)
    out = sys.stdout
    if args.write:
        out = (company_dir(args.ticker) / "market/event-reactions.csv").open("w", newline="", encoding="utf-8")
    w = csv.DictWriter(out, fieldnames=EVENT_REACTION_HEADER)
    w.writeheader()
    w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
