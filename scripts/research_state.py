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
except ImportError:  # pragma: no cover - environment guard
    sys.exit("PyYAML is required: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import recommendation  # noqa: E402  (reuse validated catch-up / reverse-DCF helpers)

THESIS_STATUSES = ("supported", "improving", "uncertain", "weakening", "invalidated")
IMPORTANCE = ("high", "medium", "low")
PROMISE_STATUSES = ("pending", "delivered", "partially_delivered", "missed", "superseded")
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
    "event_date", "event_type", "description", "source", "gap_pct", "day_return_pct",
    "volume_ratio_20d", "return_m1_p1_pct", "drift_p2_p20_pct", "max_drawdown_20d_pct",
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


def check_rules(ticker: str, root: Path = ROOT) -> List[Dict[str, Any]]:
    base = company_dir(ticker, root)
    rules = _read_yaml(base / "monitoring/rules.yaml") or {}
    metrics = (_read_json(base / "financials/latest.json", {}) or {}).get("metrics", {})
    return evaluate_rules(rules, metrics)


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


def status(ticker: str, root: Path = ROOT) -> str:
    base = company_dir(ticker, root)
    thesis = _read_yaml(base / "thesis/current.yaml") or {}
    latest = _read_json(base / "valuation/latest.json", {}) or {}
    rules = check_rules(ticker, root)
    lines = [f"# {ticker.upper()} research status (local state, no network)", ""]
    lines.append(f"As of: {thesis.get('as_of')} | Action: {thesis.get('action')} | "
                 f"Valuation confidence: {thesis.get('valuation_confidence')} | "
                 f"Role: {thesis.get('research_role')}")
    lines += ["", "## Thesis components"]
    for name, c in (thesis.get("components") or {}).items():
        lines.append(f"- {name} [{c.get('importance')}]: {c.get('status')} — next check: {c.get('next_check')}")
    lines += ["", "## Valuation", f"Price: {latest.get('price')} ({latest.get('price_date')})"]
    for m, v in (latest.get("methods") or {}).items():
        lines.append(f"- {m}: bear {v.get('bear')} / base {v.get('base')} / bull {v.get('bull')}")
    pos = (latest.get("valuation_map") or {}).get("current_position")
    if pos:
        lines.append(f"Valuation-map position: {pos}")
    rd = latest.get("reverse_dcf") or {}
    lines.append(f"Reverse DCF: {rd.get('status', 'quantified') if rd else 'not recorded'}"
                 + (f"; implied growth {rd['implied_growth']:.1%}" if rd.get("implied_growth") else ""))
    gap = latest.get("expectation_gap") or {}
    if gap.get("interpretation"):
        lines.append(f"Expectation gap: {gap['interpretation']}")
    lines += ["", "## Monitoring rules (reassess, not trade)"]
    for r in rules:
        lines.append(f"- {r['rule']}: {r['state']} (value {r['value']}, warning {r['warning']})")
    market = ((_read_yaml(base / "monitoring/rules.yaml") or {}).get("monitoring") or {}).get("market") or {}
    if market.get("reassess_price"):
        lines.append(f"- reassess at prices: {market['reassess_price']} — {market.get('meaning', 'reassess')}")
    return "\n".join(lines)


def _fmt_change(prev: Any, cur: Any) -> str:
    return f"{prev} → {cur}" if prev != cur else f"{cur} (unchanged)"


def change_report(ticker: str, root: Path = ROOT, dry_run_note: str = "") -> str:
    base = company_dir(ticker, root)
    t_hist = _read_json(base / "thesis/history.json", []) or []
    v_hist = read_valuation_history(base / "valuation/history.csv")
    promises = _read_json(base / "management/promises.json", []) or []
    thesis = _read_yaml(base / "thesis/current.yaml") or {}
    latest = _read_json(base / "valuation/latest.json", {}) or {}
    cur = t_hist[-1] if t_hist else thesis_snapshot(thesis)
    prev = t_hist[-2] if len(t_hist) >= 2 else None
    lines = [f"# What Changed Since Last Review — {ticker.upper()}", ""]
    if dry_run_note:
        lines += [f"> {dry_run_note}", ""]
    if prev is None:
        lines += [f"Baseline state as of {cur.get('as_of')}; there is no prior research state to compare.",
                  "Every item below is the starting point for the next update.", ""]
    pos, neg, same = [], [], []
    order = {s: i for i, s in enumerate(THESIS_STATUSES)}
    for name, c in cur.get("components", {}).items():
        p = (prev or {}).get("components", {}).get(name)
        if not p:
            same.append(f"{name}: {c['status']} (new or baseline)")
        elif order[c["status"]] < order[p["status"]]:
            pos.append(f"{name}: {p['status']} → {c['status']}")
        elif order[c["status"]] > order[p["status"]]:
            neg.append(f"{name}: {p['status']} → {c['status']}")
        else:
            same.append(f"{name}: {c['status']}")
    for title, items in (("Positive", pos), ("Negative", neg), ("Unchanged", same)):
        lines += [f"## {title}"] + ([f"- {i}" for i in items] or ["- none"]) + [""]
    lines += ["## Management wording changes",
              f"- See management/changes.md ({len(_read_json(base / 'management/statements.json', []) or [])} statements recorded)", ""]
    counts: Dict[str, int] = {}
    for p in promises:
        counts[p.get("status", "?")] = counts.get(p.get("status", "?"), 0) + 1
    lines += ["## Promises", "- " + (", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
                                     or "none recorded"), ""]
    statuses = [c["status"] for c in cur.get("components", {}).values()]
    worst = max(statuses, key=lambda s: order[s]) if statuses else "n/a"
    lines += ["## Thesis", f"- weakest component status: {worst}", ""]
    dates = sorted({r["as_of"] for r in v_hist})
    def _vals(d):
        return {r["method"]: f"{r['bear']}/{r['base']}/{r['bull']}" for r in v_hist if r["as_of"] == d}
    if len(dates) >= 2:
        lines += ["## Valuation (bear/base/bull)",
                  *[f"- {m}: {_fmt_change(_vals(dates[-2]).get(m), v)}" for m, v in _vals(dates[-1]).items()], ""]
    elif dates:
        lines += ["## Valuation (bear/base/bull)",
                  *[f"- {m}: {v} (baseline)" for m, v in _vals(dates[-1]).items()], ""]
    gap_hist = latest.get("expectation_gap") or {}
    lines += ["## Expectation gap", f"- {gap_hist.get('interpretation', 'not quantified')}"
              + (f" Direction: {gap_hist.get('direction')}." if gap_hist.get("direction") else ""), ""]
    lines += ["## Action", f"- {_fmt_change((prev or {}).get('action', cur.get('action')), cur.get('action'))}", "",
              "## Confidence",
              f"- {_fmt_change((prev or {}).get('valuation_confidence', cur.get('valuation_confidence')), cur.get('valuation_confidence'))}",
              "", "## Next catalysts"]
    lines += [f"- {c}" for c in thesis.get("next_catalysts", [])] or ["- none recorded"]
    lines += ["", "Price movement alone is not treated as evidence that fundamentals changed."]
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
    for name in ("status", "record-valuation", "check-rules", "catch-up", "expectation-gap"):
        sub.add_parser(name).add_argument("ticker")
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
