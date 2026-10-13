#!/usr/bin/env python3
"""Research OS quality log: an evaluation layer on top of the Level 4 research OS.

It records, per workflow run or detected event, what the system produced and what a
human reviewer later judged — event detection, classification, priority, extraction,
interpretation, valuation / monitoring process and research value — so the quality of
the research OS can be measured over time. It never changes research state, rules or
priorities: corrections are stored as a feedback dataset only (no self-modification).

Storage (research/quality/):
  quality-events.jsonl  machine-readable evaluation events (source of truth, one per line)
  quality-log.csv       human-readable summary, regenerated from the JSONL on every write
  corrections.jsonl     append-only manual corrections (feedback dataset for rule refinement)
  summaries/            monthly quality summaries (quality_summary.py)
  reviews/              optional free-form review notes

Only evaluation metadata and references are stored, never copies of filings or reports.

Review values are explicit: true / false / "unknown" (not yet judged) / "not_applicable".
Auto-created events start as review_status = pending with every human field "unknown";
the system may fill system_output (detected event, classification, priority, outputs,
guidance count, triggered rules) but never a human judgment.

Hindsight-bias rule: quality is about process, evidence and reasoning available at the
time. Later price moves are never a quality signal; review notes / correction reasons that
argue from subsequent returns are rejected, and no module here reads price data.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1

UNKNOWN, NA = "unknown", "not_applicable"
TRISTATE = (True, False, UNKNOWN, NA)

REVIEW_STATUSES = ("pending", "in_review", "reviewed", "dismissed")
ORIGINS = ("auto", "seed", "manual_missed")
WORKFLOWS = ("scan-research", "update-stock", "init-stock", "monthly-research", "targeted-update",
             "market-reaction", "manual")

MODULES = ("event_detector", "event_classifier", "priority_engine", "kpi_registry", "management_diff",
           "guidance_tracker", "promise_tracker", "thesis_monitor", "valuation_monitor", "monitoring_rules",
           "monthly_review")

# Boolean review fields → the module they grade. false_positive / false_negative grade the
# detector in the opposite direction (true = an error).
BOOL_FIELDS: Dict[str, str] = {
    "event_detected_correctly": "event_detector",
    "event_classification_correct": "event_classifier",
    "priority_correct": "priority_engine",
    "guidance_extracted_correctly": "guidance_tracker",
    "management_change_correct": "management_diff",
    "kpi_extraction_correct": "kpi_registry",
    "promise_resolution_correct": "promise_tracker",
    "thesis_update_useful": "thesis_monitor",
    "valuation_update_useful": "valuation_monitor",
    "monitoring_trigger_correct": "monitoring_rules",
    "monthly_review_useful": "monthly_review",
    "false_positive": "event_detector",
    "false_negative": "event_detector",
    "manual_correction_required": "",
}
ERROR_WHEN_TRUE = ("false_positive", "false_negative", "manual_correction_required")

CLASSIFICATION_VERDICTS = ("correct", "too_high", "too_low", "wrong_type", UNKNOWN, NA)
INTERPRETATION_VERDICTS = ("correct", "reasonable_but_uncertain", "overinterpreted", "underinterpreted",
                           "unsupported", UNKNOWN, NA)
EXTRACTION_ERROR_TYPES = ("missing", "wrong_value", "wrong_unit", "wrong_period", "wrong_metric_definition",
                          "duplicate", "unsupported_inference")
RESEARCH_VALUES = ("HIGH", "MEDIUM", "LOW", "NONE", UNKNOWN, NA)
PRIORITIES = ("HIGH", "MEDIUM", "LOW")
CLASSIFICATIONS = ("A", "B", "C", "D")
CONFIDENCES = ("high", "medium", "low", UNKNOWN)

ENUM_FIELDS: Dict[str, tuple] = {
    "classification_verdict": CLASSIFICATION_VERDICTS,
    "interpretation_verdict": INTERPRETATION_VERDICTS,
    "research_value": RESEARCH_VALUES,
    "reviewed_priority": PRIORITIES + (UNKNOWN, NA),
    "reviewed_classification": CLASSIFICATIONS + (UNKNOWN, NA),
    "confidence": CONFIDENCES,
}
TEXT_FIELDS = ("missed_information", "notes", "interpretation_module")
COUNT_FIELDS = ("guidance_items_reviewed", "guidance_items_correct")
HUMAN_FIELDS = tuple(BOOL_FIELDS) + tuple(ENUM_FIELDS) + TEXT_FIELDS + COUNT_FIELDS + ("extraction_errors",)

# Which review fields are relevant for a workflow (a reviewer hint, never a judgment).
RELEVANT_FIELDS: Dict[str, List[str]] = {
    "scan-research": ["event_detected_correctly", "false_positive", "event_classification_correct",
                      "classification_verdict", "priority_correct", "reviewed_priority", "monitoring_trigger_correct",
                      "research_value"],
    "update-stock": ["guidance_extracted_correctly", "management_change_correct", "kpi_extraction_correct",
                     "promise_resolution_correct", "thesis_update_useful", "valuation_update_useful",
                     "monitoring_trigger_correct", "interpretation_verdict", "missed_information", "research_value"],
    "init-stock": ["kpi_extraction_correct", "guidance_extracted_correctly", "management_change_correct",
                   "promise_resolution_correct", "thesis_update_useful", "valuation_update_useful", "missed_information",
                   "research_value"],
    "monthly-research": ["monthly_review_useful", "false_negative", "missed_information", "priority_correct",
                         "research_value"],
    "targeted-update": ["event_detected_correctly", "event_classification_correct", "priority_correct",
                        "thesis_update_useful", "interpretation_verdict", "research_value"],
    "market-reaction": ["event_detected_correctly", "false_positive", "event_classification_correct",
                        "priority_correct", "interpretation_verdict", "research_value"],
    "manual": ["false_negative", "missed_information", "research_value"],
}

CSV_COLUMNS = [
    "quality_event_id", "date", "ticker", "event_id", "event_type", "workflow", "source_reference",
    "event_detected_correctly", "event_classification_correct", "priority_correct", "guidance_extracted_correctly",
    "management_change_correct", "kpi_extraction_correct", "promise_resolution_correct", "thesis_update_useful",
    "valuation_update_useful", "monitoring_trigger_correct", "false_positive", "false_negative", "missed_information",
    "manual_correction_required", "manual_correction_type", "research_value", "confidence", "review_status",
    "reviewed_by", "reviewed_at", "notes",
    # extra columns (after the required ones)
    "origin", "review_requirement", "system_classification", "classification_verdict", "system_priority",
    "reviewed_priority", "interpretation_verdict", "monthly_review_useful", "extraction_errors", "corrections",
]

# Arguments from later returns are not quality evidence (hindsight bias).
HINDSIGHT_PATTERNS = [
    r"\b(stock|share|price|shares)\b[^.;]{0,40}\b(later|subsequently|afterwards|since then|went on to)\b",
    r"\b(later|subsequently|afterwards|since then)\b[^.;]{0,40}\b(rose|fell|rallied|dropped|crashed|soared|went up|went down|up|down)\b",
    r"\b(return|returns|performance)\s+(since|after)\b",
    r"\b(stock|share|price)\s+(rose|fell|rallied|dropped|crashed|soared|went up|went down)\b[^.;]{0,30}\b(so|therefore|hence|proves|shows)\b",
    r"\bin hindsight\b",
    r"股價.{0,8}(後來|之後|事後)", r"(後來|之後|事後).{0,8}(上漲|下跌|大漲|大跌|漲|跌)", r"事後報酬", r"後來的報酬",
]
FORBIDDEN_FIELDS = ("return_after", "price_outcome", "outcome_correct", "subsequent_return", "forward_return",
                    "hit_rate", "pnl")


class QualityError(ValueError):
    pass


class HindsightBiasError(QualityError):
    pass


# --------------------------------------------------------------------------- paths / io

def quality_dir(root: Path = ROOT) -> Path:
    return root / "research/quality"


def events_path(root: Path = ROOT) -> Path:
    return quality_dir(root) / "quality-events.jsonl"


def corrections_path(root: Path = ROOT) -> Path:
    return quality_dir(root) / "corrections.jsonl"


def log_path(root: Path = ROOT) -> Path:
    return quality_dir(root) / "quality-log.csv"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=path.suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def load_events(root: Path = ROOT) -> List[Dict[str, Any]]:
    return _read_jsonl(events_path(root))


def load_corrections(root: Path = ROOT) -> List[Dict[str, Any]]:
    return _read_jsonl(corrections_path(root))


def save_events(events: List[Dict[str, Any]], root: Path = ROOT) -> None:
    for e in events:
        validate(e)
    _atomic_write(events_path(root), "".join(json.dumps(e, ensure_ascii=False, sort_keys=False) + "\n" for e in events))
    corrections_path(root).touch(exist_ok=True)  # the append-only feedback dataset always exists
    write_csv(events, root)


def get_event(qid: str, root: Path = ROOT) -> Dict[str, Any]:
    for e in load_events(root):
        if e["quality_event_id"] == qid:
            return e
    raise QualityError(f"unknown quality_event_id {qid}")


# --------------------------------------------------------------------------- schema

def quality_event_id(workflow: str, ticker: str, event_id: str, day: str) -> str:
    h = hashlib.sha1(f"{workflow}|{ticker}|{event_id}|{day}".encode()).hexdigest()[:8]
    return f"QE-{day.replace('-', '')}-{(ticker or 'ALL').upper()}-{h}"


def blank_review() -> Dict[str, Any]:
    r: Dict[str, Any] = {f: UNKNOWN for f in BOOL_FIELDS}
    r.update({f: UNKNOWN for f in ENUM_FIELDS})
    r.update({"missed_information": UNKNOWN, "notes": "", "interpretation_module": "management_diff",
              "guidance_items_reviewed": None, "guidance_items_correct": None, "extraction_errors": []})
    return r


def review_requirement(priority: Optional[str], workflow: str) -> str:
    """Review policy: HIGH must be reviewed; MEDIUM spot-check (or review if thesis changed);
    LOW sample review. Workflow-level runs default to spot_check."""
    p = (priority or "").upper()
    if p == "HIGH":
        return "required"
    if p == "MEDIUM":
        return "spot_check"
    if p == "LOW":
        return "sample"
    return "required" if workflow == "manual" else "spot_check"


def new_event(*, workflow: str, ticker: str, event_id: str, event_type: str, day: str,
              system_output: Dict[str, Any], references: Iterable[str] = (), source_reference: str = "",
              origin: str = "auto", modules: Iterable[str] = ()) -> Dict[str, Any]:
    if workflow not in WORKFLOWS:
        raise QualityError(f"workflow must be one of {WORKFLOWS}")
    if origin not in ORIGINS:
        raise QualityError(f"origin must be one of {ORIGINS}")
    so = {k: v for k, v in (system_output or {}).items() if k not in HUMAN_FIELDS}  # system cannot self-grade
    so.setdefault("detected", origin != "manual_missed")
    so["relevant_review_fields"] = RELEVANT_FIELDS.get(workflow, [])
    review = blank_review()
    if workflow == "monthly-research":
        review["interpretation_module"] = "monthly_review"
    return {
        "quality_event_id": quality_event_id(workflow, ticker, event_id, day),
        "schema_version": SCHEMA_VERSION,
        "date": day,
        "ticker": (ticker or "ALL").upper(),
        "event_id": event_id,
        "event_type": event_type,
        "workflow": workflow,
        "origin": origin,
        "source_reference": source_reference,
        "created_at": now_iso(),
        "review_requirement": review_requirement(so.get("priority"), workflow),
        "modules": sorted(set(modules) & set(MODULES)),
        "system_output": so,
        "human_review": review,
        "review_status": "pending",
        "reviewed_by": None,
        "reviewed_at": None,
        "corrections": [],
        "review_history": [],
        "references": [str(r) for r in references if r],
    }


def validate(e: Dict[str, Any]) -> None:
    for k in ("quality_event_id", "date", "ticker", "event_id", "event_type", "workflow", "system_output",
              "human_review", "review_status", "references", "corrections"):
        if k not in e:
            raise QualityError(f"quality event missing {k}")
    date.fromisoformat(e["date"])
    if e["review_status"] not in REVIEW_STATUSES:
        raise QualityError(f"review_status must be one of {REVIEW_STATUSES}")
    for f in FORBIDDEN_FIELDS:
        if f in e or f in e["human_review"] or f in e["system_output"]:
            raise HindsightBiasError(f"{f} is a return-outcome field; quality is graded on process, not returns")
    hr = e["human_review"]
    for f in BOOL_FIELDS:
        if hr.get(f, UNKNOWN) not in TRISTATE or hr.get(f) == "":
            raise QualityError(f"{f} must be true / false / unknown / not_applicable, got {hr.get(f)!r}")
    for f, allowed in ENUM_FIELDS.items():
        if hr.get(f, UNKNOWN) not in allowed:
            raise QualityError(f"{f} must be one of {allowed}, got {hr.get(f)!r}")
    for x in hr.get("extraction_errors") or []:
        if x.get("error_type") not in EXTRACTION_ERROR_TYPES or x.get("module") not in MODULES:
            raise QualityError(f"bad extraction error {x}")
    if hr.get("interpretation_module") not in MODULES:
        raise QualityError(f"interpretation_module must be one of {MODULES}")
    if e["review_status"] == "pending" and (e.get("reviewed_by") or e.get("reviewed_at")):
        raise QualityError("pending events cannot carry a reviewer")


def check_hindsight(text: str) -> None:
    for pat in HINDSIGHT_PATTERNS:
        if text and re.search(pat, text, flags=re.IGNORECASE):
            raise HindsightBiasError(
                "review text argues from later price / return outcomes (hindsight bias). Grade the process, evidence "
                "and reasoning that were available at the time instead: " + text[:160])


def _coerce(field: str, value: Any) -> Any:
    if field in BOOL_FIELDS:
        if isinstance(value, bool):
            return value
        v = str(value).strip().lower()
        m = {"true": True, "yes": True, "y": True, "1": True, "false": False, "no": False, "n": False, "0": False,
             "unknown": UNKNOWN, "?": UNKNOWN, "not_applicable": NA, "na": NA, "n/a": NA}
        if v not in m:
            raise QualityError(f"{field}: expected true / false / unknown / not_applicable, got {value!r}")
        return m[v]
    if field in ENUM_FIELDS:
        v = str(value).strip()
        v = v.upper() if field in ("research_value", "reviewed_priority", "reviewed_classification") \
            and v.lower() not in (UNKNOWN, NA) else v.lower()
        if v not in ENUM_FIELDS[field]:
            raise QualityError(f"{field} must be one of {ENUM_FIELDS[field]}, got {value!r}")
        return v
    if field in COUNT_FIELDS:
        return None if value in (None, "", UNKNOWN) else int(value)
    if field in TEXT_FIELDS:
        return str(value)
    raise QualityError(f"unknown review field {field}; allowed: {', '.join(HUMAN_FIELDS)}")


# --------------------------------------------------------------------------- CSV

def _fmt(v: Any) -> str:
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return ""
    return str(v)


def correction_type(e: Dict[str, Any]) -> str:
    kinds = []
    for c in e.get("corrections") or []:
        kinds.append(c["field"] if c["field"] != "extraction" else f"extraction:{c.get('reviewed_value')}")
    for x in e["human_review"].get("extraction_errors") or []:
        k = f"extraction:{x['error_type']}"
        if k not in kinds:
            kinds.append(k)
    if not kinds:
        mcr = e["human_review"].get("manual_correction_required")
        return "none" if mcr is False else (NA if mcr == NA else UNKNOWN)
    return ";".join(dict.fromkeys(kinds))


def csv_row(e: Dict[str, Any]) -> Dict[str, str]:
    hr, so = e["human_review"], e["system_output"]
    verdict = hr.get("classification_verdict", UNKNOWN)
    cls_ok = hr.get("event_classification_correct", UNKNOWN)
    row = {
        "quality_event_id": e["quality_event_id"], "date": e["date"], "ticker": e["ticker"], "event_id": e["event_id"],
        "event_type": e["event_type"], "workflow": e["workflow"], "source_reference": e.get("source_reference", ""),
        "event_classification_correct": _fmt(cls_ok),
        "manual_correction_type": correction_type(e),
        "review_status": e["review_status"], "reviewed_by": _fmt(e.get("reviewed_by")),
        "reviewed_at": _fmt(e.get("reviewed_at")), "notes": hr.get("notes", ""),
        "origin": e.get("origin", "auto"), "review_requirement": e.get("review_requirement", ""),
        "system_classification": _fmt(so.get("classification")), "classification_verdict": verdict,
        "system_priority": _fmt(so.get("priority")), "reviewed_priority": hr.get("reviewed_priority", UNKNOWN),
        "interpretation_verdict": hr.get("interpretation_verdict", UNKNOWN),
        "extraction_errors": ";".join(f"{x['module']}:{x['error_type']}" for x in hr.get("extraction_errors") or []) or "none",
        "corrections": str(len(e.get("corrections") or [])),
    }
    for f in ("event_detected_correctly", "priority_correct", "guidance_extracted_correctly", "management_change_correct",
              "kpi_extraction_correct", "promise_resolution_correct", "thesis_update_useful", "valuation_update_useful",
              "monitoring_trigger_correct", "false_positive", "false_negative", "manual_correction_required",
              "monthly_review_useful", "research_value", "confidence"):
        row[f] = _fmt(hr.get(f, UNKNOWN))
    mi = hr.get("missed_information", UNKNOWN)
    row["missed_information"] = mi if mi not in ("", None) else "none"
    return row


def write_csv(events: List[Dict[str, Any]], root: Path = ROOT) -> None:
    path = log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for e in sorted(events, key=lambda e: (e["date"], e["ticker"], e["quality_event_id"])):
            w.writerow(csv_row(e))


# --------------------------------------------------------------------------- create

def record(events_to_add: Iterable[Dict[str, Any]], root: Path = ROOT) -> Dict[str, int]:
    """Add evaluation events; an existing id keeps its human review. A pending event gets its
    system_output refreshed; a reviewed one is never touched."""
    events = load_events(root)
    by_id = {e["quality_event_id"]: e for e in events}
    added = refreshed = 0
    for e in events_to_add:
        validate(e)
        cur = by_id.get(e["quality_event_id"])
        if cur is None:
            events.append(e)
            by_id[e["quality_event_id"]] = e
            added += 1
        elif cur["review_status"] == "pending" and cur.get("origin") != "manual_missed":
            cur["system_output"] = e["system_output"]
            cur["references"] = sorted(set(cur["references"]) | set(e["references"]))
            refreshed += 1
    save_events(events, root)
    return {"added": added, "refreshed": refreshed, "total": len(events)}


def record_workflow(workflow: str, ticker: str, day: str, system_output: Dict[str, Any], references: Iterable[str] = (),
                    event_id: Optional[str] = None, event_type: Optional[str] = None, source_reference: str = "",
                    modules: Iterable[str] = (), root: Path = ROOT) -> Dict[str, Any]:
    e = new_event(workflow=workflow, ticker=ticker, event_id=event_id or f"{(ticker or 'ALL').upper()}-{day}-{workflow}",
                  event_type=event_type or workflow.replace("-", "_"), day=day, system_output=system_output,
                  references=references, source_reference=source_reference, modules=modules)
    res = record([e], root)
    res["quality_event_id"] = e["quality_event_id"]
    return res


SCAN_MODULES = ("event_detector", "event_classifier", "priority_engine", "monitoring_rules")


def record_queue_items(items: Iterable[Dict[str, Any]], day: str, workflow: str = "scan-research",
                       root: Path = ROOT) -> Dict[str, Any]:
    """One pending quality event per research-queue item the scan produced."""
    evs = []
    for i in items:
        so = {"detected": True, "classification": i.get("category"), "category_name": i.get("category_name"),
              "priority": i.get("priority"), "severity": i.get("severity"),
              "required_workflow": i.get("required_workflow"), "evidence_quality": i.get("evidence_quality"),
              "reason": i.get("reason"), "priority_reasons": (i.get("priority_reasons") or [])[:5],
              "triggered_rules": [i["details"]["rule"]] if (i.get("details") or {}).get("rule") else [],
              "event_timestamp": i.get("timestamp")}
        mods = list(SCAN_MODULES)
        if i.get("event_type", "").startswith("promise") or "guidance" in i.get("event_type", ""):
            mods += ["promise_tracker", "guidance_tracker"]
        evs.append(new_event(workflow=workflow, ticker=i["ticker"], event_id=i["event_id"], event_type=i["event_type"],
                             day=day, system_output=so, source_reference=str(i.get("source") or ""),
                             references=["research/queue/current.json"], modules=mods))
    res = record(evs, root)
    res["quality_event_ids"] = [e["quality_event_id"] for e in evs]
    return res


def add_missed_event(*, ticker: str, event_date: str, event_type: str, source: str, why_material: str,
                     expected_workflow: str, reported_by: str = "human", notes: str = "", as_of: Optional[str] = None,
                     root: Path = ROOT) -> Dict[str, Any]:
    """A material event the system never detected (false negative)."""
    as_of = as_of or date.today().isoformat()
    if date.fromisoformat(event_date) > date.fromisoformat(as_of):
        raise QualityError("event_date is in the future; a missed event must have been knowable at the time")
    check_hindsight(why_material)
    eid = f"{ticker.upper()}-{event_date}-missed-{hashlib.sha1(f'{event_type}|{source}'.encode()).hexdigest()[:8]}"
    e = new_event(workflow="manual", ticker=ticker, event_id=eid, event_type=event_type, day=as_of,
                  system_output={"detected": False, "classification": None, "priority": None},
                  source_reference=source, origin="manual_missed",
                  references=[source], modules=["event_detector"])
    e["missed_event"] = {"event_date": event_date, "why_material": why_material, "expected_workflow": expected_workflow,
                         "information_available_at": event_date}
    hr = e["human_review"]
    hr.update({"false_negative": True, "event_detected_correctly": False, "missed_information": why_material,
               "manual_correction_required": True, "notes": notes})
    e["review_status"] = "reviewed"
    e["reviewed_by"], e["reviewed_at"] = reported_by, now_iso()
    e["review_history"].append({"at": e["reviewed_at"], "by": reported_by, "action": "add-missed-event",
                                "fields": ["false_negative", "event_detected_correctly", "missed_information"]})
    record([e], root)
    append_correction(e, field="detected", system_value=False, reviewed_value=True,
                      reason=f"missed material event: {why_material}", module="event_detector", reviewer=reported_by,
                      root=root)
    return get_event(e["quality_event_id"], root)


# --------------------------------------------------------------------------- review / correct

FIELD_MODULE = {"priority": "priority_engine", "classification": "event_classifier", "detected": "event_detector",
                "guidance": "guidance_tracker", "kpi": "kpi_registry", "management": "management_diff",
                "promise": "promise_tracker", "thesis": "thesis_monitor", "valuation": "valuation_monitor",
                "monitoring": "monitoring_rules", "monthly": "monthly_review"}


def module_for_field(field: str) -> str:
    for k, m in FIELD_MODULE.items():
        if field.startswith(k):
            return m
    return BOOL_FIELDS.get(field) or "event_detector"


def append_correction(e: Dict[str, Any], *, field: str, system_value: Any, reviewed_value: Any, reason: str,
                      module: Optional[str] = None, reviewer: str = "human", root: Path = ROOT) -> Dict[str, Any]:
    if not reason or not reason.strip():
        raise QualityError("a correction needs a reason")
    check_hindsight(reason)
    module = module or module_for_field(field)
    if module not in MODULES:
        raise QualityError(f"module must be one of {MODULES}")
    c = {"correction_id": f"QC-{hashlib.sha1(f'{e['quality_event_id']}|{field}|{now_iso()}|{len(e['corrections'])}'.encode()).hexdigest()[:10]}",
         "quality_event_id": e["quality_event_id"], "event_id": e["event_id"], "module": module, "ticker": e["ticker"],
         "workflow": e["workflow"], "field": field, "system_value": system_value, "reviewed_value": reviewed_value,
         "before": system_value, "after": reviewed_value, "reason": reason, "reviewer": reviewer,
         "timestamp": now_iso(), "applied_to_rules": False}
    path = corrections_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:  # append-only: corrections never disappear
        fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    events = load_events(root)
    for x in events:
        if x["quality_event_id"] == e["quality_event_id"]:
            x["corrections"].append(c)
            x["human_review"]["manual_correction_required"] = True
            save_events(events, root)
            e.update(x)
    return c


def review(qid: str, fields: Dict[str, Any], reviewer: str = "human", reason: str = "",
           status: str = "reviewed", extraction_errors: Iterable[str] = (), root: Path = ROOT) -> Dict[str, Any]:
    """Record a human review of the relevant fields only. Disagreements on priority /
    classification become corrections (with reason) in corrections.jsonl."""
    if status not in REVIEW_STATUSES:
        raise QualityError(f"status must be one of {REVIEW_STATUSES}")
    events = load_events(root)
    e = next((x for x in events if x["quality_event_id"] == qid), None)
    if e is None:
        raise QualityError(f"unknown quality_event_id {qid}")
    for f in fields:
        if f in FORBIDDEN_FIELDS:
            raise HindsightBiasError(f"{f} is a return-outcome field; quality is graded on process, not returns")
    vals = {f: _coerce(f, v) for f, v in fields.items()}
    for t in (vals.get("notes"), vals.get("missed_information"), reason):
        if isinstance(t, str):
            check_hindsight(t)
    errs = []
    for spec in extraction_errors:
        mod, _, et = spec.partition(":")
        if mod not in MODULES or et not in EXTRACTION_ERROR_TYPES:
            raise QualityError(f"extraction error must be module:type with module in {MODULES} and type in "
                               f"{EXTRACTION_ERROR_TYPES}; got {spec!r}")
        errs.append({"module": mod, "error_type": et})
    so, hr = e["system_output"], e["human_review"]
    hr.update(vals)
    if errs:
        hr["extraction_errors"] = hr.get("extraction_errors", []) + errs
    # derived consistency (explicit, never a guess): a verdict fixes the boolean and vice versa
    v = hr.get("classification_verdict")
    if v in ("correct", "too_high", "too_low", "wrong_type") and "event_classification_correct" not in vals:
        hr["event_classification_correct"] = v == "correct"
    rp = hr.get("reviewed_priority")
    if rp in PRIORITIES and so.get("priority") in PRIORITIES and "priority_correct" not in vals:
        hr["priority_correct"] = rp == so.get("priority")
    if hr.get("priority_correct") is True and rp == UNKNOWN and so.get("priority") in PRIORITIES:
        hr["reviewed_priority"] = so["priority"]
    pending_corr = []
    if rp in PRIORITIES and so.get("priority") in PRIORITIES and rp != so["priority"]:
        pending_corr.append(("priority", so["priority"], rp, "priority_engine"))
    rc = hr.get("reviewed_classification")
    if rc in CLASSIFICATIONS and so.get("classification") in CLASSIFICATIONS and rc != so["classification"]:
        pending_corr.append(("classification", so["classification"], rc, "event_classifier"))
    for x in errs:
        pending_corr.append(("extraction", None, x["error_type"], x["module"]))
    pending_corr = [x for x in pending_corr if x[0] == "extraction"
                    or not any(c["field"] == x[0] and c["reviewed_value"] == x[2] for c in e["corrections"])]
    if pending_corr and not (reason or hr.get("notes")):
        raise QualityError("a disagreement with the system output needs --reason (or notes)")
    if hr.get("false_positive") is True and hr.get("event_detected_correctly") == UNKNOWN:
        hr["event_detected_correctly"] = False
    e["review_status"] = status
    if status == "pending":
        e["reviewed_by"] = e["reviewed_at"] = None
    else:
        e["reviewed_by"], e["reviewed_at"] = reviewer, now_iso()
    e["review_history"].append({"at": now_iso(), "by": reviewer, "action": "review", "status": status,
                                "fields": sorted(list(vals) + (["extraction_errors"] if errs else []))})
    save_events(events, root)
    for field, sv, rv, mod in pending_corr:
        append_correction(e, field=field, system_value=sv, reviewed_value=rv, reason=reason or hr.get("notes", ""),
                          module=mod, reviewer=reviewer, root=root)
    return get_event(qid, root)


def correct(qid: str, field: str, reviewed_value: Any, reason: str, module: Optional[str] = None,
            system_value: Any = None, reviewer: str = "human", root: Path = ROOT) -> Dict[str, Any]:
    e = get_event(qid, root)
    if system_value is None:
        system_value = e["system_output"].get(field)
    return append_correction(e, field=field, system_value=system_value, reviewed_value=reviewed_value, reason=reason,
                             module=module, reviewer=reviewer, root=root)


def list_events(root: Path = ROOT, status: Optional[str] = None, ticker: Optional[str] = None,
                requirement: Optional[str] = None) -> List[Dict[str, Any]]:
    out = []
    for e in load_events(root):
        if status and e["review_status"] != status:
            continue
        if ticker and e["ticker"] != ticker.upper():
            continue
        if requirement and e.get("review_requirement") != requirement:
            continue
        out.append(e)
    order = {"required": 0, "spot_check": 1, "sample": 2}
    return sorted(out, key=lambda e: (order.get(e.get("review_requirement"), 3), e["date"], e["ticker"]))
