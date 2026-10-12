#!/usr/bin/env python3
"""One-time, re-runnable migration of the 2026-10-11 AAPL / PL outputs into
research/<TICKER>/ state files. Reads existing dated outputs only (no network)
and regenerates derived files: financials/historical.csv, financials/latest.json,
evidence/sources.json and market/prices.csv. Hand-authored state (thesis,
valuation, monitoring, management) is not touched. The dated reports and their
input JSON remain the authoritative record for that research date.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"


def _write_csv(path: Path, header, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def _metric(value, period, unit, classification, source, note=""):
    out = {"value": value, "period": period, "unit": unit,
           "classification": classification, "source": source}
    if note:
        out["note"] = note
    return out


def migrate_aapl() -> None:
    base = RESEARCH / "AAPL"
    fin = json.loads((base / "financial-data.json").read_text())
    header = ["period", "period_end", "metric", "value", "unit", "basis", "classification", "source"]
    rows = []
    for kind, records in (("annual", fin["annual"]), ("quarter", fin["quarters"])):
        for rec in records:
            for metric, value in rec.items():
                if metric in ("label", "end", "provenance") or not isinstance(value, (int, float)):
                    continue
                prov = rec.get("provenance", {}).get(metric, {})
                src = prov.get("source") or f"financial-data.json {kind} {rec['label']}"
                unit = "USD" if metric == "eps" else ("shares millions" if "shares" in metric else "USD millions")
                rows.append([rec["label"], rec["end"], metric, value, unit,
                             "consolidated US GAAP", "Fact", src])
    _write_csv(base / "financials/historical.csv", header, rows)

    q = {r["end"]: r for r in fin["quarters"]}
    cur, prior = q["2026-06-27"], q["2025-06-28"]
    src_q = "financial-data.json quarters (SEC 10-Q XBRL; per-field accession in provenance)"
    ann = {r["label"]: r for r in fin["annual"]}
    gm = {k: round((r["revenue"] - r["cogs"]) / r["revenue"] * 100, 2) for k, r in ann.items() if r.get("cogs")}
    metrics = {
        "quarterly_revenue_growth_yoy_pct": _metric(
            round((cur["revenue"] / prior["revenue"] - 1) * 100, 2), "Q3 FY2026 vs Q3 FY2025", "%",
            "Calculation", src_q),
        "quarterly_gross_margin_pct": _metric(
            round((cur["revenue"] - cur["cogs"]) / cur["revenue"] * 100, 2), "Q3 FY2026", "%",
            "Calculation", src_q, "Reported GAAP; report notes ~2 margin points from a one-time tariff refund."),
        "annual_gross_margin_pct": {k: v for k, v in gm.items()},
        "diluted_shares_yoy_pct": _metric(
            round((cur["diluted_shares"] / prior["diluted_shares"] - 1) * 100, 2),
            "Q3 FY2026 vs Q3 FY2025 weighted diluted", "%", "Calculation", src_q),
        "quarterly_receivables_growth_yoy_pct": _metric(
            round((cur["receivables"] / prior["receivables"] - 1) * 100, 2) if prior.get("receivables") else None,
            "2026-06-27 vs 2025-06-28 balance", "%", "Calculation", src_q),
        "receivables_growth_minus_revenue_growth_pp": _metric(
            12.7, "FY2025 (trade AR +19.1% vs sales +6.4%)", "pp", "Calculation",
            "AAPL-analysis-2026-10-11.md scorecard gate; FY2025/FY2024 10-K balance sheets"),
        "ttm_revenue": _metric(fin["ttm"]["revenue"], "TTM to Q3 FY2026", "USD millions", "Calculation",
                               "financial-data.json ttm; " + fin["ttm_formula"]),
        "ttm_reported_fcf": _metric(fin["ttm"]["fcf"], "TTM to Q3 FY2026", "USD millions", "Calculation",
                                    "financial-data.json ttm (CFO - PP&E capex; not FCFF)"),
        "normalized_fcff_proxy": _metric(120500, "2026-10-11 normalization", "USD millions", "Assumption",
                                         "normalized-valuation-output.json; cashflow-valuation-review.md"),
    }
    latest = {"ticker": "AAPL", "as_of": "2026-10-11", "reporting_basis": "consolidated US GAAP",
              "latest_reported_period": "Q3 FY2026 (ended 2026-06-27; 10-Q filed 2026-07-31)",
              "authoritative_source": "../financial-data.json (SEC XBRL with provenance)",
              "metrics": metrics}
    (base / "financials/latest.json").write_text(json.dumps(latest, indent=2) + "\n")

    manifest = json.loads((base / "filing-manifest.json").read_text())
    sources = [{"id": f"sec-{r['accession']}", "tier": 1, "type": r["form"], "period_end": r.get("period_end"),
                "filed": r.get("filed"), "url": r["url"], "retrieved_at": manifest.get("retrieved_at_utc"),
                "local_raw": "raw/ (git-ignored)"} for r in manifest["records"]]
    (base / "evidence/sources.json").write_text(json.dumps(sources, indent=2) + "\n")

    market = json.loads((base / "market-data.json").read_text())
    rows = [[m["date"][:10], "", "", "", round(m["close"], 2), "", m["source"], m["retrieved_at_utc"]]
            for m in market if m["ticker"] == "AAPL"]
    _write_csv(base / "market/prices.csv",
               ["date", "open", "high", "low", "close", "volume", "source", "retrieved_at"], rows)


def migrate_pl() -> None:
    base = RESEARCH / "PL"
    d = json.loads((base / "filings-data.json").read_text())
    h1 = d["six_months_ended_2026_07_31"]
    liq = d["liquidity_and_capital"]
    g = d["guidance_as_of_2026_09_03"]
    src10q = f"SEC 10-Q {d['latest_filing']['accession']} filed {d['latest_filing']['filed']} via filings-data.json"
    rows = [["H1 FY2027", "2026-07-31", k, v, "USD millions" if not k.endswith("_pct") else "%",
             "consolidated US GAAP", "Calculation" if k.startswith("normalized") else "Fact", src10q]
            for k, v in h1.items() if isinstance(v, (int, float))]
    _write_csv(base / "financials/historical.csv",
               ["period", "period_end", "metric", "value", "unit", "basis", "classification", "source"], rows)
    metrics = {
        "revenue_growth_yoy_pct": _metric(h1["revenue_yoy_pct"], "H1 FY2027", "%", "Fact", src10q),
        "q2_revenue_growth_yoy_pct": _metric(h1["q2_revenue_yoy_pct"], "Q2 FY2027", "%", "Fact", src10q),
        "gaap_gross_margin_pct": _metric(56.6, "Q2 FY2027", "%", "Fact",
                                         "PL-analysis-2026-10-11.md (SEC 10-Q / earnings 8-K)",
                                         "H1 GAAP gross margin 55.2%; prior-year Q2 57.6%."),
        "rpo_change_vs_fy_end_pct": _metric(round((h1["rpo"] / h1["rpo_at_fy_end"] - 1) * 100, 2),
                                            "2026-07-31 vs 2026-01-31", "%", "Calculation", src10q),
        "rpo_yoy_pct": _metric(None, "2026-07-31 vs 2025-07-31", "%", "Fact", src10q,
                               "Year-over-year RPO not captured in local data."),
        "rpo_12m_conversion_pct": _metric(h1["rpo_expected_within_12_months_pct"], "2026-07-31", "%", "Fact", src10q),
        "capex_pct_revenue": _metric(round(h1["total_capex"] / h1["revenue"] * 100, 2), "H1 FY2027", "%",
                                     "Calculation", src10q),
        "fcf_ex_deferred_revenue": _metric(h1["normalized_fcf_ex_deferred_revenue_inflow"], "H1 FY2027",
                                           "USD millions", "Calculation", src10q,
                                           "Timing sensitivity, not a GAAP figure or forecast."),
        "sbc_pct_revenue": _metric(round(h1["stock_based_compensation"] / h1["revenue"] * 100, 2), "H1 FY2027",
                                   "%", "Calculation", src10q),
        "diluted_shares_yoy_pct": _metric(None, "latest vs prior year", "%", "Fact", src10q,
                                          "Fully diluted share count history not captured locally."),
        "fy2027_revenue_reported": _metric(None, "FY2027 (ends 2027-01-31)", "USD millions", "Fact",
                                           "pending FY2027 10-K", f"Guidance {g['fy2027_revenue_low']}-{g['fy2027_revenue_high']}."),
        "cash_plus_short_term_investments": _metric(liq["cash_plus_short_term_investments"], "2026-07-31",
                                                    "USD millions", "Fact", src10q),
        "convertible_notes_principal": _metric(liq["convertible_notes_principal_due_2030"], "2026-07-31",
                                               "USD millions", "Fact", src10q),
        "total_shares": _metric(liq["total_shares_2026_08_27"], "2026-08-27", "shares", "Fact", src10q),
    }
    latest = {"ticker": "PL", "as_of": d["as_of"], "reporting_basis": d["reporting"]["basis"],
              "latest_reported_period": f"Q2 FY2027 (ended {d['latest_filing']['period_end']}; "
                                        f"10-Q filed {d['latest_filing']['filed']})",
              "authoritative_source": "../filings-data.json", "metrics": metrics}
    (base / "financials/latest.json").write_text(json.dumps(latest, indent=2) + "\n")
    sources = [
        {"id": f"sec-{d['latest_filing']['accession']}", "tier": 1, "type": "10-Q",
         "period_end": d["latest_filing"]["period_end"], "filed": d["latest_filing"]["filed"],
         "url": d["latest_filing"]["url"]},
        {"id": f"sec-{d['related_earnings_8k']['accession']}", "tier": 1, "type": "8-K (earnings, Item 2.02)",
         "filed": d["related_earnings_8k"]["filed"], "url": d["related_earnings_8k"]["earnings_exhibit_url"]},
        {"id": "sec-fy2026-10k", "tier": 1, "type": "10-K", "period_end": "2026-01-31",
         "url": d["source_urls"]["fy2026_10k"]},
    ] + [{"id": f"event-{e['date']}", "tier": 1, "type": "issuer announcement", "date": e["date"],
          "description": e["event"], "url": e["source"]} for e in d["post_quarter_events"]]
    (base / "evidence/sources.json").write_text(json.dumps(sources, indent=2) + "\n")
    _write_csv(base / "market/prices.csv",
               ["date", "open", "high", "low", "close", "volume", "source", "retrieved_at"],
               [["2026-10-09", "", "", "", 17.18, "",
                 "FT Markets NYSE close, cross-checked; PL-analysis-2026-10-11.md", "2026-10-11"]])


if __name__ == "__main__":
    migrate_aapl()
    migrate_pl()
    print("AAPL and PL derived state files regenerated")
