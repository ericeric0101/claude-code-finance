#!/usr/bin/env python3
"""Persistent company research state for the US equity research OS.

Local-only: no command here calls a network API. Valuation arithmetic is
reused from scripts/recommendation.py (and, upstream, stock-analysis
valuation.py); this module only stores, compares and reports research state.

Commands:
  init TICKER        create the research/<TICKER>/ state skeleton (never overwrites)
  status TICKER      thesis, valuation, expectation gap and monitoring summary
  list               companies with a thesis/current.yaml
  snapshot TICKER    upsert thesis/current.yaml into thesis/history.json by as_of
  record-valuation TICKER  upsert valuation/latest.json into valuation/history.csv
  change-report TICKER     "What Changed Since Last Review" from stored history
  check-rules TICKER       evaluate monitoring/rules.yaml against financials/latest.json
  catch-up TICKER          earnings / FCF / revenue catch-up scenarios (not forecasts)
  expectation-gap TICKER   market-implied vs internal base / bull, with direction vs prior
  record-gap TICKER        upsert valuation/expectation-gap-history.csv
  refresh-financials TICKER  merge history-derived metrics into financials/latest.json
  snapshot-state TICKER    write snapshots/<as_of>.json (all domains) for the state diff
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import operator
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - e.g. the finance-skill uv env used for price fetches
    yaml = None


def _require_yaml() -> None:
    if yaml is None:
        sys.exit("PyYAML is required for thesis / monitoring state: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import recommendation  # noqa: E402  (reuse validated catch-up / reverse-DCF helpers)

THESIS_STATUSES = ("supported", "improving", "uncertain", "weakening", "invalidated")
# Explicit semantics for every status transition. Enum order carries no meaning.
# "neutral" covers moves that are slightly weaker or stronger but not a thesis
# deterioration (e.g. supported -> improving: evidence still positive, less settled).
_POS, _NEU, _NEG = "positive", "neutral", "negative"
THESIS_TRANSITIONS = {
    ("uncertain", "improving"): _POS, ("uncertain", "supported"): _POS,
    ("improving", "supported"): _POS,
    ("weakening", "uncertain"): _POS, ("weakening", "improving"): _POS, ("weakening", "supported"): _POS,
    ("invalidated", "weakening"): _POS, ("invalidated", "uncertain"): _POS,
    ("invalidated", "improving"): _POS, ("invalidated", "supported"): _POS,
    ("supported", "improving"): _NEU,
    ("supported", "uncertain"): _NEG, ("improving", "uncertain"): _NEG,
    ("supported", "weakening"): _NEG, ("improving", "weakening"): _NEG, ("uncertain", "weakening"): _NEG,
    ("supported", "invalidated"): _NEG, ("improving", "invalidated"): _NEG,
    ("uncertain", "invalidated"): _NEG, ("weakening", "invalidated"): _NEG,
}
TRANSITION_NOTES = {("supported", "improving"): "slightly less settled evidence; not automatically negative"}


def classify_transition(prev: Optional[str], cur: str) -> str:
    """positive / neutral / negative / unchanged / new for a thesis component status change."""
    if prev is None:
        return "new"
    if prev == cur:
        return "unchanged"
    if (prev, cur) not in THESIS_TRANSITIONS:
        raise ValueError(f"unknown thesis transition {prev} -> {cur}")
    return THESIS_TRANSITIONS[(prev, cur)]

IMPORTANCE = ("high", "medium", "low")
PROMISE_STATUSES = ("pending", "delivered", "partially_delivered", "missed", "superseded",
                    "delayed", "not_evaluable")  # Level 4 adds delayed / not_evaluable (guidance_tracker.py)
VALUATION_HISTORY_FIELDS = (
    "as_of", "price", "price_date", "method", "bear", "base", "bull",
    "reverse_dcf_implied_growth", "valuation_confidence", "action",
    "map_position", "source",
)
STATE_DIRS = (
    "evidence/filings", "evidence/earnings", "evidence/presentations",
    "evidence/announcements", "evidence/external", "management", "financials",
    "thesis", "valuation", "market", "monitoring", "reports",
)
FORBIDDEN_DECISION_KEYS = ("buy_range", "entry_price", "target_buy_price", "required_entry_price")


def company_dir(ticker: str, root: Path = ROOT) -> Path:
    return root / "research" / ticker.upper()


def _read_yaml(path: Path) -> Any:
    _require_yaml()
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None


def _read_json(path: Path, default: Any = None) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------

def _skeleton(ticker: str, company: str, cik: Optional[str]) -> Dict[str, Any]:
    t = ticker.upper()
    return {
        "company-profile.md": f"# {company or t} ({t})\n\nCIK: {cik or 'not verified'}\n\n"
                              "Status: initialized; no research conclusions recorded yet.\n",
        "management/statements.json": [],
        "management/promises.json": [],
        "management/changes.md": f"# {t} management wording changes\n\nNo comparison yet.\n",
        "financials/latest.json": {"ticker": t, "as_of": None, "metrics": {}},
        "financials/historical.csv": "period,period_end,metric,value,unit,basis,classification,source\n",
        "thesis/current.yaml": {"ticker": t, "as_of": None, "action": None,
                                "valuation_confidence": None, "components": {}},
        "thesis/history.json": [],
        "thesis/invalidation-rules.yaml": {"ticker": t, "rules": []},
        "valuation/assumptions.json": {"ticker": t, "methods": {}},
        "valuation/latest.json": {"ticker": t, "as_of": None, "methods": {}},
        "valuation/history.csv": ",".join(VALUATION_HISTORY_FIELDS) + "\n",
        "market/prices.csv": "date,open,high,low,close,volume,source,retrieved_at\n",
        "market/event-reactions.csv": "",
        "monitoring/rules.yaml": {"ticker": t, "monitoring": {"fundamental": {}, "market": {}}},
    }


def init_company(ticker: str, company: str = "", cik: Optional[str] = None,
                 root: Path = ROOT) -> Dict[str, List[str]]:
    """Create missing state files only; existing research is never overwritten."""
    _require_yaml()
    base = company_dir(ticker, root)
    created: List[str] = []
    kept: List[str] = []
    for d in STATE_DIRS:
        (base / d).mkdir(parents=True, exist_ok=True)
    for rel, content in _skeleton(ticker, company, cik).items():
        path = base / rel
        if path.exists():
            kept.append(rel)
            continue
        if rel.endswith(".yaml"):
            path.write_text(yaml.safe_dump(content, sort_keys=False, allow_unicode=True), encoding="utf-8")
        elif rel.endswith(".json"):
            _write_json(path, content)
        else:
            path.write_text(content if rel != "market/event-reactions.csv"
                            else ",".join(EVENT_REACTION_HEADER) + "\n", encoding="utf-8")
        created.append(rel)
    return {"created": created, "kept": kept}


EVENT_REACTION_HEADER = (
    "event_date", "event_type", "description", "source", "t0", "gap_pct", "day_return_pct",
    "volume_ratio_20d", "return_m1_p1_pct", "drift_p2_p20_pct", "max_drawdown_20d_pct",
    "benchmark", "return_5d_pct", "return_20d_pct", "abnormal_1d_pct", "abnormal_5d_pct", "abnormal_20d_pct",
    "abnormal_sector_1d_pct", "abnormal_sector_5d_pct", "abnormal_sector_20d_pct",
    "observation", "interpretation",
)


# --------------------------------------------------------------------------
# thesis
# --------------------------------------------------------------------------

def validate_thesis(doc: Dict[str, Any]) -> List[str]:
    errors = []
    for name, comp in (doc.get("components") or {}).items():
        if comp.get("importance") not in IMPORTANCE:
            errors.append(f"{name}: importance must be one of {IMPORTANCE}")
        if comp.get("status") not in THESIS_STATUSES:
            errors.append(f"{name}: status must be one of {THESIS_STATUSES}")
        for field in ("evidence", "last_updated", "next_check", "invalidation_condition"):
            if not comp.get(field):
                errors.append(f"{name}: missing {field}")
    return errors


def thesis_snapshot(doc: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    return {
        "as_of": str(doc.get("as_of")),
        "action": doc.get("action"),
        "valuation_confidence": doc.get("valuation_confidence"),
        "components": {k: {"status": v.get("status"), "importance": v.get("importance")}
                       for k, v in (doc.get("components") or {}).items()},
        "source_report": doc.get("source_report"),
        "note": note,
    }


def upsert_history(history: List[Dict[str, Any]], entry: Dict[str, Any],
                   key: str = "as_of") -> List[Dict[str, Any]]:
    """Replace an entry with the same key, otherwise append; never drops others."""
    out = [copy.deepcopy(h) for h in history if h.get(key) != entry.get(key)]
    out.append(copy.deepcopy(entry))
    return sorted(out, key=lambda h: str(h.get(key)))


def snapshot_thesis(ticker: str, note: str = "", root: Path = ROOT) -> Dict[str, Any]:
    base = company_dir(ticker, root)
    doc = _read_yaml(base / "thesis/current.yaml")
    if not doc or not doc.get("as_of"):
        raise ValueError("thesis/current.yaml needs an as_of date before snapshotting")
    errors = validate_thesis(doc)
    if errors:
        raise ValueError("; ".join(errors))
    path = base / "thesis/history.json"
    history = upsert_history(_read_json(path, []), thesis_snapshot(doc, note))
    _write_json(path, history)
    return history[-1]


# --------------------------------------------------------------------------
# valuation history and expectation gap
# --------------------------------------------------------------------------

def valuation_rows(latest: Dict[str, Any]) -> List[Dict[str, str]]:
    rows = []
    implied = (latest.get("reverse_dcf") or {}).get("implied_growth")
    for method, vals in (latest.get("methods") or {}).items():
        rows.append({
            "as_of": str(latest.get("as_of")), "price": str(latest.get("price")),
            "price_date": str(latest.get("price_date")), "method": method,
            "bear": str(vals.get("bear", "")), "base": str(vals.get("base", "")),
            "bull": str(vals.get("bull", "")),
            "reverse_dcf_implied_growth": "" if implied is None else str(implied),
            "valuation_confidence": str(latest.get("valuation_confidence", "")),
            "action": str(latest.get("action", "")),
            "map_position": str((latest.get("valuation_map") or {}).get("current_position", "")),
            "source": str(latest.get("source_report", "")),
        })
    return rows


def read_valuation_history(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def upsert_valuation_history(existing: List[Dict[str, str]],
                             new_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Upsert by (as_of, method); prior dates and methods are retained."""
    keys = {(r["as_of"], r["method"]) for r in new_rows}
    out = [r for r in existing if (r.get("as_of"), r.get("method")) not in keys] + list(new_rows)
    return sorted(out, key=lambda r: (r["as_of"], r["method"]))


