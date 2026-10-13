"""Level 4 research command center tests (offline).

Covers KPI registry (+ company override), management semantic diff, guidance
normalization and guidance-vs-actual (definition mismatch → not_evaluable), event
classifier, research queue, priority engine, stale detector, catalyst calendar,
dashboard, enhanced monthly review, no BUY / SELL execution, cross-company priority,
and Level 3 / PL / RKLB / AAPL regressions on the committed research state."""
import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalyst_calendar as cal  # noqa: E402
import guidance_tracker as gt  # noqa: E402
import kpi_registry as kr  # noqa: E402
import level4_common as l4  # noqa: E402
import management_semantic_diff as msd  # noqa: E402
import monthly_research_review as mrr  # noqa: E402
import research_command_center as cc  # noqa: E402
import research_dashboard as dash  # noqa: E402
import research_event_classifier as clf  # noqa: E402
import research_event_detector as det  # noqa: E402
import research_priority as prio  # noqa: E402
import research_queue as rq  # noqa: E402
import research_state as rs  # noqa: E402
import stale_research as sr  # noqa: E402


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix in (".yaml", ".yml"):
        path.write_text(yaml.safe_dump(data, sort_keys=False))
    else:
        path.write_text(json.dumps(data, indent=1))


def _metric(v, **kw):
    return {"value": v, **kw}


def _history(quarters):
    """quarters: list of (period, end, {metric: value})."""
    return {"units": "USD millions", "fiscal_year_ends": ["2025-12-31"], "annual": [],
            "quarters": [{"period": p, "period_end": e,
                          "metrics": {k: _metric(v, form="10-Q", filed=f"{e[:4]}-{int(e[5:7]) % 12 + 1:02d}-10", accn=f"A{p}")
                                      for k, v in m.items()}} for p, e, m in quarters]}


def _prices(path: Path, start_close=10.0, n=300, last_jump=None, start="2025-08-01"):
    from datetime import date, timedelta
    d0 = date.fromisoformat(start)
    rows, c, i, d = [], start_close, 0, d0
    while i < n:
        if d.weekday() < 5:
            rows.append([d.isoformat(), c, c, c, c, 1_000_000, "test", "t"])
            i += 1
            c = round(c * 1.001, 4)
        d += timedelta(days=1)
    if last_jump:
        rows[-1][4] = round(rows[-2][4] * (1 + last_jump / 100), 4)
        rows[-1][5] = 5_000_000
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close", "volume", "source", "retrieved_at"])
        w.writerows(rows)
    return rows


def _company(root: Path, t: str, *, importance="high", research_role="Core", as_of="2026-10-01",
             components=None, valuation_conf="medium"):
    base = root / "research" / t
    comps = components or {
        "per_share_dilution": {"importance": importance, "status": "supported", "evidence": ["Fact: x (SEC 10-Q)"],
                               "last_updated": as_of, "next_check": "10-Q", "invalidation_condition": "x"},
        "revenue_growth": {"importance": "high", "status": "supported", "evidence": ["Fact: y (SEC 10-Q)"],
                           "last_updated": as_of, "next_check": "10-Q", "invalidation_condition": "y"}}
    _write(base / "thesis/current.yaml", {"ticker": t, "as_of": as_of, "action": "WATCH", "research_role": research_role,
                                          "valuation_confidence": valuation_conf, "components": comps,
                                          "next_catalysts": ["Debt conversion window 2026-11-01 to 2026-11-30 (SEC 10-Q).",
                                                             "Q3 results (earnings 8-K 2026-08-05)."]})
    _write(base / "valuation/latest.json", {"as_of": as_of, "price": 10.0, "price_date": as_of,
                                            "methods": {"dcf": {"bear": 5, "base": 9, "bull": 14}},
                                            "valuation_map": {"zones": [{"low": None, "high": 5, "interpretation": "below all modeled bear values"},
                                                                        {"low": 5, "high": 9, "interpretation": "between bear and base estimates"},
                                                                        {"low": 9, "high": 14, "interpretation": "between base and bull estimates"},
                                                                        {"low": 14, "high": None, "interpretation": "above all modeled bull values"}]}})
    _write(base / "snapshots" / f"{as_of}.json", {"ticker": t, "as_of": as_of, "retrospective": False,
                                                   "financials": {"latest_quarter": "Q2 FY2026", "latest_filed": "2026-08-10"},
                                                   "rules": {}, "management": {"promises": {}}})
    (base / "reports").mkdir(parents=True, exist_ok=True)
    (base / "reports" / f"{as_of}-change-report.md").write_text("# report\n")
    return base


