#!/usr/bin/env python3
"""PL deep dive 2026-10-13: scenario DCF, reverse DCF, share-basis sensitivity,
own-history EV/Sales cross-check and revenue catch-up. Reproducible from local state.

Run from the repo root:  python3 research/PL/valuation/model-2026-10-13.py
Writes research/PL/valuation/model-2026-10-13.json.  All outputs are
Calculations from Assumptions; none is a price target or entry price.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from baseline_draft import solve_implied_cagr, value_per_share  # noqa: E402

PL = ROOT / "research/PL"

PRICE, PRICE_DATE = 15.96, "2026-10-12 close"
REV0 = 435.5            # FY2027 midpoint guidance (8-K 2026-09-03), USD m
START_MARGIN = -0.06    # FY2027 FCF margin start (assumption; TTM reported +5.3%, H1 ex deferred revenue -12.3%)
BASIC_SHARES = 363.848  # 10-Q cover, 2026-08-27
AWARDS = 37.444 + 1.066  # options/RSUs/PSUs + warrants excluded from diluted EPS at 2026-07-31
CONV_SHARES = 460 * 83.6715 / 1000  # 0.50% notes due 2030, conversion rate per $1,000 (8-K 2025-09-12)
CASH, NOTES, LEASES = 865.418, 448.255, 50.4

SCENARIOS = {  # unchanged from the 2026-10-11 baseline (valuation/assumptions.json)
    "bear": {"prob": 0.30, "cagr": 0.10, "margin": 0.08, "multiple": 18, "rate": 0.12},
    "base": {"prob": 0.50, "cagr": 0.25, "margin": 0.20, "multiple": 25, "rate": 0.105},
    "bull": {"prob": 0.20, "cagr": 0.35, "margin": 0.25, "multiple": 30, "rate": 0.095},
}

SHARE_BASES = {
    "stored (net liquid 375 / 410m)": (375.0, 410.0),
    "basic + awards, notes as debt": (CASH - NOTES - LEASES, BASIC_SHARES + AWARDS),
    "basic + awards + if-converted notes": (CASH - LEASES, BASIC_SHARES + AWARDS + CONV_SHARES),
}


def vps(a, net, sh, **over):
    p = {**a, **over}
    return round(value_per_share(REV0, p["cagr"], p["margin"], p["multiple"], p["rate"], net, sh, START_MARGIN), 2)


def main():
    out = {"as_of": "2026-10-13", "price": PRICE, "price_date": PRICE_DATE,
           "classification": "Calculation from Assumptions", "start_revenue": REV0,
           "start_fcf_margin": START_MARGIN, "conversion_shares_m": round(CONV_SHARES, 2)}
    net, sh = SHARE_BASES["basic + awards, notes as debt"]
    out["scenarios"] = {}
    for basis, (n, s) in SHARE_BASES.items():
        out["scenarios"][basis] = {k: vps(a, n, s) for k, a in SCENARIOS.items()}
        out["scenarios"][basis]["probability_weighted"] = round(
            sum(SCENARIOS[k]["prob"] * out["scenarios"][basis][k] for k in SCENARIOS), 2)

    b = SCENARIOS["base"]
    rd = {}
    for label, margin, mult, rate in [("base margin 20% / 25x / 10.5%", .20, 25, .105),
                                      ("history-anchored margin 15% / 25x / 10.5%", .15, 25, .105),
                                      ("bull margin 25% / 30x / 9.5%", .25, 30, .095)]:
        rd[label] = {basis: solve_implied_cagr(PRICE, REV0, margin, mult, rate, n, s, START_MARGIN)
                     for basis, (n, s) in SHARE_BASES.items()}
    out["reverse_dcf_implied_5y_cagr"] = rd

    out["base_sensitivity"] = {
        "fcf_margin_y5": {str(m): vps(b, net, sh, margin=m) for m in (0.10, 0.15, 0.20, 0.25)},
        "discount_rate": {str(r): vps(b, net, sh, rate=r) for r in (0.095, 0.105, 0.12)},
        "terminal_ev_fcf": {str(x): vps(b, net, sh, multiple=x) for x in (18, 25, 30)},
        "revenue_cagr": {str(g): vps(b, net, sh, cagr=g) for g in (0.15, 0.20, 0.25, 0.30)},
    }

    ev = PRICE * BASIC_SHARES + NOTES + LEASES - CASH
    out["current_ev_m"] = round(ev, 1)
    out["ev_sales_fy2027_guidance_mid"] = round(ev / REV0, 2)
    out["ev_sales_ttm"] = round(ev / 378.278, 2)
    out["ev_gross_profit_ttm"] = round(ev / 209.647, 2)

    rows = [r for r in csv.DictReader(open(PL / "valuation/historical-multiples.csv"))
            if r["kind"] == "month_end" and r["ev_sales"]]
    hist = {}
    for label, since in [("since_listing", "2021-06-04"), ("3y", "2023-10-12"), ("1y", "2025-10-12")]:
        v = sorted(float(r["ev_sales"]) for r in rows if r["date"] >= since)
        q = {p: v[int(len(v) * p)] for p in (0.25, 0.5, 0.75)}
        hist[label] = {"n": len(v), "q25": q[0.25], "median": q[0.5], "q75": q[0.75],
                       "min": v[0], "max": v[-1],
                       "implied_price_at_median_ttm_sales": round(
                           (q[0.5] * 378.278 - NOTES - LEASES + CASH) / BASIC_SHARES, 2)}
    out["own_history_ev_sales"] = hist
    out["own_history_note"] = ("Bimodal history: 0.8-6.6x before the 2025 sovereign-contract RPO step-up, "
                               "12.8-50.8x after; a single median mixes two regimes.")

    out["catch_up"] = {f"{int(g*100)}%": [{"year": y, "revenue": round(REV0 * (1 + g) ** y),
                                           "ev_sales": round(ev / (REV0 * (1 + g) ** y), 1)}
                                          for y in (1, 2, 3)] for g in (0.10, 0.25, 0.35)}
    # Same model at the two retrospective snapshot dates (data public at that date; no hindsight).
    retro = {}
    for date, price, rev0, net, sh, basis in [
            ("2025-09-10", 8.97, 285.0, 271.537, 304.129,
             "FY2026 guidance mid 281-289 (8-K 2025-09-08); cash 271.5, no debt; diluted 304.1m"),
            ("2026-06-08", 32.74, 433.0, 730.835 - 447.569 - 50.4, 345.524,
             "FY2027 guidance mid 425-441 (8-K 2026-06-04); cash 730.8 - notes 447.6 - leases 50.4; diluted 345.5m")]:
        retro[date] = {"price": price, "basis": basis,
                       "implied_5y_cagr_base_margin": solve_implied_cagr(price, rev0, .20, 25, .105, net, sh, START_MARGIN),
                       "implied_5y_cagr_bull_margin": solve_implied_cagr(price, rev0, .25, 30, .095, net, sh, START_MARGIN)}
    out["retrospective_reverse_dcf"] = retro
    path = PL / "valuation/model-2026-10-13.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
