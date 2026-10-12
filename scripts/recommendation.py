#!/usr/bin/env python3
"""Decision-layer helpers for valuation context; never auto-generates a buy price.

Valuation methods, reverse-DCF assumptions, scenario maps, and earnings catch-up
are displayed separately. BUY/ACCUMULATE/WATCH/HOLD EXISTING/AVOID remains an
analyst judgment based on evidence, not a threshold applied to one DCF result.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SCENARIOS = ("bear", "base", "bull")
ACTIONS = ("BUY", "ACCUMULATE", "WATCH", "HOLD EXISTING", "AVOID")


def _scenario_bounds(methods: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    bounds: Dict[str, Dict[str, float]] = {}
    for scenario in SCENARIOS:
        vals = [float(v[scenario]) for v in methods.values()
                if isinstance(v, dict) and scenario in v]
        if vals:
            bounds[scenario] = {"low": min(vals), "high": max(vals)}
    return bounds


def _between(low: float, high: float, label: str) -> Dict[str, Any]:
    return {"low": round(low, 2), "high": round(high, 2), "interpretation": label}


def valuation_map(methods: Dict[str, Dict[str, float]], current_price: float) -> Dict[str, Any]:
    """Map valuation zones from supplied method/scenario values; no fixed haircut."""
    bounds = _scenario_bounds(methods)
    if not bounds:
        raise ValueError("at least one bear/base/bull valuation is required")
    if not all(k in bounds for k in SCENARIOS):
        raise ValueError("valuation map needs bear, base, and bull estimates")
    bear, base, bull = (bounds[k] for k in SCENARIOS)
    zones: List[Dict[str, Any]] = [
        {"low": None, "high": round(bear["low"], 2), "interpretation": "below all modeled bear values"},
    ]
    if bear["low"] < bear["high"]:
        zones.append(_between(bear["low"], bear["high"], "within the bear-value spread across methods"))
    if bear["high"] < base["low"]:
        zones.append(_between(bear["high"], base["low"], "between bear and base estimates"))
    elif bear["high"] > base["low"]:
        zones.append(_between(base["low"], bear["high"], "bear/base estimates overlap"))
    if base["low"] < base["high"]:
        zones.append(_between(base["low"], base["high"], "within the base-value spread across methods"))
    if base["high"] < bull["low"]:
        zones.append(_between(base["high"], bull["low"], "between base and bull estimates"))
    elif base["high"] > bull["low"]:
        zones.append(_between(bull["low"], base["high"], "base/bull estimates overlap"))
    if bull["low"] < bull["high"]:
        zones.append(_between(bull["low"], bull["high"], "within the bull-value spread across methods"))
    zones.append({"low": round(bull["high"], 2), "high": None,
                  "interpretation": "above all modeled bull values"})

    if current_price < bear["low"]:
        position = zones[0]["interpretation"]
    elif current_price <= bear["high"]:
        position = zones[1]["interpretation"]
    elif current_price < base["low"]:
        position = "between bear and base estimates" if bear["high"] < base["low"] else "within overlapping bear/base estimates"
    elif current_price <= base["high"]:
        position = "within the base-value spread across methods"
    elif current_price < bull["low"]:
        position = "between base and bull estimates" if base["high"] < bull["low"] else "within overlapping base/bull estimates"
    elif current_price <= bull["high"]:
        position = "within the bull-value spread across methods"
    else:
        position = "above all modeled bull values"

    base_spread = None
    if base["low"] > 0 and len(methods) > 1:
        base_spread = (base["high"] - base["low"]) / base["low"]
    return {
        "scenario_bounds": bounds,
        "zones": zones,
        "current_price": round(float(current_price), 2),
        "current_position": position,
        "base_method_spread_pct_of_low": None if base_spread is None else round(base_spread * 100, 1),
    }


def reverse_dcf_interpretation(implied_growth: float, base_growth: float,
                               bull_growth: float) -> str:
    """Compare market-implied growth with analyst base/bull assumptions."""
    if implied_growth <= base_growth:
        return "at or below modeled base growth"
    if implied_growth <= bull_growth:
        return "above base but within modeled bull growth"
    return "above modeled bull growth"


def earnings_catch_up(current_price: float, current_eps: float,
                       growth_rates: Iterable[float] = (0.10, 0.15, 0.20),
                       years: Iterable[int] = (1, 2, 3)) -> List[Dict[str, Any]]:
    """Price-flat EPS growth scenarios; rates are decimals, not forecasts."""
    if current_price <= 0 or current_eps <= 0:
        raise ValueError("price and EPS must be positive")
    rows: List[Dict[str, Any]] = []
    for growth in growth_rates:
        if growth <= -1:
            raise ValueError("EPS growth must be greater than -100%")
        for horizon in years:
            if horizon <= 0:
                raise ValueError("years must be positive")
            future_eps = current_eps * (1 + growth) ** horizon
            rows.append({
                "annual_eps_growth_pct": round(growth * 100, 1),
                "years": int(horizon),
                "future_eps": round(future_eps, 2),
                "static_price_pe": round(current_price / future_eps, 1),
                "price_held_flat": round(current_price, 2),
            })
    return rows


def revenue_catch_up(current_ev: float, current_revenue: float,
                     growth_rates: Iterable[float],
                     years: Iterable[int] = (1, 2, 3)) -> List[Dict[str, Any]]:
    """Illustrate EV/sales compression if EV is held flat as revenue grows."""
    if current_ev <= 0 or current_revenue <= 0:
        raise ValueError("enterprise value and revenue must be positive")
    rows: List[Dict[str, Any]] = []
    for growth in growth_rates:
        if growth <= -1:
            raise ValueError("revenue growth must be greater than -100%")
        for horizon in years:
            if horizon <= 0:
                raise ValueError("years must be positive")
            future_revenue = current_revenue * (1 + growth) ** horizon
            rows.append({
                "annual_revenue_growth_pct": round(growth * 100, 1),
                "years": int(horizon),
                "future_revenue": round(future_revenue, 2),
                "static_ev_sales": round(current_ev / future_revenue, 1),
                "enterprise_value_held_flat": round(current_ev, 2),
            })
    return rows


def build_summary(doc: Dict[str, Any]) -> Dict[str, Any]:
    price = float(doc["current_price"])
    methods = doc["valuation_methods"]
    reverse = doc.get("reverse_dcf", {})
    eps = doc.get("normalized_eps")
    summary: Dict[str, Any] = {
        "current_price": round(price, 2),
        "valuation_methods": methods,
        "valuation_map": valuation_map(methods, price),
    }
    if all(k in reverse for k in ("implied_growth", "base_growth", "bull_growth")):
        summary["reverse_dcf"] = {
            **reverse,
            "market_expectation_vs_cases": reverse_dcf_interpretation(
                float(reverse["implied_growth"]), float(reverse["base_growth"]),
                float(reverse["bull_growth"])),
        }
    if eps is not None:
        summary["earnings_catch_up"] = earnings_catch_up(
            price, float(eps), doc.get("earnings_growth_rates", (0.10, 0.15, 0.20)),
            doc.get("catch_up_years", (1, 2, 3)))
    if "current_ev" in doc and "current_revenue" in doc:
        summary["revenue_catch_up"] = revenue_catch_up(
            float(doc["current_ev"]), float(doc["current_revenue"]),
            doc.get("revenue_growth_rates", (0.10, 0.20, 0.30)),
            doc.get("catch_up_years", (1, 2, 3)))
    return summary


def render_action(action: str, reason: str, has_existing_position: bool = False) -> str:
    """Render a qualitative action; no entry/exit price is attached."""
    if action not in ACTIONS:
        raise ValueError("action must be one of: " + ", ".join(ACTIONS))
    if action == "HOLD EXISTING" and not has_existing_position:
        raise ValueError("HOLD EXISTING requires an explicitly disclosed existing position")
    text = f"{action} — {reason.strip()}"
    if action == "WATCH":
        text += " WATCH describes current evidence and expectations; it does not set a required entry price or imply waiting for a market crash."
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON valuation-context inputs")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        print(json.dumps(build_summary(data), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
