#!/usr/bin/env python3
"""US equity price / volume reaction analyzer (replaces the Taiwan FinMind workflow).

Reads research/<TICKER>/market/prices.csv (date,open,high,low,close,volume,...)
and an events CSV (event_date,event_type,description,source), typically SEC
filing dates, earnings dates and 8-K guidance changes. Output columns are
observations only; the `interpretation` column is left for the analyst.
Volume alone is never read as "smart money".

Optional price refresh (network, uses the finance-skill clients):
  uv run --project .claude/skills/finance-skill/scripts python \
      scripts/price_reaction.py fetch PL --source alphavantage
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from datetime import datetime, timezone
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
                   drift_days: int = 20) -> Optional[Dict[str, Any]]:
    """Reaction on the first session on/after event_date (t0). Returns None if no data."""
    idx = next((i for i, r in enumerate(prices) if r["date"] >= event_date), None)
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
            r = event_reaction(prices, ev["event_date"])
            row = {k: "" for k in EVENT_REACTION_HEADER}
            row.update({k: ev.get(k, "") for k in ("event_date", "event_type", "description", "source")})
            if r is None:
                row["observation"] = "insufficient local price data"
            else:
                row.update({k: ("" if r.get(k) is None else r[k]) for k in EVENT_REACTION_HEADER if k in r})
            row["interpretation"] = ""  # analyst-owned; never auto-filled
            rows.append(row)
    return rows


def fetch(ticker: str, source: str, root: Path = ROOT) -> int:
    """Refresh prices.csv. Network call; Alpha Vantage preferred, yfinance fallback."""
    sys.path.insert(0, str(ROOT / ".claude/skills/finance-skill/scripts"))
    retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    if source == "alphavantage":
        import alphavantage
        series = alphavantage.get_daily_prices(ticker, "full").get("Time Series (Daily)", {})
        for d, v in series.items():
            rows.append([d, v["1. open"], v["2. high"], v["3. low"], v["4. close"], v["5. volume"],
                         "Alpha Vantage TIME_SERIES_DAILY (unadjusted)", retrieved])
    else:
        import yfinance
        hist = yfinance.Ticker(ticker).history(period="2y", auto_adjust=False)
        for idx, v in hist.iterrows():
            rows.append([idx.strftime("%Y-%m-%d"), v["Open"], v["High"], v["Low"], v["Close"],
                         int(v["Volume"]), "yfinance (tier 4, cross-check only)", retrieved])
    if not rows:
        print("ERROR: no price rows returned; prices.csv left unchanged", file=sys.stderr)
        return 2
    path = company_dir(ticker, root) / "market/prices.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close", "volume", "source", "retrieved_at"])
        w.writerows(sorted(rows))
    print(f"{len(rows)} rows written to {path.relative_to(root)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze"); a.add_argument("ticker"); a.add_argument("events", type=Path)
    a.add_argument("--write", action="store_true", help="write market/event-reactions.csv")
    f = sub.add_parser("fetch"); f.add_argument("ticker")
    f.add_argument("--source", choices=("alphavantage", "yfinance"), default="alphavantage")
    args = parser.parse_args()
    if args.cmd == "fetch":
        return fetch(args.ticker.upper(), args.source)
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