def _submissions(base: Path, filings):
    recent = {"form": [f[0] for f in filings], "filingDate": [f[1] for f in filings],
              "reportDate": [f[2] if len(f) > 2 else f[1] for f in filings],
              "accessionNumber": [f"0000-{i}" for i in range(len(filings))],
              "primaryDocument": ["x.htm"] * len(filings), "items": [f[3] if len(f) > 3 else "" for f in filings]}
    _write(base / "raw/submissions.json", {"cik": "123", "filings": {"recent": recent}})


def _tmp_root():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    shutil.copytree(ROOT / "config", root / "config")
    return tmp, root


# --------------------------------------------------------------------------- 1-2 KPI registry

class KpiRegistryTests(unittest.TestCase):
    def test_registry_loading_layers(self):
        reg = kr.resolve("PL")
        self.assertEqual(reg["sector"], "space")
        self.assertEqual(reg["errors"], [])
        for k in ("revenue", "gross_margin", "fcf", "sbc_pct_revenue", "diluted_share_growth", "cash", "debt", "rpo",
                  "backlog", "capex", "government_mix"):
            self.assertIn(k, reg["kpis"])
        self.assertTrue(reg["kpis"]["revenue"]["required"])
        self.assertFalse(reg["kpis"]["backlog"]["required"])
        self.assertEqual(reg["kpis"]["rpo"]["concept"], "rpo")
        self.assertEqual(reg["kpis"]["backlog"]["concept"], "backlog")
        for sector in kr.SUPPORTED_SECTORS:
            self.assertTrue(kr.load_layer(sector), sector)

    def test_company_override_missing_unavailable_and_concepts(self):
        tmp, root = _tmp_root()
        with tmp:
            base = root / "research/ZZZ"
            _write(base / "financials/history.json", _history([("Q1 FY2026", "2026-03-31", {"revenue": 100.0, "rpo": 50.0})]))
            _write(base / "config/kpis.yaml", {
                "sector": "space", "disable": ["satellite_commissioning"],
                "kpis": {"backlog_wrong": {"name": "x", "unit": "USD millions", "concept": "backlog",
                                           "sources": [{"type": "sec_history", "metric": "rpo"}]},
                         "contract_value": {"name": "Contract value", "original_name": "Total contract value",
                                            "definition": "company TCV", "unit": "USD millions", "sources": []}},
                "values": [{"kpi": "contract_value", "period": "Q1 FY2026", "date": "2026-03-31", "value": 75,
                            "source": "8-K", "source_type": "issuer earnings release"},
                           {"kpi": "contract_value", "period": "Q1 FY2026", "value": 1, "unit": "%"}]})
            out = kr.build("ZZZ", root, "2026-10-13")
            self.assertNotIn("satellite_commissioning", out["coverage"])
            self.assertTrue(any("cannot be sourced from metric 'rpo'" in e for e in out["errors"]))
            self.assertTrue(any("manual unit '%'" in e for e in out["errors"]))
            rows = {(r["kpi"], str(r["value"])) for r in out["rows"]}
            self.assertIn(("contract_value", "75"), rows)
            self.assertIn(("backlog", "unavailable"), rows)          # missing → unavailable, never 0
            self.assertNotIn(("backlog", "0"), rows)
            self.assertNotIn(("backlog_wrong", "50.0"), rows)         # RPO never fills a backlog concept
            self.assertIn("Total contract value", next(r["notes"] for r in out["rows"] if r["kpi"] == "contract_value"))
            self.assertIn("gross_margin", out["required_unavailable"])
            self.assertTrue(out["review_required"])


# --------------------------------------------------------------------------- 3 semantic diff

