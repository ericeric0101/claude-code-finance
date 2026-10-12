#!/usr/bin/env python3
"""History-anchored drafts of thesis, valuation and monitoring rules for INIT.

Every output is labelled `draft_auto: true` and "Assumption (auto-draft from
reported history; analyst review required)". Drafts exist so that a newly
initialized company has a comparable baseline state instead of an empty shell;
they are not recommendations. The action is WATCH with low valuation confidence
until an analyst reviews the drafts (recommendation-policy: actions are analyst
judgments). No buy range or entry price is ever produced.

Valuation model (same structure as the PL five-year scenario DCF, which it reproduces):
  revenue_t = revenue_ttm * (1 + cagr)^t, FCF margin ramps linearly from the TTM
  margin to the year-5 margin; value = PV(FCF years 1-5) + PV(year-5 FCF x terminal
  EV/FCF) + net cash, divided by diluted shares.
Reverse DCF solves the 5-year revenue CAGR that reproduces the current price
holding the base-case margin, multiple and discount rate.
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import recommendation  # noqa: E402
from build_fundamental_history import _v  # noqa: E402

DRAFT_LABEL = "Assumption (auto-draft from reported history; analyst review required)"


def _ttm(qs: List[Dict[str, Any]], key: str) -> Optional[float]:
    vals = [_v(q["metrics"], key) for q in qs[-4:]]
    return sum(vals) if len(vals) == 4 and None not in vals else None


def facts_summary(history: Dict[str, Any]) -> Dict[str, Any]:
    qs = [q for q in history["quarters"] if _v(q["metrics"], "revenue") is not None]
    ann = [a for a in history["annual"] if _v(a["metrics"], "revenue") is not None]
    last = qs[-1]["metrics"] if qs else {}
    rev_ttm, prev_ttm = _ttm(qs, "revenue"), _ttm(qs[:-4], "revenue") if len(qs) >= 8 else None
    fcf_ttm = _ttm(qs, "fcf")
    gm = [_v(q["metrics"], "gross_margin_pct") for q in qs[-8:] if _v(q["metrics"], "gross_margin_pct") is not None]
    cagr3 = None
    if len(ann) >= 4 and _v(ann[-4]["metrics"], "revenue") and _v(ann[-1]["metrics"], "revenue"):
        a, b = _v(ann[-4]["metrics"], "revenue"), _v(ann[-1]["metrics"], "revenue")
        cagr3 = (b / a) ** (1 / 3) - 1 if a > 0 and b > 0 else None
    fcf_margins = [_v(a["metrics"], "fcf_margin_pct") for a in ann if _v(a["metrics"], "fcf_margin_pct") is not None]
    return {
        "latest_quarter": qs[-1]["period"] if qs else None, "revenue_ttm": rev_ttm,
        "ttm_growth": (rev_ttm / prev_ttm - 1) if rev_ttm and prev_ttm else None, "cagr_3y": cagr3,
        "fcf_ttm": fcf_ttm, "fcf_margin_ttm": (fcf_ttm / rev_ttm) if fcf_ttm is not None and rev_ttm else None,
        "best_fcf_margin": max(fcf_margins) / 100 if fcf_margins else None,
        "gm_last": _v(last, "gross_margin_pct"), "gm_min_8q": min(gm) if gm else None,
        "gm_median_8q": statistics.median(gm) if gm else None,
        "om_last": _v(last, "operating_margin_pct"), "rev_yoy_last": _v(last, "revenue_yoy_pct"),
        "dil_yoy_last": _v(last, "diluted_shares_yoy_pct"), "rpo": _v(last, "rpo"),
        "rpo_yoy": _v(last, "rpo_yoy_pct"), "cash": _v(last, "cash_and_investments") or 0.0,
        "debt": _v(last, "debt") or 0.0,
        "diluted_shares": next((_v(q["metrics"], "diluted_shares") for q in reversed(qs)
                                if _v(q["metrics"], "diluted_shares")), None),
        "capex_pct_ttm": (_ttm(qs, "capex") / rev_ttm * 100) if _ttm(qs, "capex") is not None and rev_ttm else None,
    }


def value_per_share(rev0: float, cagr: float, fcf_margin: float, multiple: float, rate: float,
                    net_cash: float, shares: float, start_margin: Optional[float] = None) -> float:
    """Five years of FCF (margin ramps linearly from start_margin to fcf_margin) plus a
    terminal EV/FCF multiple on year-5 FCF, discounted, plus net cash, per share.
    Reproduces the PL 2026-10-11 scenario values (3 / 12 / 25) and 36.1% implied CAGR."""
    m0 = fcf_margin if start_margin is None else start_margin
    pv = 0.0
    for t in range(1, 6):
        pv += rev0 * (1 + cagr) ** t * (m0 + (fcf_margin - m0) * t / 5) / (1 + rate) ** t
    pv += rev0 * (1 + cagr) ** 5 * fcf_margin * multiple / (1 + rate) ** 5
    return (pv + net_cash) / shares


def solve_implied_cagr(price: float, rev0: float, fcf_margin: float, multiple: float, rate: float,
                       net_cash: float, shares: float, start_margin: Optional[float] = None) -> Optional[float]:
    lo, hi = -0.5, 1.5
    f = lambda g: value_per_share(rev0, g, fcf_margin, multiple, rate, net_cash, shares, start_margin) - price
    if f(lo) > 0 or f(hi) < 0:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2, 4)


def scenario_assumptions(s: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """History-anchored scenarios: base growth blends 3Y CAGR and TTM growth; margins
    anchor to the best reported FCF margin (floored / capped)."""
    hist = [g for g in (s["cagr_3y"], s["ttm_growth"]) if g is not None]
    base_g = max(min(statistics.mean(hist) if hist else 0.05, 0.40), 0.0)
    best = max([m for m in (s["best_fcf_margin"], s["fcf_margin_ttm"]) if m is not None] or [0.10])
    base_m = min(max(best, 0.10), 0.30)
    return {
        "bear": {"revenue_cagr_5y": round(base_g * 0.5, 4), "fcf_margin_y5": round(base_m * 0.6, 4),
                 "terminal_ev_fcf": 18, "discount_rate": 0.12},
        "base": {"revenue_cagr_5y": round(base_g, 4), "fcf_margin_y5": round(base_m, 4),
                 "terminal_ev_fcf": 22, "discount_rate": 0.105},
        "bull": {"revenue_cagr_5y": round(min(max(base_g * 1.4, (s["ttm_growth"] or 0)), 0.6), 4),
                 "fcf_margin_y5": round(min(base_m + 0.05, 0.35), 4), "terminal_ev_fcf": 28, "discount_rate": 0.095},
    }


def draft_valuation(ticker: str, s: Dict[str, Any], price: float, price_date: str, as_of: str) -> Dict[str, Any]:
    sc = scenario_assumptions(s)
    net_cash = s["cash"] - s["debt"]
    shares = s["diluted_shares"]
    rev0 = s["revenue_ttm"]
    m0 = s["fcf_margin_ttm"]
    methods = {"five-year scenario DCF (auto-draft)": {
        k: round(value_per_share(rev0, a["revenue_cagr_5y"], a["fcf_margin_y5"], a["terminal_ev_fcf"],
                                 a["discount_rate"], net_cash, shares, m0), 2) for k, a in sc.items()}}
    b = sc["base"]
    implied = solve_implied_cagr(price, rev0, b["fcf_margin_y5"], b["terminal_ev_fcf"], b["discount_rate"],
                                 net_cash, shares, m0)
    vmap = recommendation.valuation_map(methods, price)
    rd = {"status": "auto-draft (low confidence)", "classification": "Calculation from Assumptions",
          "implied_growth": implied, "base_growth": b["revenue_cagr_5y"], "bull_growth": sc["bull"]["revenue_cagr_5y"],
          "solved_for": "5-year revenue CAGR from TTM revenue", "held_at_base_case": b,
          "caveat": "Not a unique solution; implied growth moves with margin, multiple and dilution."}
    if implied is not None:
        rd["market_expectation_vs_cases"] = recommendation.reverse_dcf_interpretation(
            implied, b["revenue_cagr_5y"], sc["bull"]["revenue_cagr_5y"])
    return {
        "ticker": ticker, "as_of": as_of, "draft_auto": True, "price": price, "price_date": price_date,
        "action": "WATCH", "valuation_confidence": "low",
        "confidence_reason": "Auto-drafted from reported history; assumptions not yet reviewed by an analyst.",
        "classification": DRAFT_LABEL, "methods": methods, "reverse_dcf": rd,
        "valuation_map": {"current_position": vmap.get("current_position"), "zones": vmap.get("zones"),
                          "note": "Zones are model comparisons, not forecasts or entry prices."},
        "expectations": {"market_implied": {"revenue_cagr_5y": implied} if implied is not None else {},
                         "internal_base": {"revenue_cagr_5y": b["revenue_cagr_5y"], "fcf_margin_y5": b["fcf_margin_y5"]},
                         "bear": {"revenue_cagr_5y": sc["bear"]["revenue_cagr_5y"], "fcf_margin_y5": sc["bear"]["fcf_margin_y5"]},
                         "bull": {"revenue_cagr_5y": sc["bull"]["revenue_cagr_5y"], "fcf_margin_y5": sc["bull"]["fcf_margin_y5"]},
                         "reason": "Market-implied CAGR solved holding base-case margin, multiple and discount rate."},
        "catch_up": {"ev": round(price * shares - net_cash, 1), "revenue": rev0,
                     "revenue_growth_rates": [0.10, 0.20, 0.30], "years": [1, 2, 3]},
        "inputs": {"revenue_ttm": rev0, "net_cash": net_cash, "diluted_shares": shares,
                   "source": "financials/history.json (SEC companyfacts)"},
    }, {"ticker": ticker, "as_of": as_of, "classification": DRAFT_LABEL, "scenario_assumptions": {
        k: {"revenue_cagr_5y": v["revenue_cagr_5y"], "fcf_margin_y5": v["fcf_margin_y5"]} for k, v in sc.items()},
        "model_parameters": sc}


def _status(good: Optional[bool], bad: Optional[bool]) -> str:
    if bad:
        return "weakening"
    if good:
        return "improving"
    return "uncertain"


def draft_thesis(ticker: str, company: str, s: Dict[str, Any], as_of: str, src: str) -> Dict[str, Any]:
    def comp(importance, status, evidence, next_check, invalidation):
        return {"importance": importance, "status": status, "evidence": evidence, "last_updated": as_of,
                "next_check": next_check, "invalidation_condition": invalidation, "draft_auto": True}
    g = s["rev_yoy_last"]
    comps = {
        "revenue_growth_durability": comp(
            "high", _status(g is not None and s["ttm_growth"] is not None and g / 100 >= s["ttm_growth"],
                            g is not None and g < 0),
            [f"Calculation: latest quarter revenue YoY {g if g is None else round(g, 1)}%, TTM growth "
             f"{None if s['ttm_growth'] is None else round(s['ttm_growth'] * 100, 1)}%, 3Y CAGR "
             f"{None if s['cagr_3y'] is None else round(s['cagr_3y'] * 100, 1)}% ({src})."],
            "Next 10-Q revenue YoY", "Revenue YoY negative for two consecutive quarters"),
        "margin_trajectory": comp(
            "high", _status(s["gm_last"] is not None and s["gm_median_8q"] is not None and s["gm_last"] >= s["gm_median_8q"],
                            s["gm_last"] is not None and s["gm_min_8q"] is not None and s["gm_last"] <= s["gm_min_8q"]),
            [f"Calculation: gross margin latest {s['gm_last'] and round(s['gm_last'], 1)}% vs 8Q median "
             f"{s['gm_median_8q'] and round(s['gm_median_8q'], 1)}%; operating margin {s['om_last'] and round(s['om_last'], 1)}% ({src})."],
            "Next 10-Q gross and operating margin", "Gross margin below the 8-quarter low for two consecutive quarters"),
        "cash_conversion": comp(
            "high", _status(s["fcf_ttm"] is not None and s["fcf_ttm"] > 0, s["fcf_ttm"] is not None and s["fcf_ttm"] < 0),
            [f"Calculation: TTM FCF {s['fcf_ttm'] and round(s['fcf_ttm'], 1)}m (CFO - capex), capex "
             f"{s['capex_pct_ttm'] and round(s['capex_pct_ttm'], 1)}% of revenue ({src})."],
            "Next 10-Q cash flow statement", "TTM FCF turns negative while capex intensity rises"),
        "per_share_dilution": comp(
            "medium", _status(s["dil_yoy_last"] is not None and s["dil_yoy_last"] <= 0,
                              s["dil_yoy_last"] is not None and s["dil_yoy_last"] > 5),
            [f"Calculation: weighted diluted shares YoY {s['dil_yoy_last'] and round(s['dil_yoy_last'], 1)}% ({src})."],
            "Each 10-Q share count", "Diluted shares rise more than 5% YoY"),
        "balance_sheet_liquidity": comp(
            "medium", "supported" if s["cash"] >= s["debt"] else "uncertain",
            [f"Fact: cash and short-term investments {round(s['cash'], 1)}m vs debt {round(s['debt'], 1)}m ({src})."],
            "Next balance sheet", "Net debt with negative FCF"),
    }
    if s["rpo"] is not None:
        comps["backlog_visibility"] = comp(
            "high", _status(s["rpo_yoy"] is not None and s["rpo_yoy"] > 0, s["rpo_yoy"] is not None and s["rpo_yoy"] < 0),
            [f"Fact/Calculation: RPO {round(s['rpo'], 1)}m, YoY {s['rpo_yoy'] and round(s['rpo_yoy'], 1)}% ({src})."],
            "Next 10-Q RPO", "RPO declines year over year")
    return {"ticker": ticker, "company": company, "as_of": as_of, "draft_auto": True, "action": "WATCH",
            "valuation_confidence": "low", "research_role": "auto-draft (unclassified)",
            "summary": "Auto-drafted from SEC history: component statuses follow reported trends only. "
                       "An analyst must review the thesis, add qualitative evidence and set the action.",
            "components": comps,
            "next_catalysts": ["Next 10-Q / earnings release (8-K Item 2.02)",
                               "Resolution of pending guidance promises (management/promises.json)"]}


def draft_rules(ticker: str, s: Dict[str, Any], methods: Dict[str, Dict[str, float]], as_of: str) -> tuple:
    base_g = None
    fundamental = {
        "revenue_growth": {"metric": "revenue_growth_yoy_pct", "warning": "<0%",
                           "basis": "assumption (auto-draft): revenue decline year over year"},
        "dilution_yoy": {"metric": "diluted_shares_yoy_pct", "warning": ">5%", "basis": "assumption (auto-draft)"},
    }
    if s["gm_min_8q"] is not None:
        fundamental["gross_margin"] = {"metric": "gaap_gross_margin_pct", "warning": f"<{round(s['gm_min_8q'] - 2, 1)}%",
                                       "basis": "auto-draft: 2 pp below the 8-quarter low"}
    if s["rpo"] is not None:
        fundamental["backlog_yoy"] = {"metric": "rpo_yoy_pct", "warning": "<0%", "basis": "auto-draft"}
    if s["capex_pct_ttm"] is not None:
        fundamental["capex_intensity"] = {"metric": "capex_pct_revenue",
                                          "warning": f">{round(s['capex_pct_ttm'] + 10, 1)}%",
                                          "basis": "auto-draft: TTM capex intensity + 10 pp"}
    vals = sorted({v for m in methods.values() for v in m.values() if v and v > 0})
    rules = {"ticker": ticker, "as_of": as_of, "draft_auto": True, "monitoring": {
        "fundamental": fundamental,
        "market": {"reassess_price": vals, "basis": "valuation-map boundaries of the auto-draft scenario DCF",
                   "meaning": "reassess thesis and valuation; not an entry price, exit price or order"}}}
    inval = {"ticker": ticker, "as_of": as_of, "rules": [
        {"id": "revenue_decline_two_quarters", "condition": "Revenue YoY negative for two consecutive quarters",
         "thesis_component": "revenue_growth_durability", "checks": [
             {"metric": "revenue_growth_yoy_pct", "warning": "<0%", "consecutive_quarters": 2}]},
        {"id": "dilution_above_5pct", "condition": "Diluted shares up more than 5% YoY",
         "thesis_component": "per_share_dilution", "checks": [{"metric": "diluted_shares_yoy_pct", "warning": ">5%"}]},
    ]}
    if s["gm_min_8q"] is not None:
        inval["rules"].append({"id": "gross_margin_below_8q_low", "condition": "Gross margin below the 8-quarter low "
                               "for two consecutive quarters", "thesis_component": "margin_trajectory", "checks": [
                                   {"metric": "gaap_gross_margin_pct", "warning": f"<{round(s['gm_min_8q'], 1)}%",
                                    "consecutive_quarters": 2}]})
    if s["rpo"] is not None:
        inval["rules"].append({"id": "rpo_decline_yoy", "condition": "RPO declines year over year",
                               "thesis_component": "backlog_visibility",
                               "checks": [{"metric": "rpo_yoy_pct", "warning": "<0%"}]})
    return rules, inval
