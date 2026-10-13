#!/usr/bin/env python3
"""Level 4 research command center: event-driven, multi-company, priority-aware.

  DATA / EVENTS (SEC, market, company IR, research state)
        → research_event_detector.py   (incremental; scan-state per ticker)
        → research_event_classifier.py (A full update / B targeted / C market only / D info)
        → research_queue.py            (research/queue/current.json)
        → research_priority.py         (HIGH / MEDIUM / LOW with reasons; cross-company rank)
        → existing Level 3 workflows   (/update-stock = research_pipeline.py update)
        → research_dashboard.py        (research/dashboard/current.{md,json})

Commands (slash commands in .claude/commands/):
  scan        /scan-research      refresh (optional) → detect → classify → enqueue → prioritize
                                  → KPI registry, guidance tracker, catalyst calendar, stale check
  queue       /research-queue     prioritized open queue with the workflow each item needs
  prioritize                      recompute priorities from the open queue and staleness
  dashboard   /research-dashboard watchlist command center
  stale       /stale-research     stale research detector
  calendar                        catalyst calendar
Every trigger means REASSESS. Nothing here executes or recommends a trade.

Usage:
  python3 scripts/research_command_center.py scan [--refresh] [--skip-prices] [--tickers PL RKLB] [--as-of D]
  python3 scripts/research_command_center.py queue|prioritize|dashboard|stale|calendar [--as-of D]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalyst_calendar as cal  # noqa: E402
import guidance_tracker as gt  # noqa: E402
import kpi_registry as kr  # noqa: E402
import level4_common as l4  # noqa: E402
import research_dashboard as dash  # noqa: E402
import research_event_classifier as clf  # noqa: E402
import research_event_detector as det  # noqa: E402
import research_priority as prio  # noqa: E402
import research_queue as rq  # noqa: E402
import stale_research as sr  # noqa: E402


def _refresh_prices(ticker: str, root: Path) -> str:
    import research_pipeline as rp
    try:
        return rp.fetch_prices(ticker, root, "1y")
    except Exception as exc:  # network optional; state stays usable
        return f"price refresh failed: {exc!r}"[:200]


def prioritize(root: Path = ROOT, as_of: Optional[str] = None, tickers: Optional[List[str]] = None) -> Dict[str, Any]:
    as_of = l4.today(as_of)
    tickers = tickers or [e["ticker"] for e in l4.load_watchlist(root)]
    q = rq.load(root)
    calendar = l4.read_csv(root / "research/calendar/upcoming.csv")
    # re-score open items so priorities reflect the current queue (e.g. multiple triggers)
    for t in tickers:
        items = [i for i in q["items"] if i["ticker"] == t and i["status"] in rq.OPEN]
        scored = prio.prioritize_events(t, items, root, as_of)
        for i, s in zip(items, scored):
            i.update({k: s[k] for k in ("priority", "priority_reasons", "linked_components", "high_importance_links")})
    rq.save(q, root)
    rows = []
    for t in tickers:
        items = [i for i in q["items"] if i["ticker"] == t and i["status"] in rq.OPEN]
        rows.append(prio.ticker_priority(t, items, sr.check(t, root, as_of, calendar), root, as_of))
    return prio.write(prio.rank(rows), root, as_of)


def scan(root: Path = ROOT, as_of: Optional[str] = None, tickers: Optional[List[str]] = None,
         refresh: bool = False, skip_prices: bool = True, save_state: bool = True) -> Dict[str, Any]:
    as_of = l4.today(as_of)
    entries = [e for e in l4.load_watchlist(root) if not tickers or e["ticker"] in [x.upper() for x in tickers]]
    log: Dict[str, Any] = {}
    q = rq.load(root)
    seen_ids = {i["event_id"] for i in q["items"]}
    for e in entries:
        t = e["ticker"]
        if not (l4.company_dir(t, root) / "thesis/current.yaml").exists():
            log[t] = {"skipped": "no research state; run /init-stock first"}
            continue
        step: Dict[str, Any] = {}
        if not skip_prices:
            step["prices"] = _refresh_prices(t, root)
        step["kpi"] = {k: v for k, v in kr.build(t, root, as_of).items() if k in ("required_unavailable", "errors")}
        g = gt.track(t, root, as_of, parse=True)
        step["guidance"] = {"added": g["guidance_added"], "counts": g["counts"], "message": g["message"]}
        res = det.detect(t, root, as_of, refresh=refresh, save_state=save_state)
        events = clf.classify_all(t, res["events"], root)
        events = prio.prioritize_events(t, events, root, as_of)
        q = rq.enqueue(events, root, q)
        step.update({"since": res["since"], "first_scan": res["first_scan"], "events": len(events),
                     "by_category": {c: sum(x["category"] == c for x in events) for c in "ABCD"}})
        log[t] = step
    rq.archive(q, root, as_of)
    rq.save(q, root)
    cal.build([e["ticker"] for e in entries] if tickers else None, root, as_of)
    sr.run(root, as_of)
    pri = prioritize(root, as_of)
    out = {"as_of": as_of, "tickers": log, "priorities": pri["tickers"],
           "open_items": len(rq.open_items(root)), "quality": record_quality(root, as_of, seen_ids, log)}
    l4.write_json(root / "research/queue/last-scan.json", out)
    return out


def record_quality(root: Path, as_of: str, seen_ids: set, log: Dict[str, Any]) -> Dict[str, Any]:
    """Quality evaluation layer: one pending quality event per new queue item (or one run-level
    event when the scan found nothing, so missed events can still be attached to the run)."""
    try:
        import quality_log as ql
        new_items = [i for i in rq.load(root)["items"] if i["event_id"] not in seen_ids]
        if new_items:
            r = ql.record_queue_items(new_items, as_of, root=root)
            return {"added": r["added"], "quality_event_ids": r["quality_event_ids"]}
        r = ql.record_workflow("scan-research", "ALL", as_of,
                               {"detected": False, "classification": None, "priority": None, "new_events": 0,
                                "tickers": sorted(log)}, ["research/queue/last-scan.json"],
                               event_id=f"ALL-{as_of}-scan-research", event_type="scan_run",
                               modules=list(ql.SCAN_MODULES), root=root)
        return {"added": r["added"], "quality_event_ids": [r["quality_event_id"]]}
    except Exception as exc:  # never fails the scan
        return {"error": repr(exc)[:200]}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("scan", "queue", "prioritize", "dashboard", "stale", "calendar"))
    ap.add_argument("--as-of")
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--refresh", action="store_true", help="scan: refresh SEC submissions (network)")
    ap.add_argument("--skip-prices", action="store_true", help="scan: do not refresh prices")
    ap.add_argument("--all", action="store_true", help="queue: include closed items")
    args = ap.parse_args(argv)
    if args.cmd == "scan":
        out = scan(ROOT, args.as_of, args.tickers, args.refresh, args.skip_prices)
        for t, s in out["tickers"].items():
            print(f"{t}: {s}")
        for r in out["priorities"]:
            print(f"{r['rank']}. {r['ticker']} {r['priority']} — {'; '.join(r['reasons'])[:160]}")
        print(f"open queue items: {out['open_items']} → research/queue/current.json")
        print(f"quality events (pending review): {out['quality']} → research/quality/quality-events.jsonl")
    elif args.cmd == "queue":
        pri = l4.read_json(ROOT / "research/queue/priorities.json", {}) or {}
        for r in pri.get("tickers", []):
            print(f"{r['rank']}. {r['ticker']} {r['priority']} — {'; '.join(r['reasons'])[:200]}")
        print()
        print(rq.render(rq.load(), args.all))
    elif args.cmd == "prioritize":
        for r in prioritize(ROOT, args.as_of, args.tickers)["tickers"]:
            print(f"{r['rank']}. {r['ticker']} {r['priority']} — {'; '.join(r['reasons'])[:200]}")
    elif args.cmd == "dashboard":
        dash.build(ROOT, args.as_of)
        print((ROOT / "research/dashboard/current.md").read_text())
    elif args.cmd == "stale":
        for r in sr.run(ROOT, args.as_of):
            print(f"{r['ticker']}: {r['severity'] or 'not stale'} — {'; '.join(r['reasons']) or 'no staleness'}")
    elif args.cmd == "calendar":
        for r in cal.build(args.tickers, ROOT, args.as_of):
            print(f"{r['ticker']:5s} {r['expected_date']:12s} {r['confidence']:6s} {r['status']:9s} {r['event'][:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