class SemanticDiffTests(unittest.TestCase):
    def test_claims_and_findings(self):
        tmp, root = _tmp_root()
        with tmp:
            base = root / "research/SEM"
            _write(base / "config/kpis.yaml", {"milestone_subjects": ["Rocket"]})
            _write(base / "management/statements.json", [
                {"period": "Q1 FY2026", "date": "2026-05-01", "topic": "margins", "verbatim": True, "source": "u1",
                 "statement": "Margins should improve in H2 2026 as volumes scale."},
                {"period": "Q1 FY2026", "date": "2026-05-01", "topic": "product_launch", "verbatim": True, "source": "u1",
                 "statement": "We expect the Rocket first launch in the second half of 2026."},
                {"period": "Q2 FY2026", "date": "2026-08-01", "topic": "product_launch", "verbatim": True, "source": "u2",
                 "statement": "Rocket first launch is now targeted for Q2 2027 after a test anomaly."},
                {"period": "Q2 FY2026", "date": "2026-08-01", "topic": "demand", "verbatim": True, "source": "u2",
                 "statement": "Customer demand remained strong with a record pipeline."}])
            _write(base / "management/guidance.json", [
                {"issued": "2026-05-01", "period": "FY2026", "metric": "revenue", "low": 100, "high": 110, "unit": "USD millions", "statement": "a", "source": "u1"},
                {"issued": "2026-08-01", "period": "FY2026", "metric": "revenue", "low": 95, "high": 100, "unit": "USD millions", "statement": "b", "source": "u2"}])
            out = msd.run("SEM", root, "2026-10-13", use_releases=False)
            q = next(c for c in out["claims"] if c["claim_type"] == "qualitative_guidance")
            self.assertIsNone(q["lower"])
            self.assertIsNone(q["upper"])                 # "should improve in H2" never becomes a number
            self.assertEqual(q["timing"], "H2 2026")
            self.assertEqual(q["direction"], "up")
            dims = {f["dimension"]: f for f in out["findings"]}
            self.assertEqual(dims["quantitative_guidance"]["kind"], "lowered")
            self.assertEqual(dims["quantitative_guidance"]["CONFIDENCE"], "high")
            self.assertEqual(dims["timing"]["kind"], "slipped")
            for f in out["findings"]:
                for k in ("FACT", "CHANGE", "INTERPRETATION", "CONFIDENCE"):
                    self.assertIn(k, f)
                self.assertNotIn("fundamentals deteriorated", (f["CHANGE"] + f["INTERPRETATION"]).lower())
                if f["dimension"] in ("confidence_shift", "customer_demand", "bottleneck"):
                    self.assertEqual(f["CONFIDENCE"], "low")
            self.assertTrue((base / "management/semantic-diff.md").exists())


# --------------------------------------------------------------------------- 4-6 guidance

RELEASE = """Third Quarter 2026 Guidance   For the third quarter of 2026, Acme expects:
 • Revenue between $250 million and $265 million.
 • GAAP Gross Margins between 29% and 31%.
 • Non-GAAP Gross Margins between 35% and 37%.
 • Adjusted EBITDA loss of between $17 million and $23 million.
 • Basic Weighted Average Common Shares Outstanding of 641 million, including approximately 41 million of preferred.
 See "Use of Non-GAAP Financial Measures" below. Stock-based compensation is currently expected to range from $18 million to $20 million in Q3 2026."""


class GuidanceTests(unittest.TestCase):
    def test_guidance_normalization(self):
        g = {x["metric"]: x for x in gt.parse_bullet_guidance(RELEASE, "2026-08-10", "u")}
        self.assertEqual((g["revenue"]["low"], g["revenue"]["high"], g["revenue"]["unit"]), (250, 265, "USD millions"))
        self.assertEqual(g["revenue"]["period"], "Q3 FY2026")
        self.assertEqual((g["gross_margin"]["low"], g["gross_margin"]["unit"]), (29, "%"))
        self.assertEqual(g["non_gaap_gross_margin"]["low"], 35)
        self.assertEqual((g["adjusted_ebitda"]["low"], g["adjusted_ebitda"]["high"]), (-23, -17))
        self.assertEqual((g["basic_shares_guided"]["low"], g["basic_shares_guided"]["unit"]), (641, "millions of shares"))
        self.assertEqual((g["sbc"]["low"], g["sbc"]["high"]), (18, 20))

    def _setup(self, root, guidance_metrics):
        base = root / "research/GVA"
        _write(base / "financials/history.json", _history([
            ("Q2 FY2026", "2026-06-30", {"revenue": 240.0, "gross_margin_pct": 30.5, "basic_shares": 600.0, "capex": 30.0})]))
        _write(base / "management/guidance.json", [
            {"issued": "2026-05-07", "period": "Q2 FY2026", "metric": m, "low": lo, "high": hi, "unit": u, "statement": m, "source": "u"}
            for m, lo, hi, u in (("revenue", 225, 240, "USD millions"), ("gross_margin", 29, 31, "%"),
                                 ("basic_shares_guided", 629, 629, "millions of shares"), ("capex", 20, 25, "USD millions"),
                                 ("non_gaap_gross_margin", 35, 37, "%"))] +
            [{"issued": "2026-08-10", "period": "Q3 FY2026", "metric": "revenue", "low": 250, "high": 265,
              "unit": "USD millions", "statement": "r3", "source": "u"}])
        _write(base / "config/kpis.yaml", {"guidance_metrics": guidance_metrics})
        return base

    def test_guidance_vs_actual_and_definition_audit(self):
        tmp, root = _tmp_root()
        with tmp:
            self._setup(root, {
                "revenue": {"company_definition": "GAAP revenue", "actual": {"type": "sec_history", "metric": "revenue"},
                            "comparison_basis": "gaap_match"},
                "gross_margin": {"company_definition": "GAAP GM", "actual": {"type": "sec_history", "metric": "gross_margin_pct"},
                                 "comparison_basis": "gaap_match"},
                "basic_shares_guided": {"company_definition": "basic incl. preferred", "actual": {"type": "sec_history", "metric": "basic_shares"},
                                        "actual_definition": "XBRL basic excl. preferred", "comparison_basis": "definition_mismatch"},
                "capex": {"company_definition": "PP&E + software", "actual": {"type": "sec_history", "metric": "capex"},
                          "comparison_basis": "definition_match", "kind": "spending_plan"}})
            out = gt.track("GVA", root, "2026-10-13", parse=False)
            by = {r["guidance"]["metric"] + "|" + r["guidance"]["period"]: r for r in out["rows"] if r.get("guidance")}
            self.assertEqual(by["revenue|Q2 FY2026"]["status"], "delivered")
            self.assertEqual(by["revenue|Q2 FY2026"]["resolution_confidence"], "high")
            self.assertEqual(by["revenue|Q3 FY2026"]["status"], "pending")            # not yet reported
            self.assertEqual(by["gross_margin|Q2 FY2026"]["status"], "delivered")
            # metric definition mismatch → never auto-resolved
            self.assertEqual(by["basic_shares_guided|Q2 FY2026"]["status"], "not_evaluable")
            self.assertIn("definition mismatch", by["basic_shares_guided|Q2 FY2026"]["resolution_rule"])
            # no recorded definition → not_evaluable (comparison basis unverified)
            self.assertEqual(by["non_gaap_gross_margin|Q2 FY2026"]["status"], "not_evaluable")
            self.assertEqual(by["non_gaap_gross_margin|Q2 FY2026"]["comparison_basis"], "comparison_basis_mismatch")
            # spending plan overspent by 20% → deviation, labelled as not by itself negative
            self.assertEqual(by["capex|Q2 FY2026"]["status"], "missed")
            self.assertIn("not by itself a negative signal", by["capex|Q2 FY2026"]["resolution_rule"])
            prom = json.loads((root / "research/GVA/management/promises.json").read_text())
            for p in prom:
                for k in ("metric_definition", "comparison_basis", "resolution_confidence", "actual_source"):
                    self.assertIn(k, p)
            self.assertIn("Guidance vs Actual", (root / "research/GVA/management/guidance-vs-actual.md").read_text())

    def test_no_guidance_message(self):
        tmp, root = _tmp_root()
        with tmp:
            _write(root / "research/NOG/financials/history.json", _history([]))
            out = gt.track("NOG", root, "2026-10-13", parse=False)
            self.assertEqual(out["message"], "No explicit evaluable management guidance found.")
            self.assertEqual(json.loads((root / "research/NOG/management/promises.json").read_text()), [])


