#!/usr/bin/env python3
"""Research event queue (Level 4): research/queue/current.json.

Each item:
  event_id, ticker, event_type, detected_at, timestamp, priority, priority_reasons,
  category, severity, required_workflow, source, reason, immediate_alert, status, details
Status: pending → processing → completed | dismissed | superseded.

Rules
- Idempotent: an event_id already in the queue is never re-added (its status is kept).
- A pending FULL_UPDATE (A) for a ticker supersedes that ticker's older pending
  MARKET_REACTION_ONLY (C) and LOW_PRIORITY (D) items: the full update covers them.
- Completed / dismissed / superseded items older than queue.archive_after_days move to
  research/queue/archive/YYYY-MM.json.
- /update-stock completes the ticker's pending A / B items (research_pipeline.py hook).

Usage:
  python3 scripts/research_queue.py list [--all]
  python3 scripts/research_queue.py set EVENT_ID processing|completed|dismissed [--note TEXT]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import level4_common as l4  # noqa: E402

STATUSES = ("pending", "processing", "completed", "dismissed", "superseded")
OPEN = ("pending", "processing")
PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def queue_path(root: Path = ROOT) -> Path:
    return root / "research/queue/current.json"


def load(root: Path = ROOT) -> Dict[str, Any]:
    q = l4.read_json(queue_path(root), {}) or {}
    q.setdefault("items", [])
    return q


def save(q: Dict[str, Any], root: Path = ROOT) -> None:
    q["updated_at"] = l4.now_iso()
    q["note"] = ("Research queue: every item is a research task. Triggers mean REASSESS; "
                 "nothing here is a buy / sell order.")
    q["items"] = sorted(q["items"], key=lambda i: (i["status"] not in OPEN, PRIORITY_RANK.get(i.get("priority"), 3),
                                                   i.get("category", "Z"), i["ticker"], i.get("timestamp", "")))
    l4.assert_no_orders(q)
    l4.write_json(queue_path(root), q)


def to_item(e: Dict[str, Any]) -> Dict[str, Any]:
    return {"event_id": e["event_id"], "ticker": e["ticker"], "event_type": e["event_type"],
            "detected_at": e.get("detected_at") or l4.now_iso(), "timestamp": e.get("timestamp"),
            "priority": e.get("priority", "LOW"), "priority_reasons": e.get("priority_reasons", []),
            "category": e.get("category"), "category_name": e.get("category_name"), "severity": e.get("severity"),
            "required_workflow": e.get("required_workflow"), "source": e.get("source"),
            "evidence_quality": e.get("evidence_quality"), "reason": e.get("reason"),
            "immediate_alert": bool(e.get("immediate_alert")), "status": "pending", "details": e.get("details", {})}


def enqueue(events: Iterable[Dict[str, Any]], root: Path = ROOT, q: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    q = q or load(root)
    by_id = {i["event_id"]: i for i in q["items"]}
    added = 0
    for e in events:
        if e["event_id"] in by_id:
            cur = by_id[e["event_id"]]
            if cur["status"] in OPEN:  # refresh classification / priority of open items
                for k in ("priority", "priority_reasons", "severity", "category", "category_name",
                          "required_workflow", "reason", "immediate_alert"):
                    if k in e:
                        cur[k] = e[k]
            continue
        item = to_item(e)
        q["items"].append(item)
        by_id[item["event_id"]] = item
        added += 1
    supersede(q)
    q["last_added"] = added
    return q


def supersede(q: Dict[str, Any]) -> int:
    n = 0
    full = {}
    for i in q["items"]:
        if i["status"] in OPEN and i.get("category") == "A":
            full[i["ticker"]] = max(full.get(i["ticker"], ""), i.get("timestamp") or "")
    for i in q["items"]:
        if i["status"] == "pending" and i.get("category") in ("C", "D") and i["ticker"] in full \
                and (i.get("timestamp") or "") <= full[i["ticker"]]:
            i["status"] = "superseded"
            i["status_note"] = f"covered by pending FULL_UPDATE for {i['ticker']}"
            n += 1
    return n


def set_status(event_id: str, status: str, note: str = "", root: Path = ROOT) -> Dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    q = load(root)
    for i in q["items"]:
        if i["event_id"] == event_id:
            i["status"] = status
            i["status_updated"] = l4.now_iso()
            if note:
                i["status_note"] = note
            save(q, root)
            return i
    raise KeyError(event_id)


def complete_for_ticker(ticker: str, as_of: str, categories=("A", "B"), note: str = "",
                        root: Path = ROOT) -> int:
    """Mark a ticker's open items detected on or before as_of as completed (after /update-stock)."""
    q = load(root)
    n = 0
    for i in q["items"]:
        if i["ticker"] == ticker.upper() and i["status"] in OPEN and i.get("category") in categories \
                and (i.get("timestamp") or "") <= as_of:
            i["status"] = "completed"
            i["status_updated"] = l4.now_iso()
            i["status_note"] = note or f"handled by UPDATE {as_of}"
            n += 1
    if n:
        save(q, root)
    return n


def archive(q: Dict[str, Any], root: Path = ROOT, as_of: Optional[str] = None) -> int:
    days = int(l4.load_policy(root)["queue"]["archive_after_days"])
    as_of = l4.today(as_of)
    keep, moved = [], {}
    for i in q["items"]:
        age = l4.days_between(i.get("detected_at"), as_of)
        if i["status"] not in OPEN and age is not None and age > days:
            moved.setdefault(i["detected_at"][:7], []).append(i)
        else:
            keep.append(i)
    for month, items in moved.items():
        path = root / "research/queue/archive" / f"{month}.json"
        old = l4.read_json(path, []) or []
        ids = {x["event_id"] for x in old}
        l4.write_json(path, old + [x for x in items if x["event_id"] not in ids])
    q["items"] = keep
    return sum(len(v) for v in moved.values())


def open_items(root: Path = ROOT, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    return [i for i in load(root)["items"] if i["status"] in OPEN and (ticker is None or i["ticker"] == ticker.upper())]


def render(q: Dict[str, Any], show_all: bool = False) -> str:
    items = q["items"] if show_all else [i for i in q["items"] if i["status"] in OPEN]
    L = ["| Priority | Ticker | Cat | Event | Date | Workflow | Reason | Status |", "|---|---|---|---|---|---|---|---|"]
    for i in items:
        L.append(f"| {i.get('priority')} | {i['ticker']} | {i.get('category')} | {i['event_type']} | {i.get('timestamp')} | "
                 f"{(i.get('required_workflow') or '')[:70]} | {(i.get('reason') or '')[:90]} | {i['status']} |")
    return "\n".join(L)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--all", action="store_true")
    p = sub.add_parser("set"); p.add_argument("event_id"); p.add_argument("status", choices=STATUSES)
    p.add_argument("--note", default="")
    args = ap.parse_args(argv)
    if args.cmd == "list":
        print(render(load(), args.all))
    else:
        print(set_status(args.event_id, args.status, args.note))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