def record_valuation(ticker: str, root: Path = ROOT) -> List[Dict[str, str]]:
    base = company_dir(ticker, root)
    latest = _read_json(base / "valuation/latest.json")
    if not latest or not latest.get("as_of") or not latest.get("methods"):
        raise ValueError("valuation/latest.json needs as_of and methods")
    bad = [k for k in FORBIDDEN_DECISION_KEYS if k in json.dumps(latest)]
    if bad:
        raise ValueError(f"valuation state must not contain mechanical entry fields: {bad}")
    path = base / "valuation/history.csv"
    rows = upsert_valuation_history(read_valuation_history(path), valuation_rows(latest))
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=VALUATION_HISTORY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def expectation_gap(market_implied: Dict[str, float], base: Dict[str, float],
                    bull: Dict[str, float]) -> Dict[str, Any]:
    """Per-metric comparison of market-implied vs internal base / bull. No composite score."""
    metrics = {}
    for key, implied in market_implied.items():
        if key not in base or key not in bull or implied is None:
            continue
        metrics[key] = {
            "market_implied": implied, "internal_base": base[key], "bull": bull[key],
            "gap_vs_base": round(float(implied) - float(base[key]), 4),
            "position": recommendation.reverse_dcf_interpretation(
                float(implied), float(base[key]), float(bull[key])),
        }
    return metrics


