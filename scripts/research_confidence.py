#!/usr/bin/env python3
"""Explainable company-level research confidence (Level 4). Not a company score.

Components (each graded strong / adequate / weak with a reason in words):
  financial_history     financials/coverage.json (>= 5 fiscal years, >= 8 quarters)
  management_history    quarters with management statements; guidance records
  kpi_coverage          required KPIs available (kpi-coverage.json); company-defined KPIs
  valuation_agreement   number of valuation methods and spread of their base values;
                        reverse DCF quantified or not; draft_auto valuation
  evidence_quality      thesis evidence lines labelled Fact vs Interpretation / auto-draft
  unresolved_promises   pending + not_evaluable promises vs resolved
  stale_data            stale_research.py severity
overall: low when two or more components are weak or the thesis is draft_auto; high only
when no component is weak and most are strong; otherwise medium. No percentages.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import level4_common as l4  # noqa: E402


def assess(ticker: str, root: Path = ROOT, stale: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    t = ticker.upper()
    base = l4.company_dir(t, root)
    comp: Dict[str, Dict[str, str]] = {}
    cov = l4.read_json(base / "financials/coverage.json", {}) or {}
    if cov.get("meets_5y") and cov.get("meets_8q"):
        comp["financial_history"] = {"grade": "strong", "reason": f"strong financial history ({len(cov.get('annual_periods', []))} FY, "
                                                                  f"{len(cov.get('quarter_periods', []))} quarters from SEC filings)"}
    elif cov:
        comp["financial_history"] = {"grade": "adequate", "reason": "partial financial history (< 5 FY or < 8 quarters)"}
    else:
        comp["financial_history"] = {"grade": "weak", "reason": "no structured financial history"}
    stm = l4.read_json(base / "management/statements.json", []) or []
    gd = l4.read_json(base / "management/guidance.json", []) or []
    nq = len({s.get("period") for s in stm if s.get("period")})
    if nq >= 6 and gd:
        comp["management_history"] = {"grade": "strong", "reason": f"management history over {nq} periods with {len(gd)} guidance records"}
    elif nq >= 4:
        comp["management_history"] = {"grade": "adequate", "reason": f"management statements over {nq} periods; "
                                                                     + ("limited guidance history" if len(gd) < 8 else f"{len(gd)} guidance records")}
    else:
        comp["management_history"] = {"grade": "weak", "reason": f"limited management history ({nq} periods)"}
    kc = l4.read_json(base / "financials/kpi-coverage.json", {}) or {}
    if kc:
        miss = kc.get("required_unavailable") or []
        company = [k for k, c in (kc.get("coverage") or {}).items() if "company" in c.get("layer", "") and c["status"] == "available"]
        grade = "strong" if not miss and company else "adequate" if len(miss) <= 2 else "weak"
        comp["kpi_coverage"] = {"grade": grade, "reason": ("all required KPIs available" if not miss else
                                                          f"required KPIs unavailable: {', '.join(miss)}")
                                + (f"; company-defined KPIs: {', '.join(company)}" if company else "; no company-specific KPIs")}
    else:
        comp["kpi_coverage"] = {"grade": "weak", "reason": "KPI registry not built"}
    lat = l4.read_json(base / "valuation/latest.json", {}) or {}
    methods = lat.get("methods") or {}
    bases = [v.get("base") for v in methods.values() if isinstance(v, dict) and isinstance(v.get("base"), (int, float))]
    rd = (lat.get("reverse_dcf") or {}).get("status", "")
    if "auto-draft" in json_str(methods) or "auto-draft" in rd:
        comp["valuation_agreement"] = {"grade": "weak", "reason": "valuation is an auto-draft (history-anchored assumptions)"}
    elif len(bases) >= 2:
        spread = max(bases) / min(bases) if min(bases) > 0 else None
        grade = "strong" if spread and spread < 1.3 else "adequate"
        reason = f"{len(bases)} methods, base values {min(bases):g}–{max(bases):g}" + \
            ("; methods broadly agree" if grade == "strong" else "; methods disagree materially")
        if grade == "strong" and str(lat.get("valuation_confidence") or l4.thesis(t, root).get("valuation_confidence")).lower() == "low":
            grade, reason = "adequate", reason + "; but the analyst's valuation confidence is low"
        comp["valuation_agreement"] = {"grade": grade, "reason": reason}
    else:
        comp["valuation_agreement"] = {"grade": "weak", "reason": "single valuation method"
                                       + (f"; reverse DCF {rd}" if rd else "") + " → high valuation uncertainty"}
    th = l4.thesis(t, root)
    lines = [str(e) for c in (th.get("components") or {}).values() for e in (c.get("evidence") or [])]
    facts = sum(x.startswith("Fact") for x in lines)
    if th.get("draft_auto"):
        comp["evidence_quality"] = {"grade": "weak", "reason": "thesis is an auto-draft (draft_auto); evidence not analyst-reviewed"}
    elif lines and facts / len(lines) >= 0.6:
        comp["evidence_quality"] = {"grade": "strong", "reason": f"{facts} of {len(lines)} thesis evidence lines are labelled Fact with sources"}
    else:
        comp["evidence_quality"] = {"grade": "adequate", "reason": f"{facts} of {len(lines)} thesis evidence lines are labelled Fact"}
    prom = l4.read_json(base / "management/promises.json", []) or []
    open_p = [p for p in prom if p.get("status") in ("pending", "not_evaluable")]
    resolved = [p for p in prom if p.get("status") in ("delivered", "partially_delivered", "missed", "delayed")]
    if not prom:
        comp["unresolved_promises"] = {"grade": "adequate", "reason": "no explicit evaluable management guidance found"}
    else:
        grade = "strong" if len(resolved) >= 2 * max(len(open_p), 1) else "adequate" if resolved else "weak"
        ne = sum(p.get("status") == "not_evaluable" for p in prom)
        comp["unresolved_promises"] = {"grade": grade, "reason": f"{len(resolved)} promises resolved, {len(open_p)} open"
                                       + (f" ({ne} not evaluable: definition / actual-basis gaps)" if ne else "")}
    if stale is not None:
        sev = stale.get("severity")
        comp["stale_data"] = {"grade": "weak" if sev == "HIGH" else "adequate" if sev in ("MEDIUM", "LOW") else "strong",
                              "reason": "; ".join(stale.get("reasons") or []) or "state is current"}
    weak = [k for k, v in comp.items() if v["grade"] == "weak"]
    strong = [k for k, v in comp.items() if v["grade"] == "strong"]
    if len(weak) >= 2 or th.get("draft_auto"):
        overall = "low"
    elif not weak and len(strong) >= len(comp) - 2:
        overall = "high"
    else:
        overall = "medium"
    return {"overall": overall, "reasons": [v["reason"] for v in comp.values()], "components": comp,
            "note": "Explainable research confidence, not a company score; no percentages."}


def json_str(o: Any) -> str:
    import json
    return json.dumps(o)
