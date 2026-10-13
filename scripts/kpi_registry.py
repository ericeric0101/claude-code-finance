#!/usr/bin/env python3
"""KPI registry (Level 4): common + sector + company KPIs with source, period, unit and confidence.

Hierarchy (later layers override earlier ones key by key):
  1. config/kpi-registry/common.yaml          common financial KPIs
  2. config/kpi-registry/<sector>.yaml         sector KPIs (sector from config/watchlist.yaml
                                               or the company override)
  3. research/<TICKER>/config/kpis.yaml        company-specific KPIs, disabled KPIs,
                                               manual company-defined values, guidance
                                               metric definitions

Rules
- Not every company has every KPI. Missing data is written as `unavailable`, never 0.
- Company-defined metrics keep their original name and definition (`original_name`,
  `definition`). RPO, backlog and ARR are separate concepts: a KPI whose `concept` is
  `backlog` can never be filled from the `rpo` metric (and vice versa).
- Units are validated: a source whose unit differs from the registry unit is rejected
  and reported, not converted silently.
- Values come from local Level 3 state only (financials/history.json,
  management/reported-kpis.json, raw/companyfacts.json); no network.

Output: research/<TICKER>/financials/kpi-history.csv
        (date, period, kpi, value, unit, source, source_type, confidence, notes)
        research/<TICKER>/financials/kpi-coverage.json

Usage:
  python3 scripts/kpi_registry.py resolve PL        # print merged registry
  python3 scripts/kpi_registry.py build PL          # write kpi-history.csv + coverage
  python3 scripts/kpi_registry.py build --all
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import level4_common as l4  # noqa: E402

REGISTRY_DIR = Path("config/kpi-registry")
HEADER = ["date", "period", "kpi", "value", "unit", "source", "source_type", "confidence", "notes"]
ALLOWED_UNITS = {"USD millions", "USD", "%", "count", "days", "months", "text", "date", "ratio",
                 "millions of shares", "USD per share"}
# Concepts that must never be substituted for each other.
METRIC_CONCEPT = {"rpo": "rpo", "backlog": "backlog", "arr": "arr", "bookings": "bookings", "capex": "capex_accounting"}
SUPPORTED_SECTORS = ("software", "semiconductors", "space", "biotech", "banks", "consumer")


def metric_unit(metric: str) -> str:
    """Unit of a financials/history.json metric (history units: USD millions; shares in millions)."""
    if metric.endswith("_pct") or metric.endswith("_pct_revenue"):
        return "%"
    if metric in ("diluted_shares", "basic_shares"):
        return "millions of shares"
    if metric.startswith("eps"):
        return "USD per share"
    if metric in ("units", "subscribers"):
        return "count"
    return "USD millions"


# --------------------------------------------------------------------------- registry

def load_layer(name: str, root: Path = ROOT) -> Dict[str, Any]:
    doc = l4.read_yaml(root / REGISTRY_DIR / f"{name}.yaml", {}) or {}
    return doc.get("kpis") or {}


def company_override(ticker: str, root: Path = ROOT) -> Dict[str, Any]:
    return l4.read_yaml(l4.company_dir(ticker, root) / "config/kpis.yaml", {}) or {}


def sector_of(ticker: str, root: Path = ROOT) -> Optional[str]:
    ov = company_override(ticker, root)
    return ov.get("sector") or l4.watch_entry(ticker, root).get("sector")


def resolve(ticker: str, root: Path = ROOT, sector: Optional[str] = None) -> Dict[str, Any]:
    """Merged registry: {kpi: definition + layer + required}. Validation problems in `errors`."""
    sector = sector or sector_of(ticker, root)
    merged: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []
    layers = [("common", load_layer("common", root))]
    if sector:
        layer = load_layer(sector, root)
        if not layer:
            errors.append(f"sector layer '{sector}' not found in {REGISTRY_DIR}")
        layers.append((sector, layer))
    ov = company_override(ticker, root)
    layers.append(("company", ov.get("kpis") or {}))
    for lname, kpis in layers:
        for key, d in kpis.items():
            cur = dict(merged.get(key, {}))
            cur.update(d or {})
            cur["layer"] = lname if key not in merged else f"{merged[key]['layer']}+{lname}"
            cur.setdefault("required", False)
            cur.setdefault("sources", [])
            merged[key] = cur
    for key in ov.get("disable") or []:
        merged.pop(key, None)
    for key, d in merged.items():
        if d.get("unit") not in ALLOWED_UNITS:
            errors.append(f"{key}: unit '{d.get('unit')}' not in allowed units")
        concept = d.get("concept")
        for s in d.get("sources") or []:
            m = s.get("metric")
            if m in METRIC_CONCEPT and concept and METRIC_CONCEPT[m] != concept:
                errors.append(f"{key}: concept '{concept}' cannot be sourced from metric '{m}' "
                              f"({METRIC_CONCEPT[m]}); concepts are not interchangeable")
    return {"ticker": ticker.upper(), "sector": sector, "kpis": merged, "errors": errors,
            "guidance_metrics": ov.get("guidance_metrics") or {},
            "override_draft_auto": bool(ov.get("draft_auto")), "override_review_required": bool(ov.get("review_required"))}


# --------------------------------------------------------------------------- extraction

def _hist_rows(kpi: str, d: Dict[str, Any], src: Dict[str, Any], history: Dict[str, Any]
               ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    metric = src["metric"]
    unit = metric_unit(metric)
    if unit != d.get("unit"):
        return [], f"{kpi}: source metric {metric} unit '{unit}' != registry unit '{d.get('unit')}'"
    concept = d.get("concept")
    if metric in METRIC_CONCEPT and concept and METRIC_CONCEPT[metric] != concept:
        return [], f"{kpi}: concept mismatch ({concept} vs {METRIC_CONCEPT[metric]})"
    rows = []
    for kind, recs in (("quarter", history.get("quarters") or []), ("annual", history.get("annual") or [])):
        for r in recs:
            p = (r.get("metrics") or {}).get(metric)
            v = p.get("value") if isinstance(p, dict) else p
            if v is None:
                continue
            notes, conf = [], "high"
            if isinstance(p, dict):
                if p.get("calculation"):
                    notes.append(f"Calculation: {p['calculation']}")
                if p.get("derived"):
                    notes.append(f"derived: {p['derived']}")
                    conf = "medium"
                if p.get("fallback_tag") or p.get("tag_fallback"):
                    notes.append("fallback tag")
                    conf = "medium"
                if p.get("accn"):
                    srcs = f"SEC {p.get('form', '')} {p.get('accn')} ({p.get('tag', metric)})"
                else:
                    srcs = f"financials/history.json ({metric})"
            else:
                srcs = f"financials/history.json ({metric})"
            rows.append({"date": r.get("period_end") or r.get("end") or "", "period": r.get("period"),
                         "kpi": kpi, "value": round(float(v), 4), "unit": unit, "source": srcs,
                         "source_type": "SEC XBRL (10-Q / 10-K)", "confidence": conf,
                         "notes": "; ".join(notes)})
    return rows, None


def _reported_rows(kpi: str, d: Dict[str, Any], src: Dict[str, Any], reported: Dict[str, Any]) -> List[Dict[str, Any]]:
    key = src["key"]
    rows = []
    for period, rec in reported.items():
        vals = rec.get("values") or {}
        k = key if period.startswith("Q") else f"fy_{key}"
        if k not in vals:
            continue
        rows.append({"date": rec.get("date", ""), "period": period, "kpi": kpi, "value": vals[k],
                     "unit": d.get("unit"), "source": rec.get("source", ""),
                     "source_type": "issuer earnings release (8-K Item 2.02, non-GAAP)", "confidence": "medium",
                     "notes": f"company-defined: {d.get('original_name') or d.get('name')}; date = release date"})
    return rows


def _xbrl_rows(kpi: str, d: Dict[str, Any], src: Dict[str, Any], facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    tag = src["tag"]
    unit_key = src.get("unit", "USD")
    scale = float(src.get("scale", 1.0))
    entries = (((facts.get("facts") or {}).get("us-gaap") or {}).get(tag) or {}).get("units", {}).get(unit_key) or []
    best: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for e in entries:
        if not str(e.get("form", "")).startswith(("10-K", "10-Q")) or not e.get("start"):
            continue
        days = l4.days_between(e["start"], e["end"]) or 0
        if not (80 <= days <= 100 or 350 <= days <= 380):
            continue
        k = (e["start"], e["end"])
        if k not in best or e.get("filed", "") > best[k].get("filed", ""):
            best[k] = e
    rows = []
    for (s, e_), f in sorted(best.items(), key=lambda kv: kv[0][1])[-24:]:
        kind = "FY" if (l4.days_between(s, e_) or 0) > 300 else "quarter"
        rows.append({"date": e_, "period": f"{kind} ending {e_}", "kpi": kpi, "value": round(f["val"] * scale, 4),
                     "unit": d.get("unit"), "source": f"SEC {f.get('form')} {f.get('accn')} ({tag})",
                     "source_type": "SEC XBRL (10-Q / 10-K)", "confidence": "high", "notes": ""})
    return rows


def manual_rows(ov: Dict[str, Any], registry: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    rows, errors = [], []
    for v in ov.get("values") or []:
        k = v.get("kpi")
        d = registry.get(k)
        if d is None:
            errors.append(f"manual value for unknown KPI '{k}'")
            continue
        if v.get("unit") and v["unit"] != d.get("unit"):
            errors.append(f"{k}: manual unit '{v['unit']}' != registry unit '{d.get('unit')}' (not written)")
            continue
        if v.get("value") in (None, ""):
            errors.append(f"{k}: manual value missing (use status unavailable instead of 0)")
            continue
        notes = [f"original name: {v.get('original_name') or d.get('original_name') or d.get('name')}"]
        if v.get("definition") or d.get("definition"):
            notes.append(f"definition: {v.get('definition') or d.get('definition')}")
        if v.get("notes"):
            notes.append(v["notes"])
        st = v.get("source_type", "analyst-curated from primary filing")
        rows.append({"date": v.get("date", ""), "period": v.get("period", ""), "kpi": k, "value": v["value"],
                     "unit": d.get("unit"), "source": v.get("source", ""), "source_type": st,
                     "confidence": v.get("confidence") or l4.evidence_quality(st, v.get("source", "")).lower(),
                     "notes": "; ".join(notes)})
    return rows, errors


def build(ticker: str, root: Path = ROOT, as_of: Optional[str] = None, write: bool = True) -> Dict[str, Any]:
    t = ticker.upper()
    base = l4.company_dir(t, root)
    reg = resolve(t, root)
    history = l4.read_json(base / "financials/history.json", {}) or {}
    reported = l4.read_json(base / "management/reported-kpis.json", {}) or {}
    facts = None
    rows: List[Dict[str, Any]] = []
    errors = list(reg["errors"])
    ov = company_override(t, root)
    man, merr = manual_rows(ov, reg["kpis"])
    errors += merr
    coverage: Dict[str, Any] = {}
    for kpi, d in reg["kpis"].items():
        got: List[Dict[str, Any]] = []
        used = None
        for src in d.get("sources") or []:
            typ = src.get("type")
            if typ == "sec_history":
                r, err = _hist_rows(kpi, d, src, history)
                if err:
                    errors.append(err)
            elif typ == "reported_kpis":
                r = _reported_rows(kpi, d, src, reported)
            elif typ == "xbrl_tag":
                if facts is None:
                    facts = l4.read_json(base / "raw/companyfacts.json", {}) or {}
                r = _xbrl_rows(kpi, d, src, facts)
            else:
                r = []
            if r:
                got, used = r, typ
                break
        m = [x for x in man if x["kpi"] == kpi]
        got = got + m
        if m and not used:
            used = "manual"
        latest = max(got, key=lambda x: str(x["date"])) if got else None
        coverage[kpi] = {
            "name": d.get("name"), "layer": d["layer"], "required": bool(d.get("required")),
            "unit": d.get("unit"), "definition": d.get("definition"), "concept": d.get("concept"),
            "status": "available" if got else "unavailable", "source_type": used,
            "observations": len(got), "latest_period": latest["period"] if latest else None,
            "latest_value": latest["value"] if latest else None,
            "latest_confidence": latest["confidence"] if latest else None,
        }
        if got:
            rows += got
        else:
            rows.append({"date": as_of or date.today().isoformat(), "period": "latest", "kpi": kpi,
                         "value": "unavailable", "unit": d.get("unit"), "source": "", "source_type": "",
                         "confidence": "n/a",
                         "notes": ("required KPI not disclosed in local state" if d.get("required")
                                   else "optional KPI not disclosed in local state") + "; not filled with 0"})
    rows.sort(key=lambda r: (r["kpi"], str(r["date"]), str(r["period"])))
    req = [k for k, c in coverage.items() if c["required"]]
    out = {
        "ticker": t, "as_of": as_of or date.today().isoformat(), "sector": reg["sector"],
        "layers": ["common"] + ([reg["sector"]] if reg["sector"] else []) + (["company"] if ov else []),
        "required_available": sorted(k for k in req if coverage[k]["status"] == "available"),
        "required_unavailable": sorted(k for k in req if coverage[k]["status"] == "unavailable"),
        "optional_available": sorted(k for k, c in coverage.items() if not c["required"] and c["status"] == "available"),
        "optional_unavailable": sorted(k for k, c in coverage.items() if not c["required"] and c["status"] == "unavailable"),
        "coverage": coverage, "errors": errors,
        "draft_auto": reg["override_draft_auto"], "review_required": reg["override_review_required"] or bool(errors),
        "note": "Coverage only; not a company score. 'unavailable' means not disclosed in local state, not zero.",
    }
    if write:
        l4.write_csv(base / "financials/kpi-history.csv", HEADER, rows)
        l4.write_json(base / "financials/kpi-coverage.json", out)
    out["rows"] = rows
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("resolve"); p.add_argument("ticker")
    p = sub.add_parser("build"); p.add_argument("ticker", nargs="?"); p.add_argument("--all", action="store_true")
    p.add_argument("--as-of")
    args = ap.parse_args(argv)
    if args.cmd == "resolve":
        reg = resolve(args.ticker)
        for k, d in reg["kpis"].items():
            print(f"{k:28s} {d['layer']:18s} {'required' if d.get('required') else 'optional':9s} {d.get('unit')}")
        for e in reg["errors"]:
            print("ERROR:", e)
        return 0
    tickers = [e["ticker"] for e in l4.load_watchlist()] if args.all else [args.ticker]
    for t in tickers:
        out = build(t, as_of=args.as_of)
        print(f"{t}: sector={out['sector']} required available {len(out['required_available'])}, "
              f"unavailable {out['required_unavailable']}; optional available {out['optional_available']}; "
              f"errors {len(out['errors'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