# --------------------------------------------------------------------------- 7 classifier

def _event(t, et, ts="2026-10-10", **d):
    return {"event_id": det.event_id(t, et, ts, json.dumps(d, sort_keys=True)), "ticker": t, "event_type": et,
            "timestamp": ts, "source": "s", "source_type": "SEC 10-Q", "evidence_quality": "HIGH", "details": d}


class ClassifierTests(unittest.TestCase):
    def test_categories(self):
        ctx = {"filing_dates": set(), "dilution_core": True, "large_move_pct": 15}
        c = lambda e: clf.classify(e, ctx)  # noqa: E731
        self.assertEqual(c(_event("X", "sec_10q", form="10-Q"))["category"], "A")
        self.assertIn("/update-stock X", c(_event("X", "sec_10q", form="10-Q"))["required_workflow"])
        self.assertEqual(c(_event("X", "earnings_release"))["category"], "A")
        cut = c(_event("X", "guidance_update", metric="revenue", direction="lowered", previous=[1, 2], current=[0, 1]))
        self.assertEqual((cut["category"], cut["immediate_alert"], cut["alert_meaning"]), ("A", True, "REASSESS"))
        self.assertEqual(c(_event("X", "guidance_update", metric="capex", direction="lowered", spending_plan=True))["category"], "B")
        self.assertEqual(c(_event("X", "major_contract", description="award"))["category"], "B")
        self.assertEqual(c(_event("X", "capital_raise", form="424B5"))["severity"], "high")
        mv = c(_event("X", "major_price_move", move_pct=16.0))
        self.assertEqual((mv["category"], mv["severity"]), ("C", "medium"))
        self.assertIn("no full DCF", mv["required_workflow"])
        near = clf.classify(_event("X", "major_price_move", "2026-10-10", move_pct=16.0),
                            {**ctx, "filing_dates": {"2026-10-09"}})
        self.assertEqual(near["severity"], "low")
        self.assertEqual(c(_event("X", "insider_filings", form4=3, form144=1))["category"], "D")
        for e in (mv, cut):
            for k in ("event_type", "ticker", "timestamp", "source", "severity", "required_workflow", "reason"):
                self.assertIn(k, e)

    def test_detector_sec_and_market(self):
        tmp, root = _tmp_root()
        with tmp:
            base = _company(root, "DET", as_of="2026-10-01")
            _submissions(base, [("10-Q", "2026-11-09", "2026-09-30"), ("4", "2026-11-05"), ("4", "2026-11-06"),
                                ("8-K", "2026-11-09", "2026-11-09", "2.02,9.01"), ("10-Q", "2026-08-10", "2026-06-30")])
            _prices(base / "market/prices.csv", n=300, last_jump=20, start="2025-09-01")
            res = det.detect("DET", root, "2026-11-10")
            types = [e["event_type"] for e in res["events"]]
            self.assertIn("sec_10q", types)
            self.assertIn("earnings_release", types)
            self.assertEqual(types.count("insider_filings"), 1)          # aggregated
            self.assertIn("major_price_move", types)
            self.assertNotIn("2026-08-10", [e["timestamp"] for e in res["events"] if e["event_type"] == "sec_10q"])
            again = det.detect("DET", root, "2026-11-10")                 # incremental: nothing new
            self.assertFalse([e for e in again["events"] if e["event_type"].startswith("sec_")])
            st = l4.load_scan_state("DET", root)
            for k in ("last_checked", "last_filing", "last_price_update"):
                self.assertTrue(st[k])


