#!/usr/bin/env python3
"""Human review CLI for the Research OS quality log (research/quality/).

  list               python3 scripts/quality_review.py list --status pending [--ticker PL] [--requirement required]
  show               python3 scripts/quality_review.py show <quality_event_id>
  review             python3 scripts/quality_review.py review <id> [--priority-correct false --reviewed-priority MEDIUM
                         --reason "..."] [--set field=value ...] [--research-value HIGH] [--notes "..."]
                     (no field flags on a terminal → asks only the event's relevant fields)
  correct            python3 scripts/quality_review.py correct <id> --field priority --reviewed-value MEDIUM
                         --reason "routine contract extension, no thesis impact" [--module priority_engine]
  add-missed-event   python3 scripts/quality_review.py add-missed-event --ticker PL --event-date 2026-09-15
                         --event-type major_contract --source URL --why-material "..." --expected-workflow targeted-update
                     (missing arguments are asked for on a terminal)
  summary            python3 scripts/quality_review.py summary [--month 2026-10]  (= quality_summary.py)
  seed               create the initial pending sample events from PL / RKLB / AAPL regression cases

Values: true / false / unknown / not_applicable. Only fill the fields that are relevant.
Corrections are appended to research/quality/corrections.jsonl and never change rules.
Review notes that argue from later price moves are rejected (hindsight bias).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import quality_log as ql  # noqa: E402

FLAG_FIELDS = ("event_detected_correctly", "event_classification_correct", "priority_correct",
               "guidance_extracted_correctly", "management_change_correct", "kpi_extraction_correct",
               "promise_resolution_correct", "thesis_update_useful", "valuation_update_useful",
               "monitoring_trigger_correct", "monthly_review_useful", "false_positive", "false_negative",
               "manual_correction_required", "classification_verdict", "reviewed_classification", "reviewed_priority",
               "interpretation_verdict", "interpretation_module", "research_value", "confidence", "missed_information",
               "notes", "guidance_items_reviewed", "guidance_items_correct")


# --------------------------------------------------------------------------- seed samples

def _replay(ticker: str, etype: str, ts: str, source: str, source_type: str, key: str, root: Path,
            as_of: str, **details: Any) -> Dict[str, Any]:
    """Run the real Level 4 classifier + priority engine on a known regression event."""
    import research_event_classifier as clf
    import research_event_detector as det
    import research_priority as prio
    ev = det._ev(ticker, etype, ts, source, source_type, key, **details)
    ev = clf.classify(ev, clf.context_for(ticker, [ev], root))
    return prio.prioritize_events(ticker, [ev], root, as_of)[0]


def _so_from(ev: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    so = {"detected": True, "classification": ev.get("category"), "category_name": ev.get("category_name"),
          "priority": ev.get("priority"), "severity": ev.get("severity"), "required_workflow": ev.get("required_workflow"),
          "evidence_quality": ev.get("evidence_quality"), "reason": ev.get("reason"),
          "priority_reasons": (ev.get("priority_reasons") or [])[:5]}
    so.update(extra)
    return so


def seed(root: Path = ROOT, as_of: str = "2026-10-13") -> Dict[str, Any]:
    """5-10 pending sample events from known PL / RKLB / AAPL regression cases. Nothing is
    marked reviewed: these wait for a human."""
    import level4_common as l4
    q = {i["event_id"]: i for i in (l4.read_json(root / "research/queue/current.json", {}) or {}).get("items", [])}
    replay_note = ("system classification / priority computed by replaying the Level 4 classifier and priority "
                   f"engine on {as_of} state (event predates the first Level 4 scan)")
    evs: List[Dict[str, Any]] = []

    # PL earnings (Q2 FY2027, 8-K Item 2.02) → absorbed by the UPDATE pipeline
    e = _replay("PL", "earnings_release", "2026-09-03",
                "https://www.sec.gov/Archives/edgar/data/1836833/000119312526381874/pl-ex99_1.htm",
                "SEC 8-K Item 2.02 earnings release", "q2fy2027", root, as_of, form="8-K", items="2.02")
    gva = l4.read_json(root / "research/PL/management/guidance-vs-actual.json", {}) or {}
    evs.append(ql.new_event(workflow="update-stock", ticker="PL", event_id=e["event_id"], event_type="earnings_release",
                            day=as_of, origin="seed", source_reference=e["source"],
                            system_output=_so_from(e, replay=True, replay_note=replay_note,
                                                   guidance_counts=gva.get("counts"),
                                                   outputs=["research/PL/reports/2026-10-13-change-report.md"]),
                            references=["research/PL/reports/2026-10-13-change-report.md",
                                        "research/PL/management/guidance-vs-actual.json",
                                        "research/PL/market/event-reactions.csv"],
                            modules=["event_classifier", "priority_engine", "guidance_tracker", "management_diff",
                                     "promise_tracker", "kpi_registry", "thesis_monitor", "valuation_monitor"]))
    # PL German federal contract (issuer announcement 2026-09-15)
    e = _replay("PL", "major_contract", "2026-09-15",
                "https://investors.planet.com/news/news-details/2026/Planet-Awarded-Landmark-German-Federal-Contract-"
                "for-Exclusive-Access-to-Dedicated-Satellite-Constellation/default.aspx",
                "issuer press release", "german-bmi-bkg", root, as_of,
                description="German BMI/BKG satellite services tender award (max EUR 25m incl. options)")
    evs.append(ql.new_event(workflow="targeted-update", ticker="PL", event_id=e["event_id"], event_type="major_contract",
                            day=as_of, origin="seed", source_reference=e["source"],
                            system_output=_so_from(e, replay=True, replay_note=replay_note),
                            references=["research/PL/evidence/sources.json", "research/PL/market/event-reactions.csv"],
                            modules=["event_detector", "event_classifier", "priority_engine", "thesis_monitor"]))
    # PL price event after Q1 FY2027 results (day return -26%, t0 2026-06-05)
    e = _replay("PL", "major_price_move", "2026-06-05", "research/PL/market/prices.csv", "market data (daily close)",
                "2026-06-05-move", root, as_of, move_pct=-25.98, volume_ratio=3.71)
    evs.append(ql.new_event(workflow="market-reaction", ticker="PL", event_id=e["event_id"], event_type="major_price_move",
                            day=as_of, origin="seed", source_reference="research/PL/market/event-reactions.csv",
                            system_output=_so_from(e, replay=True, replay_note=replay_note),
                            references=["research/PL/market/event-reactions.csv"],
                            modules=["event_detector", "event_classifier", "priority_engine"]))
    # PL standing dilution trigger (actual queue item)
    pl_dil = q.get("PL-2026-10-13-standing_trigger-12d16898")
    if pl_dil:
        evs.append(ql.new_event(workflow="scan-research", ticker="PL", event_id=pl_dil["event_id"],
                                event_type=pl_dil["event_type"], day=as_of, origin="seed",
                                source_reference=pl_dil.get("source", ""),
                                system_output=_so_from(pl_dil, triggered_rules=[pl_dil["details"].get("rule")]),
                                references=["research/queue/current.json", "research/PL/monitoring/rules.yaml"],
                                modules=list(ql.SCAN_MODULES)))
    # RKLB INIT baseline (latest earnings absorbed into the baseline)
    rg = l4.read_json(root / "research/RKLB/management/guidance-vs-actual.json", {}) or {}
    evs.append(ql.new_event(workflow="init-stock", ticker="RKLB", event_id="RKLB-2026-10-13-init-stock",
                            event_type="init_baseline", day=as_of, origin="seed",
                            source_reference="research/RKLB/reports/2026-10-13-baseline-report.md",
                            system_output={"detected": True, "classification": None, "priority": None,
                                           "thesis_draft_auto": True, "guidance_counts": rg.get("counts"),
                                           "outputs": ["research/RKLB/reports/2026-10-13-baseline-report.md"]},
                            references=["research/RKLB/reports/2026-10-13-baseline-report.md",
                                        "research/RKLB/management/guidance-vs-actual.json",
                                        "research/RKLB/financials/kpi-history.csv"],
                            modules=["kpi_registry", "guidance_tracker", "management_diff", "promise_tracker",
                                     "thesis_monitor", "valuation_monitor"]))
    # RKLB Neutron first-launch delay (actual queue item)
    nd = q.get("RKLB-2026-10-13-promise_delayed-e02b11c9")
    if nd:
        evs.append(ql.new_event(workflow="scan-research", ticker="RKLB", event_id=nd["event_id"],
                                event_type=nd["event_type"], day=as_of, origin="seed", source_reference=nd.get("source", ""),
                                system_output=_so_from(nd),
                                references=["research/queue/current.json", "research/RKLB/management/promises.json"],
                                modules=list(ql.SCAN_MODULES) + ["promise_tracker", "guidance_tracker"]))
    # AAPL earnings (Q3 FY2026, 8-K Item 2.02) → UPDATE pipeline change report
    e = _replay("AAPL", "earnings_release", "2026-07-30",
                "https://www.sec.gov/Archives/edgar/data/320193/000032019326000018/aapl-20260730.htm",
                "SEC 8-K Item 2.02 earnings release", "q3fy2026", root, as_of, form="8-K", items="2.02")
    evs.append(ql.new_event(workflow="update-stock", ticker="AAPL", event_id=e["event_id"], event_type="earnings_release",
                            day=as_of, origin="seed", source_reference=e["source"],
                            system_output=_so_from(e, replay=True, replay_note=replay_note, guidance_items=0,
                                                   outputs=["research/AAPL/reports/2026-10-13-change-report.md"]),
                            references=["research/AAPL/reports/2026-10-13-change-report.md",
                                        "research/AAPL/market/event-reactions.csv"],
                            modules=["event_classifier", "priority_engine", "kpi_registry", "management_diff",
                                     "thesis_monitor", "valuation_monitor"]))
    # October monthly review
    evs.append(ql.new_event(workflow="monthly-research", ticker="ALL", event_id="ALL-2026-10-monthly-research",
                            event_type="monthly_review", day=as_of, origin="seed",
                            source_reference="research/reviews/2026-10-monthly-review.md",
                            system_output={"detected": True, "classification": None, "priority": None,
                                           "companies": ["AAPL", "PL", "RKLB"],
                                           "outputs": ["research/reviews/2026-10-monthly-review.md"]},
                            references=["research/reviews/2026-10-monthly-review.md"], modules=["monthly_review"]))
    res = ql.record(evs, root)
    res["quality_event_ids"] = [x["quality_event_id"] for x in evs]
    return res


# --------------------------------------------------------------------------- CLI

def _show(e: Dict[str, Any]) -> str:
    so, hr = e["system_output"], e["human_review"]
    L = [f"{e['quality_event_id']}  [{e['review_status']}｜{e.get('review_requirement')}｜{e.get('origin')}]",
         f"  {e['date']} {e['ticker']} {e['workflow']} {e['event_type']}  event_id={e['event_id']}",
         f"  source: {e.get('source_reference') or '—'}",
         f"  system: classification={so.get('classification')} priority={so.get('priority')} "
         f"reason={str(so.get('reason') or '')[:120]}",
         f"  relevant fields: {', '.join(so.get('relevant_review_fields') or [])}",
         "  review: " + ", ".join(f"{k}={ql._fmt(v)}" for k, v in hr.items()
                                  if v not in (ql.UNKNOWN, "", None, []) and k != "interpretation_module"),
         f"  corrections: {len(e['corrections'])}  references: {', '.join(e['references'])}"]
    if e.get("missed_event"):
        L.append(f"  missed: {e['missed_event']}")
    return "\n".join(L)


def _ask(prompt: str, default: str = "") -> str:
    v = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return v or default


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=ROOT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("--status", choices=ql.REVIEW_STATUSES)
    p.add_argument("--ticker")
    p.add_argument("--requirement", choices=("required", "spot_check", "sample"))
    p = sub.add_parser("show")
    p.add_argument("id")
    p = sub.add_parser("review")
    p.add_argument("id")
    for f in FLAG_FIELDS:
        p.add_argument("--" + f.replace("_", "-"), dest=f)
    p.add_argument("--set", action="append", default=[], metavar="FIELD=VALUE")
    p.add_argument("--extraction-error", action="append", default=[], metavar="MODULE:TYPE")
    p.add_argument("--reason", default="")
    p.add_argument("--reviewer", default="human")
    p.add_argument("--status", default="reviewed", choices=ql.REVIEW_STATUSES)
    p = sub.add_parser("correct")
    p.add_argument("id")
    p.add_argument("--field", required=True)
    p.add_argument("--reviewed-value", required=True)
    p.add_argument("--system-value")
    p.add_argument("--reason", required=True)
    p.add_argument("--module", choices=ql.MODULES)
    p.add_argument("--reviewer", default="human")
    p = sub.add_parser("add-missed-event")
    for f in ("ticker", "event_date", "event_type", "source", "why_material", "expected_workflow"):
        p.add_argument("--" + f.replace("_", "-"), dest=f)
    p.add_argument("--notes", default="")
    p.add_argument("--reviewer", default="human")
    p.add_argument("--as-of")
    p = sub.add_parser("summary")
    p.add_argument("--month")
    p = sub.add_parser("seed")
    p.add_argument("--as-of", default="2026-10-13")
    a = ap.parse_args(argv)
    root = a.root
    try:
        if a.cmd == "list":
            rows = ql.list_events(root, a.status, a.ticker, a.requirement)
            for e in rows:
                so = e["system_output"]
                print(f"{e['quality_event_id']:32s} {e['review_status']:9s} {e.get('review_requirement', ''):10s} "
                      f"{e['ticker']:5s} {e['workflow']:16s} {e['event_type']:20s} "
                      f"cls={so.get('classification') or '-'} prio={so.get('priority') or '-'}")
            print(f"{len(rows)} event(s)")
        elif a.cmd == "show":
            print(_show(ql.get_event(a.id, root)))
        elif a.cmd == "review":
            fields: Dict[str, Any] = {f: getattr(a, f) for f in FLAG_FIELDS if getattr(a, f) is not None}
            for kv in a.set:
                k, _, v = kv.partition("=")
                fields[k.strip()] = v.strip()
            if not fields and not a.extraction_error and sys.stdin.isatty():
                e = ql.get_event(a.id, root)
                print(_show(e))
                print("Enter = skip (stays unknown). Values: true / false / unknown / not_applicable.")
                for f in e["system_output"].get("relevant_review_fields") or []:
                    v = _ask(f)
                    if v:
                        fields[f] = v
                n = _ask("notes")
                if n:
                    fields["notes"] = n
            e = ql.review(a.id, fields, a.reviewer, a.reason, a.status, a.extraction_error, root)
            print(_show(e))
        elif a.cmd == "correct":
            c = ql.correct(a.id, a.field, a.reviewed_value, a.reason, a.module, a.system_value, a.reviewer, root)
            print(f"{c['correction_id']}: {c['module']} {c['field']} {c['system_value']} → {c['reviewed_value']} "
                  f"(saved to research/quality/corrections.jsonl)")
        elif a.cmd == "add-missed-event":
            vals = {f: getattr(a, f) for f in ("ticker", "event_date", "event_type", "source", "why_material",
                                               "expected_workflow")}
            for f, v in vals.items():
                if not v:
                    if not sys.stdin.isatty():
                        ap.error(f"--{f.replace('_', '-')} is required")
                    vals[f] = _ask(f)
            e = ql.add_missed_event(**vals, reported_by=a.reviewer, notes=a.notes, as_of=a.as_of, root=root)
            print(_show(e))
        elif a.cmd == "summary":
            import quality_summary
            res = quality_summary.run(a.month, root)
            print(res["path"])
            print(res["text"])
        elif a.cmd == "seed":
            res = seed(root, a.as_of)
            print(f"seed: {res['added']} added, {res['refreshed']} refreshed, {res['total']} total (all pending)")
            for qid in res["quality_event_ids"]:
                print("  " + qid)
    except ql.QualityError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
