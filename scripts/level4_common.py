#!/usr/bin/env python3
"""Shared helpers for the Level 4 research command center.

Level 4 sits on top of the Level 3 state in research/<TICKER>/ and never
replaces it: these helpers only read config (config/watchlist.yaml,
config/research-policy.yaml) and Level 3 state files, plus a small per-ticker
scan state (research/<TICKER>/monitoring/scan-state.json) used for incremental
checks (last_checked, last_filing, last_price_update, last_management_update).

Evidence quality (not a company score):
  HIGH   SEC filing / audited / official quantified guidance
  MEDIUM official IR presentation / earnings release (qualitative or non-GAAP)
  LOW    secondary source / semantic inference
LOW evidence is never treated as false; it only lowers confidence.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]

# Actions that the Level 4 engine may never emit (triggers only mean REASSESS).
FORBIDDEN_ACTIONS = ("BUY", "SELL", "ORDER", "EXECUTE", "SHORT", "COVER")
REASSESS = "REASSESS"


def read_yaml(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8")) or default


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")


def write_csv(path: Path, header: List[str], rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in header})


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def today(as_of: Optional[str] = None) -> str:
    return as_of or date.today().isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def days_between(a: Optional[str], b: Optional[str]) -> Optional[int]:
    """b - a in days for ISO dates (or datetimes); None when either is missing."""
    if not a or not b:
        return None
    try:
        return (date.fromisoformat(str(b)[:10]) - date.fromisoformat(str(a)[:10])).days
    except ValueError:
        return None


def company_dir(ticker: str, root: Path = ROOT) -> Path:
    return root / "research" / ticker.upper()


# --------------------------------------------------------------------------- config

def load_watchlist(root: Path = ROOT, include_disabled: bool = False) -> List[Dict[str, Any]]:
    """Watchlist entries; falls back to every company with a thesis when the file is absent."""
    doc = read_yaml(root / "config/watchlist.yaml", {}) or {}
    entries = []
    for e in doc.get("tickers") or []:
        if isinstance(e, str):
            e = {"ticker": e}
        e = dict(e)
        e["ticker"] = str(e["ticker"]).upper()
        e.setdefault("enabled", True)
        if e["enabled"] or include_disabled:
            entries.append(e)
    if not doc:
        entries = [{"ticker": p.parent.parent.name, "enabled": True}
                   for p in sorted((root / "research").glob("*/thesis/current.yaml"))]
    return entries


def watch_entry(ticker: str, root: Path = ROOT) -> Dict[str, Any]:
    for e in load_watchlist(root, include_disabled=True):
        if e["ticker"] == ticker.upper():
            return e
    return {"ticker": ticker.upper(), "enabled": True}


DEFAULT_POLICY: Dict[str, Any] = {
    "staleness": {"default": {"full_review_days": 100, "valuation_price_days": 7,
                              "thesis_evidence_days": 120, "management_update_days": 120},
                  "by_research_role": {}},
    "market": {"daily_move_pct": 8.0, "large_move_pct": 15.0, "volume_ratio": 2.5, "drawdown_pct": 25.0,
               "lookback_sessions": 252, "max_backfill_sessions": 20},
    "insider": {"routine_forms": ["4", "144"]},
    "priority": {"stale_days_multiplier_high": 1.5, "valuation_percentile_change": 20,
                 "expectation_gap_change": 0.03},
    "queue": {"archive_after_days": 90},
    "scan": {"first_scan_lookback_days": 45,
             "sec_forms": ["10-Q", "10-K", "8-K", "DEF 14A", "4", "144", "S-3", "S-3ASR", "S-1", "424B5",
                           "424B3", "424B2", "S-4", "425", "SC 13D", "SCHEDULE 13D"]},
}


def load_policy(root: Path = ROOT) -> Dict[str, Any]:
    doc = read_yaml(root / "config/research-policy.yaml", {}) or {}
    out = json.loads(json.dumps(DEFAULT_POLICY))
    for k, v in doc.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def staleness_limits(policy: Dict[str, Any], research_role: Optional[str]) -> Dict[str, Any]:
    st = policy.get("staleness") or {}
    limits = dict(st.get("default") or {})
    role = (research_role or "").lower()
    for key, over in (st.get("by_research_role") or {}).items():
        if key.lower() in role:
            limits.update(over or {})
    return limits


# --------------------------------------------------------------------------- scan state (incremental)

SCAN_STATE_FIELDS = ("last_checked", "last_filing", "last_filing_accession", "last_price_update",
                     "last_management_update")


def scan_state_path(ticker: str, root: Path = ROOT) -> Path:
    return company_dir(ticker, root) / "monitoring/scan-state.json"


def load_scan_state(ticker: str, root: Path = ROOT) -> Dict[str, Any]:
    st = read_json(scan_state_path(ticker, root), {}) or {}
    for k in SCAN_STATE_FIELDS:
        st.setdefault(k, None)
    st.setdefault("ticker", ticker.upper())
    return st


def save_scan_state(ticker: str, state: Dict[str, Any], root: Path = ROOT) -> None:
    write_json(scan_state_path(ticker, root), state)


# --------------------------------------------------------------------------- state readers

def thesis(ticker: str, root: Path = ROOT) -> Dict[str, Any]:
    return read_yaml(company_dir(ticker, root) / "thesis/current.yaml", {}) or {}


def prices(ticker: str, root: Path = ROOT) -> List[Dict[str, Any]]:
    """Closes sorted by date (duplicates: last row wins)."""
    by_date: Dict[str, Dict[str, Any]] = {}
    for r in read_csv(company_dir(ticker, root) / "market/prices.csv"):
        try:
            by_date[r["date"]] = {"date": r["date"], "close": float(r["close"]),
                                  "volume": float(r["volume"]) if r.get("volume") else None,
                                  "source": r.get("source", "")}
        except (KeyError, ValueError):
            continue
    return [by_date[d] for d in sorted(by_date)]


def latest_review_date(ticker: str, root: Path = ROOT) -> Optional[str]:
    """Latest non-retrospective research date: newest change / baseline report or snapshot."""
    base = company_dir(ticker, root)
    dates = []
    for p in (base / "reports").glob("*.md"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", p.name)
        if m and "dry-run" not in p.name:
            dates.append(m.group(1))
    for p in (base / "snapshots").glob("*.json"):
        snap = read_json(p, {}) or {}
        if not snap.get("retrospective"):
            dates.append(p.stem)
    return max(dates) if dates else None


def latest_full_review_date(ticker: str, root: Path = ROOT) -> Optional[str]:
    """Latest review that incorporated a new reporting period (not a price-only refresh)."""
    base = company_dir(ticker, root)
    best = None
    prev_q = None
    for p in sorted((base / "snapshots").glob("*.json")):
        snap = read_json(p, {}) or {}
        if snap.get("retrospective"):
            prev_q = (snap.get("financials") or {}).get("latest_quarter")
            continue
        q = (snap.get("financials") or {}).get("latest_quarter")
        if best is None or q != prev_q:
            best = p.stem
        prev_q = q
    th = thesis(ticker, root)
    analyst = None
    for c in (th.get("components") or {}).values():
        lu = str(c.get("last_updated") or "")
        if lu and (analyst is None or lu > analyst):
            analyst = lu
    cands = [d for d in (best, analyst) if d]
    return max(cands) if cands else latest_review_date(ticker, root)


# --------------------------------------------------------------------------- evidence quality

def evidence_quality(source_type: str = "", source: str = "", inferred: bool = False) -> str:
    """HIGH / MEDIUM / LOW from the kind of source (source_type first; the URL only when the
    type is empty). Never a truth verdict."""
    s = (source_type or source or "").lower()
    if s.startswith("market data") or "dated market source" in s:
        return "MEDIUM"  # a dated price is a fact, but it says nothing about fundamentals
    if inferred or "semantic" in s or "inference" in s or "keyword" in s:
        return "LOW"
    if any(w in s for w in ("secondary", "news", "aggregator", "yfinance", "blog", "estimate")):
        return "LOW"
    if any(w in s for w in ("10-q", "10-k", "sec xbrl", "sec ", "audited", "xbrl", "20-f", "proxy", "def 14a")):
        return "HIGH"
    if "guidance" in s and any(w in s for w in ("quantified", "range", "point")):
        return "HIGH"
    if any(w in s for w in ("earnings release", "press release", "presentation", "issuer", "8-k", "investor")):
        return "MEDIUM"
    return "LOW"


ORDER_FIELDS = ("required_workflow", "required_action", "alert_action", "meaning", "next_step", "order", "trade")


def assert_no_orders(obj: Any) -> None:
    """Raise if a workflow / alert field carries a trade instruction (Level 4 emits REASSESS only)."""
    def walk(o: Any) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ORDER_FIELDS and isinstance(v, str):
                    up = v.upper()
                    for w in FORBIDDEN_ACTIONS:
                        if re.search(rf"\b{w}\b", up) and not re.search(rf"\b(NOT|NEVER|NO)\b[^.]*\b{w}\b", up):
                            raise ValueError(f"forbidden trade instruction in {k}: {v}")
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