# --------------------------------------------------------------------------- 8 queue

class QueueTests(unittest.TestCase):
    def test_queue_lifecycle(self):
        tmp, root = _tmp_root()
        with tmp:
            ctx = {"filing_dates": set(), "dilution_core": False, "large_move_pct": 15}
            c_ev = {**clf.classify(_event("Q", "major_price_move", "2026-10-01", move_pct=20.0), ctx), "priority": "MEDIUM"}
            d_ev = {**clf.classify(_event("Q", "insider_filings", "2026-10-02", form4=1, form144=0), ctx), "priority": "LOW"}
            q = rq.enqueue([c_ev, d_ev], root)
            rq.save(q, root)
            self.assertEqual(len(rq.open_items(root)), 2)
            q = rq.enqueue([c_ev], root)                                   # idempotent
            self.assertEqual(q["last_added"], 0)
            a_ev = {**clf.classify(_event("Q", "sec_10q", "2026-10-05", form="10-Q"), ctx), "priority": "HIGH"}
            q = rq.enqueue([a_ev], root)
            rq.save(q, root)
            st = {i["event_type"]: i["status"] for i in rq.load(root)["items"]}
            self.assertEqual(st["major_price_move"], "superseded")
            self.assertEqual(st["insider_filings"], "superseded")
            self.assertEqual(st["sec_10q"], "pending")
            self.assertEqual(set(rq.load(root)["items"][0]) >= {"event_id", "ticker", "event_type", "detected_at",
                                                               "priority", "required_workflow", "source", "reason", "status"}, True)
            rq.set_status(a_ev["event_id"], "processing", "", root)
            self.assertEqual(rq.complete_for_ticker("Q", "2026-10-13", root=root), 1)
            self.assertEqual(rq.open_items(root), [])
            with self.assertRaises(ValueError):
                rq.set_status(a_ev["event_id"], "bought", "", root)


# --------------------------------------------------------------------------- 9, 15 priority

class PriorityTests(unittest.TestCase):
    def test_event_rules_and_ticker_ranking(self):
        tmp, root = _tmp_root()
        with tmp:
            _company(root, "HHH", as_of="2026-10-10", valuation_conf="low")
            _company(root, "LLL", as_of="2026-10-10")
            _company(root, "OLD", as_of="2026-01-02")
            ctx = {"filing_dates": set(), "dilution_core": False, "large_move_pct": 15}
            ev = lambda t, et, **d: clf.classify(_event(t, et, **d), ctx)  # noqa: E731
            h = prio.prioritize_events("HHH", [ev("HHH", "sec_10q", form="10-Q")], root, "2026-10-13")[0]
            self.assertEqual(h["priority"], "HIGH")
            self.assertTrue(h["priority_reasons"])
            trig = prio.prioritize_events("HHH", [ev("HHH", "monitoring_trigger", rule="a", condition="dilution"),
                                                  ev("HHH", "monitoring_trigger", rule="b", condition="capex")], root, "2026-10-13")
            self.assertTrue(all(x["priority"] == "HIGH" for x in trig))
            self.assertIn("multiple monitoring rules", trig[0]["priority_reasons"][0])
            low_ev = {**ev("LLL", "major_contract", description="x"), "evidence_quality": "LOW"}
            lo = prio.prioritize_events("LLL", [low_ev], root, "2026-10-13")[0]
            self.assertEqual(lo["priority"], "LOW")
            self.assertTrue(any("LOW evidence" in r for r in lo["priority_reasons"]))
            # price move without evidence stays LOW; an old review raises a C event one level
            small = ev("LLL", "major_price_move", move_pct=9.0)
            self.assertEqual(prio.prioritize_events("LLL", [small], root, "2026-10-13")[0]["priority"], "LOW")
            self.assertEqual(prio.prioritize_events("OLD", [ev("OLD", "major_price_move", move_pct=9.0)], root,
                                                    "2026-10-13")[0]["priority"], "MEDIUM")
            # cross-company ranking
            rows = [prio.ticker_priority("LLL", [], None, root), prio.ticker_priority("HHH", [h], None, root)]
            ranked = prio.rank(rows)
            self.assertEqual([r["ticker"] for r in ranked], ["HHH", "LLL"])
            self.assertEqual(ranked[1]["reasons"], ["no meaningful state change"])
            doc = prio.write(ranked, root, "2026-10-13")
            self.assertEqual(doc["tickers"][0]["rank"], 1)
            self.assertTrue((root / "research/queue/priority-history.csv").exists())

    def test_watchlist_override(self):
        tmp, root = _tmp_root()
        with tmp:
            _company(root, "OVR")
            _write(root / "config/watchlist.yaml", {"tickers": [{"ticker": "OVR", "priority_override": "high"}]})
            r = prio.ticker_priority("OVR", [], None, root)
            self.assertEqual(r["priority"], "HIGH")
            self.assertTrue(any("analyst override" in x for x in r["reasons"]))