def gap_direction(previous: Optional[Dict[str, Any]], current: Dict[str, Any],
                  tolerance: float = 0.005) -> Dict[str, str]:
    """widening / stable / narrowing per metric, based on |market - base| change."""
    out = {}
    for key, cur in current.items():
        prev = (previous or {}).get(key)
        if not prev:
            out[key] = "no prior state"
            continue
        delta = abs(cur["gap_vs_base"]) - abs(prev["gap_vs_base"])
        out[key] = "stable" if abs(delta) <= tolerance else ("widening" if delta > 0 else "narrowing")
    return out


def expectation_gap_for(latest: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the gap from latest.json `expectations`; compare with stored prior metrics."""
    exp = latest.get("expectations") or {}
    if not exp.get("market_implied"):
        return {"status": "not quantified",
                "reason": exp.get("reason", "no market-implied assumptions recorded")}
    metrics = expectation_gap(exp["market_implied"], exp.get("internal_base", {}), exp.get("bull", {}))
    prior = (latest.get("expectation_gap") or {}).get("previous_metrics")
    return {"metrics": metrics, "direction": gap_direction(prior, metrics),
            "label": "Assumptions solved from price; not forecasts"}


GAP_HISTORY_FIELDS = ("date", "metric", "market_implied", "base", "bull", "gap_vs_base", "gap_vs_bull",
                      "direction", "confidence", "price", "source")


def read_gap_history(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def gap_history_rows(latest: Dict[str, Any], prior_rows: List[Dict[str, str]],
                     tolerance: float = 0.005) -> List[Dict[str, str]]:
    """Rows for latest.json's date; direction compares |market - base| with the most
    recent earlier row of the same metric (widening / stable / narrowing)."""
    exp = latest.get("expectations") or {}
    if not exp.get("market_implied"):
        return []
    metrics = expectation_gap(exp["market_implied"], exp.get("internal_base", {}), exp.get("bull", {}))
    date = str(latest.get("as_of"))
    rows = []
    for key, m in metrics.items():
        earlier = [r for r in prior_rows if r["metric"] == key and r["date"] < date and r.get("gap_vs_base")]
        if earlier:
            prev = max(earlier, key=lambda r: r["date"])
            delta = abs(m["gap_vs_base"]) - abs(float(prev["gap_vs_base"]))
            direction = "stable" if abs(delta) <= tolerance else ("widening" if delta > 0 else "narrowing")
        else:
            direction = "no prior state"
        rows.append({"date": date, "metric": key, "market_implied": str(m["market_implied"]),
                     "base": str(m["internal_base"]), "bull": str(m["bull"]),
                     "gap_vs_base": str(m["gap_vs_base"]),
                     "gap_vs_bull": str(round(float(m["market_implied"]) - float(m["bull"]), 4)),
                     "direction": direction,
                     "confidence": str(latest.get("valuation_confidence", "")),
                     "price": str(latest.get("price", "")), "source": "valuation/latest.json expectations"})
    return rows


def record_expectation_gap(ticker: str, root: Path = ROOT) -> List[Dict[str, str]]:
    """Upsert today's expectation-gap rows into valuation/expectation-gap-history.csv by (date, metric)."""
    base = company_dir(ticker, root)
    latest = _read_json(base / "valuation/latest.json", {}) or {}
    path = base / "valuation/expectation-gap-history.csv"
    existing = read_gap_history(path)
    new = gap_history_rows(latest, existing)
    keys = {(r["date"], r["metric"]) for r in new}
    rows = sorted([r for r in existing if (r["date"], r["metric"]) not in keys] + new,
                  key=lambda r: (r["date"], r["metric"]))
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=GAP_HISTORY_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return rows


# --------------------------------------------------------------------------
# monitoring rules
# --------------------------------------------------------------------------

_OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}


