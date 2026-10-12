#!/usr/bin/env python3
"""Compare valuation scenario assumptions with the company's own reported history.

Every Base / Bull (and Bear when present) assumption is set against history
from financials/history.json (build_fundamental_history.py):

  revenue growth : 3Y and 5Y revenue CAGR, latest 8 quarters YoY range,
                   latest 4 quarters (TTM) growth, median quarterly YoY
  margins        : gross, operating, FCF margin, SBC / revenue, capex / revenue
                   (latest FY, TTM, 3Y average, historical best / worst)
  dilution       : diluted share 3Y CAGR and latest YoY

Classification (per assumption, direction-aware):
  Below historical | Near historical | Above historical | Materially above historical
mapped to the plain-language reading conservative / reasonable / aggressive /
very aggressive. "Above" means more optimistic than history (e.g. a lower SBC
ratio or less dilution than history is also "above"). These are Calculations
from reported data plus an Interpretation; history does not cap the future.

Assumptions are read from valuation/assumptions.json `scenario_assumptions`
or valuation/latest.json `expectations` (internal_base / bull / bear).
Output: valuation/assumption-check.json and valuation/assumption-check.md.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_fundamental_history import _v, load_history  # noqa: E402

NEAR_PP = 3.0          # within 3 percentage points of a historical reference
MATERIAL_PP = 10.0     # more than 10 pp beyond the most favourable reference

# assumption key -> (history metric family, higher_is_optimistic)
ASSUMPTION_MAP = {
    "revenue_cagr_5y": ("revenue_growth", True),
    "revenue_cagr": ("revenue_growth", True),
    "gross_margin": ("gross_margin_pct", True),
    "operating_margin": ("operating_margin_pct", True),
    "operating_margin_y5": ("operating_margin_pct", True),
    "fcf_margin": ("fcf_margin_pct", True),
    "fcf_margin_y5": ("fcf_margin_pct", True),
    "sbc_pct_revenue": ("sbc_pct_revenue", False),
    "capex_pct_revenue": ("capex_pct_revenue", False),
    "diluted_share_growth": ("diluted_share_growth", False),
}
READING = {"Below historical": "conservative", "Near historical": "reasonable",
           "Above historical": "aggressive", "Materially above historical": "very aggressive"}


def _cagr(a: Optional[float], b: Optional[float], years: int) -> Optional[float]:
    if a is None or b is None or a <= 0 or b <= 0 or years <= 0:
        return None
    return round(((b / a) ** (1 / years) - 1) * 100, 2)


def _ttm(quarters: List[Dict[str, Any]], key: str, offset: int = 0) -> Optional[float]:
    q = quarters[len(quarters) - 4 - offset: len(quarters) - offset] if len(quarters) >= 4 + offset else []
    vals = [_v(r["metrics"], key) for r in q]
    return round(sum(vals), 4) if len(vals) == 4 and all(v is not None for v in vals) else None


def history_stats(history: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    annual = [r for r in history["annual"] if _v(r["metrics"], "revenue") is not None]
    quarters = history["quarters"]
    rev = [_v(r["metrics"], "revenue") for r in annual]
    out: Dict[str, Dict[str, Any]] = {}
    yoy8 = [_v(r["metrics"], "revenue_yoy_pct") for r in quarters[-8:]]
    yoy8 = [round(v, 2) for v in yoy8 if v is not None]
    ttm, ttm_prev = _ttm(quarters, "revenue"), _ttm(quarters, "revenue", 4)
    out["revenue_growth"] = {
        "cagr_3y_pct": _cagr(rev[-4], rev[-1], 3) if len(rev) >= 4 else None,
        "cagr_5y_pct": _cagr(rev[-6], rev[-1], 5) if len(rev) >= 6 else None,
        "latest_fy_growth_pct": _cagr(rev[-2], rev[-1], 1) if len(rev) >= 2 else None,
        "latest_8q_yoy_range_pct": [min(yoy8), max(yoy8)] if yoy8 else None,
        "latest_4q_ttm_growth_pct": round((ttm / ttm_prev - 1) * 100, 2) if ttm and ttm_prev else None,
        "median_quarterly_yoy_pct": round(statistics.median(yoy8), 2) if yoy8 else None,
        "basis": f"annual revenue {annual[0]['period'] if annual else '?'}..{annual[-1]['period'] if annual else '?'}; "
                 f"quarters {quarters[-8]['period'] if len(quarters) >= 8 else '?'}..{quarters[-1]['period'] if quarters else '?'}",
    }
    for key, num in (("gross_margin_pct", "gross_profit"), ("operating_margin_pct", "operating_income"),
                     ("fcf_margin_pct", "fcf"), ("sbc_pct_revenue", "sbc"), ("capex_pct_revenue", "capex")):
        series = [(r["period"], _v(r["metrics"], key)) for r in annual]
        vals = [v for _, v in series if v is not None]
        tn, tr = _ttm(quarters, num), _ttm(quarters, "revenue")
        out[key] = {
            "by_year": {p: (None if v is None else round(v, 2)) for p, v in series},
            "latest_fy_pct": round(vals[-1], 2) if vals else None,
            "ttm_pct": round(tn / tr * 100, 2) if tn is not None and tr else None,
            "avg_3y_pct": round(statistics.mean(vals[-3:]), 2) if len(vals) >= 3 else None,
            "best_pct": round(max(vals), 2) if vals else None,
            "worst_pct": round(min(vals), 2) if vals else None,
        }
    sh = [(r["period"], _v(r["metrics"], "diluted_shares")) for r in annual]
    shv = [v for _, v in sh if v is not None]
    out["diluted_share_growth"] = {
        "cagr_3y_pct": _cagr(shv[-4], shv[-1], 3) if len(shv) >= 4 else None,
        "latest_fy_yoy_pct": _cagr(shv[-2], shv[-1], 1) if len(shv) >= 2 else None,
        "latest_quarter_yoy_pct": next((round(_v(r["metrics"], "diluted_shares_yoy_pct"), 2) for r in reversed(quarters)
                                        if _v(r["metrics"], "diluted_shares_yoy_pct") is not None), None),
    }
    return out


def _refs(family: str, stats: Dict[str, Any]) -> Dict[str, Dict[str, Optional[float]]]:
    """Historical references split into long-run and recent groups."""
    s = stats[family]
    if family == "revenue_growth":
        return {"long_run": {"cagr_5y": s["cagr_5y_pct"], "cagr_3y": s["cagr_3y_pct"]},
                "recent": {"ttm_growth": s["latest_4q_ttm_growth_pct"], "median_8q_yoy": s["median_quarterly_yoy_pct"]}}
    if family == "diluted_share_growth":
        return {"long_run": {"cagr_3y": s["cagr_3y_pct"]},
                "recent": {"latest_fy_yoy": s["latest_fy_yoy_pct"], "latest_quarter_yoy": s["latest_quarter_yoy_pct"]}}
    return {"long_run": {"avg_3y": s["avg_3y_pct"]},
            "recent": {"ttm": s["ttm_pct"], "latest_fy": s["latest_fy_pct"]}}


def classify(assumption_pct: float, refs: Dict[str, Dict[str, Optional[float]]], higher_is_optimistic: bool) -> str:
    """Near = within long-run history; Above = beyond it but within recent trajectory (or < +10 pp);
    Materially above = beyond both. Direction-aware: lower SBC / dilution is the optimistic side."""
    sign = 1 if higher_is_optimistic else -1
    long = [sign * v for v in refs["long_run"].values() if v is not None]
    recent = [sign * v for v in refs["recent"].values() if v is not None]
    if not long and not recent:
        return "No history"
    long = long or recent
    a = sign * assumption_pct
    if a < min(long) - NEAR_PP:
        return "Below historical"
    if a <= max(long) + NEAR_PP:
        return "Near historical"
    if a <= max(long) + MATERIAL_PP or (recent and a <= max(recent) + NEAR_PP):
        return "Above historical"
    return "Materially above historical"


def _fmt(group: Dict[str, Optional[float]]) -> str:
    return ", ".join(f"{k} {v:.1f}%" for k, v in group.items() if v is not None) or "n/a"


def interpret(label: str, scenario: str, key: str, pct: float, refs: Dict[str, Dict[str, Optional[float]]],
              higher_is_optimistic: bool) -> str:
    sign = 1 if higher_is_optimistic else -1
    recent = [v for v in refs["recent"].values() if v is not None]
    within_recent = bool(recent) and sign * pct <= max(sign * v for v in recent) + NEAR_PP
    text = {"Below historical": "more conservative than long-run history",
            "Near historical": "in line with long-run history",
            "Above historical": "above long-run history" + (" but within recent trajectory" if within_recent
                                                            else ", not yet shown in recent results"),
            "Materially above historical": "materially beyond both long-run history and recent trajectory",
            "No history": "not comparable (no history)"}[label]
    return (f"{scenario} {key} {pct:.1f}% is {text} (long-run: {_fmt(refs['long_run'])}; "
            f"recent: {_fmt(refs['recent'])}) -> {label} / {READING.get(label, 'n/a')}.")


def load_assumptions(base: Path) -> Dict[str, Dict[str, float]]:
    a = json.loads((base / "valuation/assumptions.json").read_text()) if (base / "valuation/assumptions.json").exists() else {}
    if a.get("scenario_assumptions"):
        return a["scenario_assumptions"]
    exp = (json.loads((base / "valuation/latest.json").read_text()) if (base / "valuation/latest.json").exists()
           else {}).get("expectations") or {}
    out = {}
    for src, name in (("bear", "bear"), ("internal_base", "base"), ("bull", "bull")):
        if exp.get(src):
            out[name] = exp[src]
    return out


def check(history: Dict[str, Any], assumptions: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    stats = history_stats(history)
    rows = []
    for scenario, vals in assumptions.items():
        for key, val in vals.items():
            if key not in ASSUMPTION_MAP or val is None:
                continue
            family, up = ASSUMPTION_MAP[key]
            pct = float(val) * 100 if abs(float(val)) <= 1.5 else float(val)
            refs = _refs(family, stats)
            label = classify(pct, refs, up)
            rows.append({"scenario": scenario, "assumption": key, "value_pct": round(pct, 2),
                         "history_refs_pct": refs, "classification": label,
                         "reading": READING.get(label, "n/a"),
                         "interpretation": interpret(label, scenario, key, pct, refs, up),
                         "label": "Calculation (history) + Interpretation"})
    return {"as_of": history.get("as_of"), "history_stats": stats, "checks": rows,
            "caveat": "History is evidence, not a ceiling: a forward 5-year assumption can exceed history "
                      "if new evidence supports it. FCF history may include working-capital timing "
                      "(e.g. customer prepayments)."}


def render_md(ticker: str, result: Dict[str, Any]) -> str:
    s = result["history_stats"]["revenue_growth"]
    lines = [f"# {ticker} 假設 vs 歷史檢查（Assumption vs History）", "",
             f"營收歷史（Calculation）：3Y CAGR {s['cagr_3y_pct']}%、5Y CAGR {s['cagr_5y_pct']}%、"
             f"最近 FY 成長 {s['latest_fy_growth_pct']}%、TTM 成長 {s['latest_4q_ttm_growth_pct']}%、"
             f"最近 8 季 YoY 範圍 {s['latest_8q_yoy_range_pct']}、中位數 {s['median_quarterly_yoy_pct']}%。", "",
             "| 情境 | 假設 | 數值 | 分類 | 解讀 |", "|---|---|---|---|---|"]
    for r in result["checks"]:
        lines.append(f"| {r['scenario']} | {r['assumption']} | {r['value_pct']}% | {r['classification']}"
                     f"（{r['reading']}） | {r['interpretation']} |")
    lines += ["", "## 歷史比率（年度，%）", "", "| 指標 | " + " | ".join(
        result["history_stats"]["gross_margin_pct"]["by_year"]) + " | TTM |",
        "|---|" + "---|" * (len(result["history_stats"]["gross_margin_pct"]["by_year"]) + 1)]
    for k in ("gross_margin_pct", "operating_margin_pct", "fcf_margin_pct", "sbc_pct_revenue", "capex_pct_revenue"):
        st = result["history_stats"][k]
        lines.append(f"| {k} | " + " | ".join("n/a" if v is None else f"{v}" for v in st["by_year"].values())
                     + f" | {st['ttm_pct']} |")
    d = result["history_stats"]["diluted_share_growth"]
    lines += ["", f"稀釋股數：3Y CAGR {d['cagr_3y_pct']}%、最近 FY YoY {d['latest_fy_yoy_pct']}%、"
                  f"最近一季 YoY {d['latest_quarter_yoy_pct']}%。", "", f"> {result['caveat']}", ""]
    return "\n".join(lines)


def run(ticker: str, root: Path = ROOT, write: bool = True) -> Dict[str, Any]:
    base = root / "research" / ticker.upper()
    history = load_history(ticker, root)
    if not history:
        raise ValueError("financials/history.json missing; run build_fundamental_history.py first")
    result = check(history, load_assumptions(base))
    if write:
        (base / "valuation").mkdir(parents=True, exist_ok=True)
        (base / "valuation/assumption-check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (base / "valuation/assumption-check.md").write_text(render_md(ticker.upper(), result), encoding="utf-8")
    return result


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    res = run(args.ticker, args.root, not args.no_write)
    for r in res["checks"]:
        print(r["interpretation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