# --------------------------------------------------------------------------- 10 stale

class StaleTests(unittest.TestCase):
    def test_new_filing_and_old_review(self):
        tmp, root = _tmp_root()
        with tmp:
            base = _company(root, "STL", as_of="2026-05-01")
            _submissions(base, [("10-Q", "2026-11-09", "2026-09-30"), ("10-Q", "2026-08-10", "2026-06-30")])
            _prices(base / "market/prices.csv", start="2025-09-01")
            r = sr.check("STL", root, "2026-11-15", calendar=[])
            self.assertEqual(r["severity"], "HIGH")
            self.assertTrue(r["new_filing_unprocessed"])
            self.assertTrue(any("not in state" in x for x in r["reasons"]))
            self.assertTrue(any("valuation price" in x for x in r["reasons"]))
            fresh = _company(root, "FRS", as_of="2026-10-10")
            _prices(fresh / "market/prices.csv", start="2025-12-20", n=200)
            f = sr.check("FRS", root, "2026-10-13", calendar=[])
            self.assertFalse(f["new_filing_unprocessed"])
            self.assertNotEqual(f["severity"], "HIGH")


# --------------------------------------------------------------------------- 11 calendar

class CalendarTests(unittest.TestCase):
    def test_calendar_precision(self):
        tmp, root = _tmp_root()
        with tmp:
            base = _company(root, "CAL", as_of="2026-10-01")
            _write(base / "financials/history.json", _history([("Q1 FY2026", "2026-03-31", {"revenue": 1.0}),
                                                              ("Q2 FY2026", "2026-06-30", {"revenue": 1.0})]))
            (base / "market").mkdir(parents=True, exist_ok=True)
            with (base / "market/events.csv").open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["event_date", "event_type", "description", "source", "timing"])
                w.writerow(["2026-05-06", "8-K 2.02 earnings", "Q1", "u", "amc"])
                w.writerow(["2026-08-05", "8-K 2.02 earnings", "Q2", "u", "amc"])
            rows = cal.build(["CAL"], root, "2026-10-13")
            earn = next(r for r in rows if r["event"].startswith("Earnings release"))
            self.assertEqual(earn["expected_date"], "2026-11")                    # month, not a guessed day
            self.assertEqual(earn["confidence"], "low")
            self.assertTrue(any(r["date_precision"].startswith("deadline") for r in rows))
            conv = next(r for r in rows if r["event"].startswith("Debt conversion"))
            self.assertEqual((conv["window_start"], conv["expected_date"]), ("2026-11-01", "2026-11-30"))
            self.assertFalse(any(r["event"].startswith("Q3 results") for r in rows))  # citation date ignored
            for k in cal.HEADER:
                self.assertIn(k, earn)
            self.assertTrue((root / "research/calendar/upcoming.csv").exists())


# --------------------------------------------------------------------------- 12-14 dashboard / monthly / no orders

class CommandCenterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        shutil.copytree(ROOT / "config", cls.root / "config")
        for t in ("PL", "RKLB", "AAPL"):
            shutil.copytree(ROOT / "research" / t, cls.root / "research" / t,
                            ignore=shutil.ignore_patterns("raw", "scan-state.json"))  # simulate a first scan
        cls.scan = cc.scan(cls.root, "2026-10-13", skip_prices=True)
        cls.doc = dash.build(cls.root, "2026-10-13")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_dashboard_generation(self):
        text = (self.root / "research/dashboard/current.md").read_text()
        self.assertIn("| Ticker | Action | Priority | Thesis trend | Valuation | Expectation gap | Triggers | Next catalyst | Last review |", text)
        for t in ("PL", "RKLB", "AAPL"):
            self.assertIn(f"| {t} |", text)
        for k in ("thesis_improved_most", "thesis_deteriorated_most", "expectation_gap_narrowed_most",
                  "valuation_cheaper", "price_up_fundamentals_lagging", "stale_research"):
            self.assertIn(k, self.doc["answers"])
        for r in self.doc["companies"]:
            self.assertIn(r["confidence"]["overall"], ("low", "medium", "high"))
            self.assertTrue(r["confidence"]["reasons"])
            self.assertNotIn("%", " ".join(r["confidence"]["reasons"]).replace("% ", ""))  # no fake precise percentages
        self.assertTrue((self.root / "research/dashboard/current.json").exists())

    def test_monthly_review_level4_sections(self):
        res = mrr.run("2026-10", self.root)
        text = res["text"]
        for i in range(1, 23):
            self.assertIn(f"## {i}. ", text)
        for h in ("Research Priority Changes", "Thesis Improvements", "Thesis Deteriorations", "Expectation Gap Changes",
                  "Guidance Delivered / Missed", "New Monitoring Triggers", "Valuation Re-Rating", "Research Staleness",
                  "Next Month Calendar", "Top 5 Research Tasks", "Deprioritized Names"):
            self.assertIn(h, text)
        self.assertIn("No explicit evaluable management guidance found.", text)   # AAPL

    def test_no_buy_sell_execution(self):
        q = rq.load(self.root)
        self.assertTrue(q["items"])
        l4.assert_no_orders(q)
        l4.assert_no_orders(self.doc)
        for t in ("PL", "RKLB", "AAPL"):
            for item in q["items"]:
                self.assertNotRegex(item["required_workflow"].upper(), r"\b(BUY|SELL)\b(?!.*NOT)")
        for et in list(clf.TARGETED) + list(clf.MARKET_TYPES) + ["sec_10q", "earnings_release", "thesis_invalidation",
                                                                 "insider_filings", "guidance_update"]:
            e = clf.classify(_event("X", et, move_pct=20.0, direction="lowered", metric="revenue"),
                             {"filing_dates": set(), "dilution_core": True, "large_move_pct": 15})
            self.assertFalse(e.get("alert_meaning") not in (None, "REASSESS"))
        with self.assertRaises(ValueError):
            l4.assert_no_orders({"required_workflow": "SELL 100 shares at market"})
        self.assertNotIn("buy_range", json.dumps(self.doc))

    def test_cross_company_priority(self):
        pri = json.loads((self.root / "research/queue/priorities.json").read_text())
        ranks = [r["rank"] for r in pri["tickers"]]
        self.assertEqual(ranks, sorted(ranks))
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        levels = [order[r["priority"]] for r in pri["tickers"]]
        self.assertEqual(levels, sorted(levels))
        self.assertEqual(pri["tickers"][0]["ticker"], "PL")                # 3 distinct triggered conditions
        for r in pri["tickers"]:
            self.assertTrue(r["reasons"])


# --------------------------------------------------------------------------- 16-19 regressions

class Level3RegressionTests(unittest.TestCase):
    def test_level3_capabilities_preserved(self):
        for s in ("pending", "delivered", "partially_delivered", "missed", "superseded"):
            self.assertIn(s, rs.PROMISE_STATUSES)
        for s in ("delayed", "not_evaluable"):
            self.assertIn(s, rs.PROMISE_STATUSES)
        self.assertIn("## Current action", rs.status("PL"))
        self.assertTrue(rs.check_rules("PL"))
        for cmd in ("init-stock", "update-stock", "deep-stock", "watch-stock", "monthly-research",
                    "scan-research", "research-queue", "research-dashboard", "stale-research"):
            self.assertTrue((ROOT / ".claude/commands" / f"{cmd}.md").exists(), cmd)
        for skill in ("equity-research-orchestrator", "management-change", "research-review"):
            link = ROOT / ".agents/skills" / skill
            self.assertTrue(link.is_symlink() and (link / "SKILL.md").exists(), skill)
        for t in ("PL", "RKLB", "AAPL"):
            latest = json.loads((ROOT / f"research/{t}/valuation/latest.json").read_text())
            for k in rs.FORBIDDEN_DECISION_KEYS:
                self.assertNotIn(k, latest)