def parse_condition(text: str):
    m = re.fullmatch(r"\s*(<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)\s*(%?)\s*", str(text))
    if not m:
        raise ValueError(f"unsupported condition: {text!r}")
    return m.group(1), float(m.group(2))


def evaluate_rules(rules: Dict[str, Any], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fundamental rules -> triggered / not_triggered / missing_data. Never an order."""
    results = []
    for name, rule in ((rules.get("monitoring") or {}).get("fundamental") or {}).items():
        metric = rule.get("metric", name)
        op, threshold = parse_condition(rule["warning"])
        value = (metrics.get(metric) or {}).get("value") if isinstance(metrics.get(metric), dict) \
            else metrics.get(metric)
        if value is None:
            state = "missing_data"
        else:
            state = "triggered" if _OPS[op](float(value), threshold) else "not_triggered"
        results.append({"rule": name, "metric": metric, "warning": rule["warning"],
                        "value": value, "state": state, "meaning": rule.get("meaning", "reassess")})
    return results


def latest_close(base: Path) -> Optional[Dict[str, Any]]:
    """Latest stored daily close (completed session) from market/prices.csv."""
    path = base / "market/prices.csv"
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("close")]
    if not rows:
        return None
    last = max(rows, key=lambda r: r["date"])
    return {"date": last["date"], "close": float(last["close"]), "source": last.get("source", "")}


def evaluate_market_rules(market: Dict[str, Any], price: Optional[float],
                          reference_price: Optional[float]) -> List[Dict[str, Any]]:
    """Valuation-map reassessment levels. A level crossed between the last reviewed
    price and the latest close is `triggered` (= REASSESS), never a trade."""
    levels = sorted(float(x) for x in (market or {}).get("reassess_price") or [])
    out = []
    for lvl in levels:
        if price is None:
            state = "missing_data"
        elif reference_price is not None and (min(price, reference_price) < lvl <= max(price, reference_price)):
            state = "triggered"
        else:
            state = "not_triggered"
        side = None if price is None else ("above" if price >= lvl else "below")
        out.append({"rule": f"reassess_price_{lvl:g}", "type": "market", "level": lvl, "value": price,
                    "reference_price": reference_price, "price_side": side, "state": state,
                    "action": "REASSESS" if state == "triggered" else "none",
                    "meaning": market.get("meaning", "reassess thesis and valuation; not an order")})
    return out


def evaluate_invalidation(rules: Dict[str, Any], metrics: Dict[str, Any],
                          quarter_series: Optional[Dict[str, List[float]]] = None) -> List[Dict[str, Any]]:
    """thesis/invalidation-rules.yaml. A rule with machine `checks` ({metric, warning,
    consecutive_quarters?}) is evaluated; all checks must fire (or any, with logic: any). Rules without checks
    keep the analyst's recorded state and are marked manual."""
    out = []
    for r in (rules or {}).get("rules") or []:
        checks = r.get("checks") or []
        if not checks:
            out.append({"rule": r["id"], "type": "invalidation", "state": r.get("state", "missing_data"),
                        "evaluation": "manual", "thesis_component": r.get("thesis_component"),
                        "action": "REASSESS" if r.get("state") == "triggered" else "none"})
            continue
        states, values = [], {}
        for c in checks:
            op, threshold = parse_condition(c["warning"])
            n = int(c.get("consecutive_quarters", 1))
            if n > 1:
                series = (quarter_series or {}).get(c["metric"]) or []
                vals = series[-n:]
                values[c["metric"]] = vals
                if len(vals) < n or any(v is None for v in vals):
                    states.append("missing_data")
                else:
                    states.append("triggered" if all(_OPS[op](float(v), threshold) for v in vals) else "not_triggered")
            else:
                m = metrics.get(c["metric"])
                v = m.get("value") if isinstance(m, dict) else m
                values[c["metric"]] = v
                states.append("missing_data" if v is None else
                              ("triggered" if _OPS[op](float(v), threshold) else "not_triggered"))
        if r.get("logic", "all") == "any":
            state = ("triggered" if "triggered" in states else
                     "missing_data" if "missing_data" in states else "not_triggered")
        else:
            state = ("triggered" if all(x == "triggered" for x in states) else
                     "missing_data" if "missing_data" in states and "not_triggered" not in states else "not_triggered")
        out.append({"rule": r["id"], "type": "invalidation", "state": state, "evaluation": "automatic",
                    "values": values, "thesis_component": r.get("thesis_component"),
                    "action": "REASSESS" if state == "triggered" else "none",
                    "meaning": "reassess the thesis component; not a sell signal"})
    return out


# Metrics refreshed from financials/history.json (SEC-derived, latest reported quarter / TTM).
HISTORY_METRICS = {
    "revenue_growth_yoy_pct": ("q", "revenue_yoy_pct"),
    "q2_revenue_growth_yoy_pct": None,  # legacy single-period key; left as recorded
    "quarterly_revenue_growth_yoy_pct": ("q", "revenue_yoy_pct"),
    "gaap_gross_margin_pct": ("q", "gross_margin_pct"),
    "quarterly_gross_margin_pct": ("q", "gross_margin_pct"),
    "operating_margin_pct": ("q", "operating_margin_pct"),
    "rpo_yoy_pct": ("q", "rpo_yoy_pct"),
    "diluted_shares_yoy_pct": ("q", "diluted_shares_yoy_pct"),
    "capex_pct_revenue": ("ttm_ratio", ("capex", "revenue")),
    "sbc_pct_revenue": ("ttm_ratio", ("sbc", "revenue")),
    "fcf_ttm": ("ttm", "fcf"),
    "revenue_ttm": ("ttm", "revenue"),
    "rpo": ("q", "rpo"),
    "cash_and_investments": ("q", "cash_and_investments"),
    "debt": ("q", "debt"),
}


def _hv(m: Dict[str, Any], k: str) -> Optional[float]:
    x = m.get(k)
    return x.get("value") if isinstance(x, dict) else None


def history_metrics(history: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Latest-quarter and TTM metrics from the SEC history, each with period and provenance."""
    qs = [q for q in history.get("quarters", []) if _hv(q["metrics"], "revenue") is not None]
    if not qs:
        return {}
    last, out = qs[-1], {}
    src = "financials/history.json (SEC companyfacts; build_fundamental_history.py)"
    for key, spec in HISTORY_METRICS.items():
        if spec is None:
            continue
        kind, arg = spec
        if kind == "q":
            v, period = _hv(last["metrics"], arg), last["period"]
        elif kind == "ttm":
            vals = [_hv(q["metrics"], arg) for q in qs[-4:]]
            v = sum(vals) if len(vals) == 4 and None not in vals else None
            period = f"TTM to {last['period']}"
        else:
            num = [_hv(q["metrics"], arg[0]) for q in qs[-4:]]
            den = [_hv(q["metrics"], arg[1]) for q in qs[-4:]]
            v = (sum(num) / sum(den) * 100 if len(num) == 4 and None not in num and None not in den and sum(den)
                 else None)
            period = f"TTM to {last['period']}"
        out[key] = {"value": None if v is None else round(v, 4), "period": period,
                    "unit": "%" if key.endswith("_pct") else "USD millions",
                    "classification": "Calculation" if kind != "q" or key.endswith("_pct") else "Fact",
                    "source": src}
    for a in history.get("annual", []):
        rev = _hv(a["metrics"], "revenue")
        if rev is not None:
            out[f"{a['period'].lower()}_revenue_reported"] = {
                "value": round(rev, 4), "period": a["period"], "unit": "USD millions",
                "classification": "Fact", "source": src}
    return out


def quarter_series(history: Dict[str, Any]) -> Dict[str, List[Optional[float]]]:
    qs = [q for q in history.get("quarters", []) if _hv(q["metrics"], "revenue") is not None]
    keys = {"gaap_gross_margin_pct": "gross_margin_pct", "operating_margin_pct": "operating_margin_pct",
            "revenue_growth_yoy_pct": "revenue_yoy_pct", "rpo_yoy_pct": "rpo_yoy_pct",
            "diluted_shares_yoy_pct": "diluted_shares_yoy_pct"}
    return {k: [_hv(q["metrics"], v) for q in qs] for k, v in keys.items()}


def refresh_latest_financials(ticker: str, root: Path = ROOT) -> Dict[str, Any]:
    """Merge history-derived metrics into financials/latest.json. Hand-entered metrics
    with other keys are kept; a history metric replaces a stored value only when its
    period is a newer reported quarter (or the stored value is missing)."""
    base = company_dir(ticker, root)
    history = _read_json(base / "financials/history.json")
    path = base / "financials/latest.json"
    latest = _read_json(path, {"ticker": ticker.upper(), "metrics": {}}) or {"metrics": {}}
    if not history:
        return latest
    hm = history_metrics(history)
    metrics = latest.setdefault("metrics", {})
    for k, v in hm.items():
        old = metrics.get(k)
        if v["value"] is None and isinstance(old, dict) and old.get("value") is not None:
            continue
        if isinstance(old, dict) and old.get("value") is not None:
            old = {**old}
            old_period = old.get("period", "")
            if old_period != v["period"]:
                v = {**v, "previous_value": old.get("value"), "previous_period": old_period}
        metrics[k] = v
    qs = [q for q in history["quarters"] if _hv(q["metrics"], "revenue") is not None]
    if qs:
        latest["latest_reported_period"] = f"{qs[-1]['period']} (ended {qs[-1]['period_end']})"
        latest["history_refreshed_from"] = "financials/history.json"
    _write_json(path, latest)
    return latest


def check_rules(ticker: str, root: Path = ROOT, reference_price: Optional[float] = None) -> List[Dict[str, Any]]:
    """Fundamental + market (price reassessment) + thesis invalidation rules.
    Every triggered rule means REASSESS; none produces BUY / SELL."""
    base = company_dir(ticker, root)
    rules = _read_yaml(base / "monitoring/rules.yaml") or {}
    metrics = (_read_json(base / "financials/latest.json", {}) or {}).get("metrics", {})
    out = [{**r, "type": "fundamental", "action": "REASSESS" if r["state"] == "triggered" else "none"}
           for r in evaluate_rules(rules, metrics)]
    close = latest_close(base)
    latest = _read_json(base / "valuation/latest.json", {}) or {}
    ref = reference_price if reference_price is not None else latest.get("price")
    out += evaluate_market_rules((rules.get("monitoring") or {}).get("market") or {},
                                 close["close"] if close else None, ref)
    history = _read_json(base / "financials/history.json")
    out += evaluate_invalidation(_read_yaml(base / "thesis/invalidation-rules.yaml") or {}, metrics,
                                 quarter_series(history) if history else None)
    return out


# --------------------------------------------------------------------------
# catch-up
# --------------------------------------------------------------------------

def catch_up(latest: Dict[str, Any]) -> Dict[str, Any]:
    """Scenario tables reusing recommendation.py; labelled scenarios, not forecasts."""
    cu = latest.get("catch_up") or {}
    price = latest.get("price")
    years = cu.get("years", (1, 2, 3))
    out: Dict[str, Any] = {"label": "Scenario analysis, not forecasts"}
    if cu.get("eps"):
        out["earnings"] = recommendation.earnings_catch_up(
            float(price), float(cu["eps"]), cu.get("eps_growth_rates", (0.10, 0.15, 0.20)), years)
    if cu.get("fcf_per_share"):
        rows = recommendation.earnings_catch_up(
            float(price), float(cu["fcf_per_share"]), cu.get("fcf_growth_rates", (0.10, 0.15, 0.20)), years)
        out["fcf"] = [{"annual_fcf_growth_pct": r["annual_eps_growth_pct"], "years": r["years"],
                       "future_fcf_per_share": r["future_eps"], "static_price_p_fcf": r["static_price_pe"],
                       "price_held_flat": r["price_held_flat"]} for r in rows]
    if cu.get("ev") and cu.get("revenue"):
        out["revenue"] = recommendation.revenue_catch_up(
            float(cu["ev"]), float(cu["revenue"]), cu.get("revenue_growth_rates", (0.10, 0.20, 0.30)), years)
        out["dilution_caveat"] = ("EV held flat; excludes future financing, SBC and ATM dilution, "
                                  "so per-share outcomes can be worse than the EV/sales path implies.")
    return out


# --------------------------------------------------------------------------
# status / change report
# --------------------------------------------------------------------------

def tracked_companies(root: Path = ROOT) -> List[str]:
    return sorted(p.parent.parent.name for p in (root / "research").glob("*/thesis/current.yaml"))


def latest_market_lines(base: Path, state_price: Any) -> List[str]:
    """Latest stored close and any intraday quote, compared with the state's price."""
    out = []
    prices = base / "market/prices.csv"
    if prices.exists():
        with prices.open(newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("close")]
        if rows:
            last = max(rows, key=lambda r: r["date"])
            line = f"Latest stored close: {float(last['close']):.2f} ({last['date']}, {last['source']})"
            if state_price:
                line += f"; {float(last['close']) / float(state_price) - 1:+.1%} vs state price"
            out.append(line)
    quote = _read_json(base / "market/latest-quote.json")
    if quote:
        out.append(f"Latest quote: {quote['price']:.2f} ({quote['status']}, {quote['as_of_et']} ET)")
    if out:
        out.append("Refresh before analysis: uv run --project .claude/skills/finance-skill/scripts "
                   "python scripts/price_reaction.py fetch TICKER")
    return out


def latest_change_date(base: Path) -> Optional[str]:
    dates = []
    for p in (base / "reports").glob("*.md"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", p.name)
        if m:
            dates.append(m.group(1))
    for p in (base / "snapshots").glob("*.json"):
        dates.append(p.stem)
    return max(dates) if dates else None


def status(ticker: str, root: Path = ROOT) -> str:
    base = company_dir(ticker, root)
    thesis = _read_yaml(base / "thesis/current.yaml") or {}
    latest = _read_json(base / "valuation/latest.json", {}) or {}
    rules = check_rules(ticker, root)
    comps = thesis.get("components") or {}
    counts: Dict[str, int] = {}
    for c in comps.values():
        counts[c.get("status")] = counts.get(c.get("status"), 0) + 1
    lines = [f"# {ticker.upper()} research status (local state, no network)", ""]
    lines += ["## Current action",
              f"Action: {thesis.get('action')} | Valuation confidence: {thesis.get('valuation_confidence')} | "
              f"Role: {thesis.get('research_role')} | Thesis as of: {thesis.get('as_of')}"
              + (" | RETROSPECTIVE" if thesis.get("retrospective") else ""),
              f"Latest change date: {latest_change_date(base) or 'none recorded'}", ""]
    lines += ["## Thesis summary",
              (thesis.get("summary") or "").strip() or "(no summary)",
              "Status counts: " + (", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=str)) or "none")]
    for name, c in comps.items():
        lines.append(f"- {name} [{c.get('importance')}]: {c.get('status')} — next check: {c.get('next_check')}")
    lines += ["", "## Valuation summary", f"State price: {latest.get('price')} ({latest.get('price_date')})"]
    lines += latest_market_lines(base, latest.get("price"))
    for m, v in (latest.get("methods") or {}).items():
        lines.append(f"- {m}: bear {v.get('bear')} / base {v.get('base')} / bull {v.get('bull')}")
    pos = (latest.get("valuation_map") or {}).get("current_position")
    if pos:
        lines.append(f"Valuation-map position: {pos}")
    rd = latest.get("reverse_dcf") or {}
    lines.append(f"Reverse DCF: {rd.get('status', 'quantified') if rd else 'not recorded'}"
                 + (f"; implied growth {rd['implied_growth']:.1%}" if rd.get("implied_growth") else ""))
    pct = _read_json(base / "valuation/historical-percentiles.json")
    if pct:
        for mult, p in (pct.get("percentiles") or {}).items():
            lines.append(f"Historical {mult}: current {p.get('current')} | 1Y pct {p.get('1y')} | "
                         f"3Y pct {p.get('3y')} | since listing {p.get('since_listing')}")
    lines += ["", "## Expectation gap"]
    gap = latest.get("expectation_gap") or {}
    hist = read_gap_history(base / "valuation/expectation-gap-history.csv")
    if hist:
        for r in [r for r in hist if r["date"] == max(h["date"] for h in hist)]:
            lines.append(f"- {r['metric']}: market {r['market_implied']} vs base {r['base']} / bull {r['bull']} "
                         f"(gap vs base {r['gap_vs_base']}; {r['direction']})")
    if gap.get("interpretation"):
        lines.append(f"Interpretation: {gap['interpretation']}")
    if not hist and not gap:
        lines.append("- not quantified")
    lines += ["", "## Monitoring rules (REASSESS only; never BUY / SELL)"]
    for r in rules:
        if r["type"] == "market":
            lines.append(f"- [market] {r['rule']}: {r['state']} (latest close {r['value']}, last reviewed "
                         f"{r['reference_price']}, price {r['price_side']} level)")
        elif r["type"] == "invalidation":
            lines.append(f"- [invalidation] {r['rule']}: {r['state']} ({r['evaluation']}) → {r.get('thesis_component')}")
        else:
            lines.append(f"- [fundamental] {r['rule']}: {r['state']} (value {r['value']}, warning {r['warning']})")
    trig = [r["rule"] for r in rules if r["state"] == "triggered"]
    lines.append(f"Triggered → REASSESS: {', '.join(trig) if trig else 'none'}")
    lines += ["", "## Next catalysts"] + ([f"- {c}" for c in thesis.get("next_catalysts") or []] or ["- none recorded"])
    return "\n".join(lines)


def _fmt_change(prev: Any, cur: Any) -> str:
    return f"{prev} → {cur}" if prev != cur else f"{cur}（未變）"


def change_report(ticker: str, root: Path = ROOT, dry_run_note: str = "") -> str:
    """Multi-domain diff of the two latest state snapshots (state_diff.py). With fewer
    than two snapshots it falls back to thesis / valuation history only."""
    import state_diff
    snaps = state_diff.list_snapshots(ticker, root)
    if len(snaps) >= 2:
        return state_diff.render_report(ticker, state_diff.diff_states(snaps[-2], snaps[-1]), snaps[-1], dry_run_note)
    return _legacy_change_report(ticker, root, dry_run_note)


def _legacy_change_report(ticker: str, root: Path = ROOT, dry_run_note: str = "") -> str:
    base = company_dir(ticker, root)
    t_hist = _read_json(base / "thesis/history.json", []) or []
    v_hist = read_valuation_history(base / "valuation/history.csv")
    promises = _read_json(base / "management/promises.json", []) or []
    thesis = _read_yaml(base / "thesis/current.yaml") or {}
    latest = _read_json(base / "valuation/latest.json", {}) or {}
    cur = t_hist[-1] if t_hist else thesis_snapshot(thesis)
    prev = t_hist[-2] if len(t_hist) >= 2 else None
    lines = [f"# What Changed Since Last Review — {ticker.upper()}｜自上次檢視以來的變化", ""]
    if dry_run_note:
        lines += [f"> {dry_run_note}", ""]
    if prev is None:
        lines += [f"基準狀態日期為 {cur.get('as_of')}；沒有先前的研究狀態可供比較。",
                  "以下各項皆為下次更新的比較起點。", ""]
    pos, neg, same = [], [], []
    order = {s: i for i, s in enumerate(THESIS_STATUSES)}  # severity, used only for "weakest component"
    for name, c in cur.get("components", {}).items():
        p = (prev or {}).get("components", {}).get(name)
        kind = classify_transition(p["status"] if p else None, c["status"])
        if kind == "new":
            same.append(f"{name}: {c['status']}（新增或基準）")
        elif kind == "positive":
            pos.append(f"{name}: {p['status']} → {c['status']}")
        elif kind == "negative":
            neg.append(f"{name}: {p['status']} → {c['status']}")
        elif kind == "neutral":
            same.append(f"{name}: {p['status']} → {c['status']}（中性：{TRANSITION_NOTES.get((p['status'], c['status']), '')}）")
        else:
            same.append(f"{name}: {c['status']}")
    for title, items in (("Positive 正面變化", pos), ("Negative 負面變化", neg), ("Unchanged 未變化", same)):
        lines += [f"## {title}"] + ([f"- {i}" for i in items] or ["- 無"]) + [""]
    lines += ["## Management wording changes 管理層措辭變化",
              f"- 詳見 management/changes.md（已記錄 {len(_read_json(base / 'management/statements.json', []) or [])} 則陳述）", ""]
    counts: Dict[str, int] = {}
    for p in promises:
        counts[p.get("status", "?")] = counts.get(p.get("status", "?"), 0) + 1
    lines += ["## Promises 管理層承諾", "- " + (", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
                                     or "尚無紀錄"), ""]
    statuses = [c["status"] for c in cur.get("components", {}).values()]
    worst = max(statuses, key=lambda s: order[s]) if statuses else "n/a"
    lines += ["## Thesis 投資論點", f"- 最弱論點元件狀態：{worst}", ""]
    dates = sorted({r["as_of"] for r in v_hist})
    def _vals(d):
        return {r["method"]: f"{r['bear']}/{r['base']}/{r['bull']}" for r in v_hist if r["as_of"] == d}
    if len(dates) >= 2:
        lines += ["## Valuation (bear/base/bull) 估值（悲觀/基準/樂觀）",
                  *[f"- {m}: {_fmt_change(_vals(dates[-2]).get(m), v)}" for m, v in _vals(dates[-1]).items()], ""]
    elif dates:
        lines += ["## Valuation (bear/base/bull) 估值（悲觀/基準/樂觀）",
                  *[f"- {m}: {v}（基準）" for m, v in _vals(dates[-1]).items()], ""]
    gap_hist = latest.get("expectation_gap") or {}
    lines += ["## Expectation gap 預期落差", f"- {gap_hist.get('interpretation', '尚未量化')}"
              + (f" 方向：{gap_hist.get('direction')}。" if gap_hist.get("direction") else ""), ""]
    lines += ["## Action 研究分類", f"- {_fmt_change((prev or {}).get('action', cur.get('action')), cur.get('action'))}", "",
              "## Confidence 估值信心",
              f"- {_fmt_change((prev or {}).get('valuation_confidence', cur.get('valuation_confidence')), cur.get('valuation_confidence'))}",
              "", "## Next catalysts 下一個催化劑"]
    lines += [f"- {c}" for c in thesis.get("next_catalysts", [])] or ["- 尚無紀錄"]
    lines += ["", "僅有股價變動不視為基本面已改變的證據。"]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("ticker"); p.add_argument("--company", default="")
    p.add_argument("--cik")
    for name in ("status", "record-valuation", "check-rules", "catch-up", "expectation-gap",
                 "record-gap", "refresh-financials"):
        sub.add_parser(name).add_argument("ticker")
    p = sub.add_parser("snapshot-state"); p.add_argument("ticker"); p.add_argument("--as-of")
    p.add_argument("--note", default="")
    p = sub.add_parser("snapshot"); p.add_argument("ticker"); p.add_argument("--note", default="")
    p = sub.add_parser("change-report"); p.add_argument("ticker")
    p.add_argument("--dry-run-note", default=""); p.add_argument("--out", type=Path)
    sub.add_parser("list")
    args = parser.parse_args(argv)
    root = args.root
    try:
        if args.cmd == "init":
            print(json.dumps(init_company(args.ticker, args.company, args.cik, root), indent=2))
        elif args.cmd == "status":
            print(status(args.ticker, root))
        elif args.cmd == "list":
            print("\n".join(tracked_companies(root)))
        elif args.cmd == "snapshot":
            print(json.dumps(snapshot_thesis(args.ticker, args.note, root), indent=2))
        elif args.cmd == "record-valuation":
            print(f"{len(record_valuation(args.ticker, root))} valuation history rows")
        elif args.cmd == "check-rules":
            print(json.dumps(check_rules(args.ticker, root), indent=2))
        elif args.cmd == "catch-up":
            print(json.dumps(catch_up(_read_json(company_dir(args.ticker, root) / "valuation/latest.json", {})), indent=2))
        elif args.cmd == "expectation-gap":
            print(json.dumps(expectation_gap_for(_read_json(company_dir(args.ticker, root) / "valuation/latest.json", {})), indent=2))
        elif args.cmd == "record-gap":
            print(f"{len(record_expectation_gap(args.ticker, root))} expectation-gap history rows")
        elif args.cmd == "refresh-financials":
            print(json.dumps(refresh_latest_financials(args.ticker, root).get("latest_reported_period")))
        elif args.cmd == "snapshot-state":
            import state_diff
            snap = state_diff.build_snapshot(args.ticker, root, args.as_of, note=args.note)
            print(state_diff.save_snapshot(args.ticker, snap, root))
        elif args.cmd == "change-report":
            text = change_report(args.ticker, root, args.dry_run_note)
            if args.out:
                args.out.write_text(text, encoding="utf-8")
            print(text)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
