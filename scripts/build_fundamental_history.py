#!/usr/bin/env python3
"""Generic SEC companyfacts -> historical fundamental baseline (5+ FY, 8+ quarters).

Replaces the AAPL-only extract_aapl.py pattern for any US filer. Rules:

* Mapping layer: each metric has an ordered list of candidate us-gaap tags.
  The tag actually used is stored per period (`tag`), and a fallback away
  from the metric's dominant tag is flagged (`tag_fallback`). No blind merge.
* Only facts from primary periodic filings (10-K, 10-Q and their /A
  amendments) are used; 8-K / S-1 / proxy facts are ignored.
* Duplicates (same tag, start, end, unit) resolve to the latest filed fact, so
  an amendment or a later restated comparative supersedes the original.
* `as_of` cutoff: facts filed after as_of are invisible (no look-ahead).
* Durations are classified by length (quarter 80-100 days, YTD 170-200 /
  260-290 days, year 350-380 days); YTD values are never stored as quarters.
* A standalone quarter missing from filings is derived as YTD(end) minus
  YTD(previous quarter end) only when both share the same fiscal-year start;
  the derivation is recorded. Otherwise the value stays null.
* Missing data is null with a reason. Nothing is interpolated or zero-filled.

Outputs (research/<TICKER>/financials/):
  history.json        annual + quarterly records with per-metric provenance
  historical.csv      long-format rows merged into any existing rows
  coverage.json       which periods/metrics are available or missing

Usage (network for the SEC fetch; --offline reuses raw/companyfacts.json):
  python3 scripts/build_fundamental_history.py PL --cik 1836833
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

PRIMARY_FORMS = ("10-K", "10-Q", "10-K/A", "10-Q/A", "10-KT", "10-KT/A", "20-F", "20-F/A", "40-F")

# metric -> (kind, unit, candidate tags in precedence order)
CONCEPTS: Dict[str, Tuple[str, str, Tuple[str, ...]]] = {
    "revenue": ("duration", "USD", (
        "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueGoodsNet")),
    "cost_of_revenue": ("duration", "USD", (
        "CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold", "CostOfServices")),
    "gross_profit": ("duration", "USD", ("GrossProfit",)),
    "operating_income": ("duration", "USD", ("OperatingIncomeLoss",)),
    "net_income": ("duration", "USD", ("NetIncomeLoss", "ProfitLoss",
                                        "NetIncomeLossAvailableToCommonStockholdersBasic")),
    "cfo": ("duration", "USD", ("NetCashProvidedByUsedInOperatingActivities",
                                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations")),
    "capex_ppe": ("duration", "USD", ("PaymentsToAcquirePropertyPlantAndEquipment",
                                      "PaymentsToAcquireProductiveAssets")),
    "capitalized_software": ("duration", "USD", ("PaymentsForSoftware", "PaymentsToDevelopSoftware")),
    "sbc": ("duration", "USD", ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense")),
    "depreciation_amortization": ("duration", "USD", (
        "DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
        "DepreciationAmortizationAndAccretionNet")),
    "diluted_shares": ("duration", "shares", ("WeightedAverageNumberOfDilutedSharesOutstanding",)),
    "basic_shares": ("duration", "shares", ("WeightedAverageNumberOfSharesOutstandingBasic",)),
    "eps_diluted": ("duration", "USD/shares", ("EarningsPerShareDiluted",)),
    "cash": ("instant", "USD", ("CashAndCashEquivalentsAtCarryingValue",
                                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")),
    "short_term_investments": ("instant", "USD", (
        "ShortTermInvestments", "MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent")),
    "debt_total": ("instant", "USD", ("LongTermDebt", "DebtInstrumentCarryingAmount")),
    "debt_noncurrent": ("instant", "USD", ("LongTermDebtNoncurrent", "ConvertibleNotesPayable",
                                           "ConvertibleDebtNoncurrent", "ConvertibleSeniorNotesNoncurrent")),
    "debt_current": ("instant", "USD", ("LongTermDebtCurrent", "ConvertibleNotesPayableCurrent",
                                        "DebtCurrent")),
    "commercial_paper": ("instant", "USD", ("CommercialPaper",)),
    "operating_lease_liability": ("instant", "USD", ("OperatingLeaseLiability",)),
    "shares_outstanding": ("instant", "shares", ("CommonStockSharesOutstanding",
                                                 "EntityCommonStockSharesOutstanding")),
    "equity": ("instant", "USD", ("StockholdersEquity",)),
    "rpo": ("instant", "USD", ("RevenueRemainingPerformanceObligation",)),
    "deferred_revenue": ("instant", "USD", ("ContractWithCustomerLiability", "DeferredRevenue")),
}
# Company-specific KPIs have no us-gaap tag; they are filled only from a
# configured extension tag (financials/tag-overrides.json) or stay unavailable.
COMPANY_KPIS = ("backlog", "arr", "bookings", "units", "subscribers")

ANNUAL_DAYS = (350, 380)
QUARTER_DAYS = (80, 100)
YTD_DAYS = {2: (170, 200), 3: (260, 290)}


def _days(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1


def _is_primary(form: str) -> bool:
    return form in PRIMARY_FORMS


def clean_facts(entries: Iterable[Dict[str, Any]], as_of: Optional[str] = None) -> Dict[Tuple, Dict[str, Any]]:
    """Primary filings only, filed <= as_of, one fact per (start, end): latest filed wins."""
    best: Dict[Tuple, Dict[str, Any]] = {}
    for x in entries:
        if not _is_primary(x.get("form", "")):
            continue
        if as_of and x.get("filed", "") > as_of:
            continue
        key = (x.get("start"), x["end"])
        cur = best.get(key)
        if cur is None or (x["filed"], x.get("accn", "")) > (cur["filed"], cur.get("accn", "")):
            best[key] = x
    return best


def tag_facts(facts: Dict[str, Any], tag: str, unit: str, as_of: Optional[str],
              overrides_ns: Iterable[str] = ("us-gaap",)) -> Dict[Tuple, Dict[str, Any]]:
    for ns in overrides_ns:
        node = facts.get("facts", {}).get(ns, {}).get(tag)
        if node and unit in node.get("units", {}):
            return clean_facts(node["units"][unit], as_of)
    return {}


def fiscal_year_ends(facts: Dict[str, Any], as_of: Optional[str]) -> List[str]:
    """Fiscal year-end dates from annual-length revenue / net income facts in 10-K filings."""
    ends = set()
    for metric in ("revenue", "net_income", "operating_income", "cfo"):
        _, unit, tags = CONCEPTS[metric]
        for tag in tags:
            for (start, end), x in tag_facts(facts, tag, unit, as_of).items():
                if start and ANNUAL_DAYS[0] <= _days(start, end) <= ANNUAL_DAYS[1] \
                        and x.get("form", "").startswith(("10-K", "20-F", "40-F")):
                    ends.add(end)
    return sorted(ends)


def fy_label(end: str, fy_ends: List[str]) -> Tuple[str, int]:
    """Fiscal year and quarter number of a period end (named by the FY-end calendar year)."""
    e = date.fromisoformat(end)
    if fy_ends:
        ref = date.fromisoformat(fy_ends[-1])
        fy_month, fy_day = ref.month, ref.day
    else:
        fy_month, fy_day = 12, 31
    fy_end = date(e.year, fy_month, min(fy_day, 28 if fy_month == 2 else fy_day))
    if (e - fy_end).days > 20:  # quarter ends after this year's FY end -> next fiscal year
        fy_end = date(e.year + 1, fy_end.month, fy_end.day)
    months_left = round((fy_end - e).days / 30.44)
    q = 4 - round(months_left / 3)
    return f"FY{fy_end.year}", max(1, min(4, q))


def _select(facts, metric, start_end_ok, as_of, overrides) -> Dict[str, Dict[str, Any]]:
    """For one metric: {end: fact+tag}, taking for each period the highest-precedence tag."""
    kind, unit, tags = CONCEPTS[metric]
    tags = tuple(overrides.get(metric, ())) + tags
    out: Dict[str, Dict[str, Any]] = {}
    for rank, tag in enumerate(tags):
        for (start, end), x in tag_facts(facts, tag, unit, as_of, ("us-gaap", "dei", "ifrs-full") +
                                         tuple(overrides.get("_namespaces", ()))).items():
            if not start_end_ok(start, end) or end in out:
                continue
            out[end] = {**x, "tag": tag, "tag_rank": rank}
    return out


def _prov(x: Dict[str, Any], scale: float, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    p = {"value": round(x["val"] / scale, 6) if scale != 1 else x["val"], "tag": x["tag"],
         "form": x.get("form"), "filed": x.get("filed"), "accn": x.get("accn"),
         "start": x.get("start"), "end": x.get("end")}
    if x.get("tag_rank"):
        p["tag_fallback"] = True
    if extra:
        p.update(extra)
    return p


def _scale(metric: str) -> float:
    kind, unit, _ = CONCEPTS[metric]
    return 1.0 if unit == "USD/shares" else 1e6


def build_history(facts: Dict[str, Any], as_of: Optional[str] = None, n_years: int = 6, n_quarters: int = 12,
                  overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    overrides = overrides or {}
    fy_ends = fiscal_year_ends(facts, as_of)
    annual_ok = lambda s, e: bool(s) and ANNUAL_DAYS[0] <= _days(s, e) <= ANNUAL_DAYS[1]
    quarter_ok = lambda s, e: bool(s) and QUARTER_DAYS[0] <= _days(s, e) <= QUARTER_DAYS[1]
    any_dur = lambda s, e: bool(s)
    instant_ok = lambda s, e: not s

    annual: Dict[str, Dict[str, Any]] = {e: {"period": fy_label(e, fy_ends)[0], "period_end": e, "metrics": {}}
                                         for e in fy_ends}
    quarters: Dict[str, Dict[str, Any]] = {}
    duration_metrics = [m for m, c in CONCEPTS.items() if c[0] == "duration"]
    instant_metrics = [m for m, c in CONCEPTS.items() if c[0] == "instant"]

    # Quarter ends: any 3-month or YTD duration fact for revenue / net income ending in a fiscal quarter.
    q_ends = set()
    for metric in ("revenue", "net_income", "operating_income"):
        for e, x in _select(facts, metric, any_dur, as_of, overrides).items():
            d = _days(x["start"], e)
            if QUARTER_DAYS[0] <= d <= QUARTER_DAYS[1] or any(a <= d <= b for a, b in YTD_DAYS.values()):
                q_ends.add(e)
    q_ends |= set(fy_ends)

    for metric in duration_metrics:
        scale = _scale(metric)
        ann = _select(facts, metric, annual_ok, as_of, overrides)
        for e, x in ann.items():
            if e in annual:
                annual[e]["metrics"][metric] = _prov(x, scale)
        # All duration facts ending on a quarter end, grouped by start, for YTD derivation.
        all_facts: Dict[Tuple[str, str], Dict[str, Any]] = {}
        kind, unit, tags = CONCEPTS[metric]
        for rank, tag in enumerate(tuple(overrides.get(metric, ())) + tags):
            for (s, e), x in tag_facts(facts, tag, unit, as_of).items():
                if s and (s, e) not in all_facts:
                    all_facts[(s, e)] = {**x, "tag": tag, "tag_rank": rank}
        for e in q_ends:
            standalone = [x for (s, ee), x in all_facts.items() if ee == e and quarter_ok(s, e)]
            rec = quarters.setdefault(e, {"period_end": e, "metrics": {}})
            if standalone:
                rec["metrics"][metric] = _prov(min(standalone, key=lambda x: x["tag_rank"]), scale)
                continue
            if metric in ("diluted_shares", "basic_shares", "eps_diluted"):
                rec["metrics"].setdefault(metric, None)  # averages / per-share values cannot be differenced
                continue
            # Derive: cumulative(start, e) - cumulative(start, prev_end) with the same fiscal-year start.
            derived = None
            for (s, ee), cum in sorted(all_facts.items()):
                if ee != e or quarter_ok(s, e):
                    continue
                for (s2, e2), prior in all_facts.items():
                    if s2 == s and e2 < e and _days(e2, e) - 1 in range(80, 101) and prior["tag"] == cum["tag"]:
                        val = cum["val"] - prior["val"]
                        derived = _prov({**cum, "val": val}, scale, {
                            "derived": f"{cum['tag']} {s}..{e} minus {s}..{e2}",
                            "derived_from": [cum.get("accn"), prior.get("accn")], "start": e2})
                        break
                if derived:
                    break
                # Fallback: cumulative minus the sum of contiguous standalone quarters from the same start.
                parts, cursor = [], s
                for _ in range(3):
                    nxt = next((x for (s3, e3), x in all_facts.items() if s3 == cursor and e3 < e
                                and quarter_ok(s3, e3) and x["tag"] == cum["tag"]), None)
                    if nxt is None:
                        break
                    parts.append(nxt)
                    cursor = (date.fromisoformat(nxt["end"]) + timedelta(days=1)).isoformat()
                    if _days(cursor, e) - 1 in range(80, 101) and parts:
                        val = cum["val"] - sum(x["val"] for x in parts)
                        derived = _prov({**cum, "val": val}, scale, {
                            "derived": f"{cum['tag']} {s}..{e} minus {len(parts)} standalone quarters",
                            "derived_from": [cum.get("accn")] + [x.get("accn") for x in parts], "start": cursor})
                        break
                if derived:
                    break
            rec["metrics"][metric] = derived

    for metric in instant_metrics:
        scale = _scale(metric)
        vals = _select(facts, metric, instant_ok, as_of, overrides)
        for e, x in vals.items():
            if e in annual:
                annual[e]["metrics"][metric] = _prov(x, scale)
            if e in quarters:
                quarters[e]["metrics"][metric] = _prov(x, scale)

    for kpi in COMPANY_KPIS:
        tag = overrides.get(kpi)
        for rec in list(annual.values()) + list(quarters.values()):
            rec["metrics"].setdefault(kpi, None)
        if tag:
            ns_list = overrides.get("_namespaces", [])
            for ns in ns_list:
                node = facts.get("facts", {}).get(ns, {}).get(tag[0] if isinstance(tag, list) else tag)
                if not node:
                    continue
                for unit, entries in node["units"].items():
                    for (s, e), x in clean_facts(entries, as_of).items():
                        for rec in ([annual.get(e)] + [quarters.get(e)]):
                            if rec is not None:
                                rec["metrics"][kpi] = _prov({**x, "tag": f"{ns}:{tag}", "tag_rank": 0},
                                                            1e6 if unit == "USD" else 1, {"unit": unit})

    for e, rec in quarters.items():
        fy, q = fy_label(e, fy_ends)
        rec["period"] = f"Q{q} {fy}"
    for rec in list(annual.values()) + list(quarters.values()):
        derive_metrics(rec["metrics"])

    annual_list = sorted(annual.values(), key=lambda r: r["period_end"])
    quarter_list = [q for q in sorted(quarters.values(), key=lambda r: r["period_end"])
                    if (q["metrics"].get("revenue") or q["metrics"].get("net_income"))]
    add_growth(annual_list, 1)  # on the full series so the first kept period still has a prior
    add_growth(quarter_list, 4)
    annual_list, quarter_list = annual_list[-n_years:], quarter_list[-n_quarters:]
    return {"as_of": as_of, "entity": facts.get("entityName"), "cik": facts.get("cik"),
            "fiscal_year_ends": fy_ends[-n_years:],
            "units": "USD millions; shares in millions; EPS in USD",
            "annual": annual_list, "quarters": quarter_list,
            "method": "build_fundamental_history.py (primary filings, latest-filed precedence, "
                      "YTD differencing only with matching fiscal-year start)"}


def _v(m: Dict[str, Any], k: str) -> Optional[float]:
    x = m.get(k)
    return x["value"] if isinstance(x, dict) and x.get("value") is not None else None


def _calc(value: Optional[float], formula: str) -> Optional[Dict[str, Any]]:
    return None if value is None else {"value": round(value, 6), "calculation": formula}


def derive_metrics(m: Dict[str, Any]) -> None:
    rev, cogs, gp = _v(m, "revenue"), _v(m, "cost_of_revenue"), _v(m, "gross_profit")
    if gp is None and rev is not None and cogs is not None:
        m["gross_profit"] = _calc(rev - cogs, "revenue - cost_of_revenue")
        gp = rev - cogs
    m["gross_margin_pct"] = _calc(gp / rev * 100 if gp is not None and rev else None, "gross_profit / revenue")
    oi = _v(m, "operating_income")
    m["operating_margin_pct"] = _calc(oi / rev * 100 if oi is not None and rev else None, "operating_income / revenue")
    ni = _v(m, "net_income")
    m["net_margin_pct"] = _calc(ni / rev * 100 if ni is not None and rev else None, "net_income / revenue")
    ppe, sw, cfo = _v(m, "capex_ppe"), _v(m, "capitalized_software"), _v(m, "cfo")
    capex = None if ppe is None else ppe + (sw or 0.0)
    m["capex"] = _calc(capex, "capex_ppe + capitalized_software" if sw is not None else "capex_ppe")
    m["fcf"] = _calc(cfo - capex if cfo is not None and capex is not None else None, "cfo - capex")
    fcf = _v(m, "fcf")
    m["fcf_margin_pct"] = _calc(fcf / rev * 100 if fcf is not None and rev else None, "fcf / revenue")
    sbc = _v(m, "sbc")
    m["sbc_pct_revenue"] = _calc(sbc / rev * 100 if sbc is not None and rev else None, "sbc / revenue")
    m["capex_pct_revenue"] = _calc(capex / rev * 100 if capex is not None and rev else None, "capex / revenue")
    total = _v(m, "debt_total")
    if total is None:
        parts = [_v(m, k) for k in ("debt_noncurrent", "debt_current", "commercial_paper")]
        if any(p is not None for p in parts):
            used = [k for k, p in zip(("debt_noncurrent", "debt_current", "commercial_paper"), parts) if p is not None]
            m["debt"] = _calc(sum(p for p in parts if p is not None), " + ".join(used))
        else:
            m["debt"] = None
    else:
        m["debt"] = _calc(total, "debt_total")
    cash, sti = _v(m, "cash"), _v(m, "short_term_investments")
    m["cash_and_investments"] = _calc(None if cash is None else cash + (sti or 0.0),
                                      "cash + short_term_investments" if sti is not None else "cash")


def add_growth(records: List[Dict[str, Any]], lag: int) -> None:
    by_end = {r["period_end"]: r for r in records}
    ends = sorted(by_end)
    for i, e in enumerate(ends):
        m = by_end[e]["metrics"]
        prior = None
        for j in range(i - 1, -1, -1):  # match the same fiscal period one year earlier
            days = (date.fromisoformat(e) - date.fromisoformat(ends[j])).days
            if 350 <= days <= 380:
                prior = by_end[ends[j]]["metrics"]
                break
        for k in ("revenue", "diluted_shares", "rpo", "gross_profit"):
            cur, prev = _v(m, k), _v(prior or {}, k)
            m[f"{k}_yoy_pct"] = _calc((cur / prev - 1) * 100 if cur is not None and prev else None,
                                      f"{k} vs same period prior year")


def coverage(history: Dict[str, Any]) -> Dict[str, Any]:
    def miss(records):
        out = {}
        for r in records:
            gone = sorted(k for k, v in r["metrics"].items() if v is None)
            if gone:
                out[r["period"]] = gone
        return out
    fb = sorted({f"{r['period']}:{k}" for r in history["annual"] + history["quarters"]
                 for k, v in r["metrics"].items() if isinstance(v, dict) and v.get("tag_fallback")})
    return {"annual_periods": [r["period"] for r in history["annual"]],
            "quarter_periods": [r["period"] for r in history["quarters"]],
            "meets_5y": len([r for r in history["annual"] if _v(r["metrics"], "revenue") is not None]) >= 5,
            "meets_8q": len([r for r in history["quarters"] if _v(r["metrics"], "revenue") is not None]) >= 8,
            "missing": {"annual": miss(history["annual"]), "quarters": miss(history["quarters"])},
            "tag_fallbacks": fb,
            "company_kpis_note": "backlog / ARR / bookings / units / subscribers have no us-gaap tag; "
                                 "null unless an extension tag is configured in tag-overrides.json"}


CSV_HEADER = ["period", "period_end", "metric", "value", "unit", "basis", "classification", "source"]


def csv_rows(history: Dict[str, Any]) -> List[List[Any]]:
    rows = []
    for kind, records in (("annual", history["annual"]), ("quarter", history["quarters"])):
        for r in records:
            for metric, p in sorted(r["metrics"].items()):
                if not isinstance(p, dict) or p.get("value") is None:
                    continue
                unit = "%" if metric.endswith("_pct") else ("shares millions" if "shares" in metric
                                                             else "USD" if metric == "eps_diluted" else "USD millions")
                if "calculation" in p:
                    cls, src = "Calculation", p["calculation"]
                else:
                    cls = "Calculation" if p.get("derived") else "Fact"
                    src = f"SEC {p.get('form')} filed {p.get('filed')}, accession {p.get('accn')}, US GAAP {p.get('tag')}"
                    if p.get("derived"):
                        src += f" (standalone quarter derived: {p['derived']})"
                rows.append([r["period"], r["period_end"], metric, p["value"], unit,
                             "consolidated US GAAP", cls, src])
    return rows


def merge_historical_csv(path: Path, new_rows: List[List[Any]]) -> int:
    """Merge by (period_end, metric): new SEC rows replace the same key; other rows are kept."""
    existing: Dict[Tuple[str, str], List[Any]] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                existing[(r["period_end"], r["metric"])] = [r.get(h, "") for h in CSV_HEADER]
    for row in new_rows:
        existing[(str(row[1]), row[2])] = row
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEADER)
        w.writerows(existing[k] for k in sorted(existing))
    return len(existing)


def write_outputs(ticker: str, history: Dict[str, Any], root: Path = ROOT) -> Dict[str, Any]:
    fin = root / "research" / ticker.upper() / "financials"
    fin.mkdir(parents=True, exist_ok=True)
    (fin / "history.json").write_text(json.dumps(history, indent=1) + "\n", encoding="utf-8")
    cov = coverage(history)
    (fin / "coverage.json").write_text(json.dumps(cov, indent=2) + "\n", encoding="utf-8")
    n = merge_historical_csv(fin / "historical.csv", csv_rows(history))
    return {"history": str(fin / "history.json"), "historical_csv_rows": n, **cov}


def load_history(ticker: str, root: Path = ROOT) -> Optional[Dict[str, Any]]:
    p = root / "research" / ticker.upper() / "financials/history.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--cik", help="verified numeric CIK (required unless --offline)")
    ap.add_argument("--as-of", help="ignore facts filed after this date (YYYY-MM-DD)")
    ap.add_argument("--offline", action="store_true", help="reuse research/<T>/raw/companyfacts.json")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args(argv)
    t = args.ticker.upper()
    if args.offline:
        facts = json.loads((args.root / "research" / t / "raw/companyfacts.json").read_text())
    else:
        if not args.cik or not args.cik.isdigit():
            ap.error("a verified numeric --cik is required")
        import sec_data
        facts = sec_data.company_facts(args.cik, t, args.root)
    ov_path = args.root / "research" / t / "financials/tag-overrides.json"
    overrides = json.loads(ov_path.read_text()) if ov_path.exists() else {}
    history = build_history(facts, args.as_of, overrides=overrides)
    out = write_outputs(t, history, args.root)
    print(json.dumps({k: v for k, v in out.items() if k != "missing"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