class PLRegressionTests(unittest.TestCase):
    def test_pl_kpis(self):
        cov = json.loads((ROOT / "research/PL/financials/kpi-coverage.json").read_text())["coverage"]
        for k in ("rpo", "backlog", "government_mix", "revenue", "gross_margin", "capex", "diluted_share_growth", "cash"):
            self.assertEqual(cov[k]["status"], "available", k)
        self.assertEqual(cov["backlog"]["latest_value"], 814.9)
        self.assertNotEqual(cov["backlog"]["latest_value"], cov["rpo"]["latest_value"])   # backlog ≠ RPO
        self.assertEqual(cov["launch_cadence"]["status"], "unavailable")

    def test_pl_capex_promises_definition_checked(self):
        prom = json.loads((ROOT / "research/PL/management/promises.json").read_text())
        capex = [p for p in prom if (p.get("guidance") or {}).get("metric") == "capex"]
        self.assertTrue(capex)
        for p in capex:
            self.assertEqual(p["comparison_basis"], "definition_match")
            self.assertIn("purchases of property and equipment", p["metric_definition"]["company"])
            if p["status"] in ("missed", "partially_delivered"):
                self.assertIn("spending-plan deviation", p["resolution_rule"])
            if p["status"] not in ("pending", "superseded"):
                self.assertIn(p["resolution_confidence"], ("high", "medium"))
        rev = [p for p in prom if (p.get("guidance") or {}).get("metric") == "revenue" and p["status"] == "delivered"]
        self.assertGreaterEqual(len(rev), 10)

    def test_pl_semantic_and_calendar(self):
        sd = json.loads((ROOT / "research/PL/management/semantic-diff.json").read_text())
        rev = [f for f in sd["findings"] if f["dimension"] == "quantitative_guidance" and f.get("metric") == "revenue"
               and f.get("period") == "FY2027"]
        self.assertTrue(rev and all(f["kind"] == "raised" for f in rev))
        rows = l4.read_csv(ROOT / "research/calendar/upcoming.csv")
        pl = [r for r in rows if r["ticker"] == "PL" and r["event"].startswith("Earnings release")]
        self.assertTrue(pl and pl[0]["date_precision"].startswith("month"))


class RKLBRegressionTests(unittest.TestCase):
    def test_rklb_guidance_and_promises(self):
        g = json.loads((ROOT / "research/RKLB/management/guidance.json").read_text())
        self.assertTrue(any(x["period"] == "Q3 FY2026" and x["metric"] == "revenue" and (x["low"], x["high"]) == (250, 265)
                            for x in g))
        prom = json.loads((ROOT / "research/RKLB/management/promises.json").read_text())
        shares = [p for p in prom if (p.get("guidance") or {}).get("metric") == "basic_shares_guided" and p["status"] != "pending"]
        self.assertTrue(shares and all(p["status"] == "not_evaluable" for p in shares))
        rev = [p for p in prom if (p.get("guidance") or {}).get("metric") == "revenue" and p["status"] == "delivered"]
        self.assertGreaterEqual(len(rev), 8)
        neutron = [p for p in prom if p["promise_id"].startswith("RKLB-milestone-neutron")]
        self.assertEqual(neutron[0]["status"], "delayed")
        self.assertEqual(neutron[-1]["status"], "pending")

    def test_rklb_space_kpis(self):
        cov = json.loads((ROOT / "research/RKLB/financials/kpi-coverage.json").read_text())
        self.assertEqual(cov["sector"], "space")
        for k in ("backlog", "launch_cadence", "revenue", "gross_margin", "cash", "capex"):
            self.assertEqual(cov["coverage"][k]["status"], "available", k)
        self.assertEqual(cov["coverage"]["government_mix"]["status"], "unavailable")


class AAPLRegressionTests(unittest.TestCase):
    def test_aapl_mature_kpis_and_no_guidance(self):
        cov = json.loads((ROOT / "research/AAPL/financials/kpi-coverage.json").read_text())
        self.assertEqual(cov["sector"], "consumer")
        for k in ("rpo", "launch_cadence", "satellites_deployed", "arr"):
            self.assertNotIn(k, cov["coverage"])                                  # no space / software KPIs
        for k in ("gross_margin", "operating_margin", "services_revenue", "fcf", "cfo", "diluted_share_growth", "buybacks"):
            self.assertEqual(cov["coverage"][k]["status"], "available", k)
        gva = json.loads((ROOT / "research/AAPL/management/guidance-vs-actual.json").read_text())
        self.assertEqual(gva["message"], "No explicit evaluable management guidance found.")
        latest = json.loads((ROOT / "research/AAPL/valuation/latest.json").read_text())
        self.assertEqual(latest["reverse_dcf"]["status"], "quantified")
        gap = dash.gap_view("AAPL", ROOT)
        self.assertTrue(gap["label"].startswith("Wide"))


if __name__ == "__main__":
    unittest.main()
