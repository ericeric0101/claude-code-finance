"""Level 3 engine tests: history builder, state diff, management / promises,
valuation history, monthly review, INIT / UPDATE pipelines and PL / AAPL regressions.
All tests are offline (synthetic SEC facts or cached repo state)."""
import copy
import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import assumption_history_check as ahc  # noqa: E402
import baseline_draft as bd  # noqa: E402
import build_fundamental_history as bfh  # noqa: E402
import build_management_history as bmh  # noqa: E402
import build_valuation_history as bvh  # noqa: E402
import migrate_legacy_state  # noqa: E402
import monthly_research_review as mrr  # noqa: E402
import research_pipeline as rp  # noqa: E402
import research_state as rs  # noqa: E402
import state_diff  # noqa: E402

# --------------------------------------------------------------------------- synthetic SEC facts
# Calendar fiscal year; quarters Q1..Q4. Revenue grows 10 per quarter.
QE = {1: ("01-01", "03-31"), 2: ("04-01", "06-30"), 3: ("07-01", "09-30"), 4: ("10-01", "12-31")}
FILED = {1: "05-10", 2: "08-10", 3: "11-10"}


def _fact(start, end, val, form, filed, accn):
    f = {"end": end, "val": val, "accn": accn, "form": form, "filed": filed, "fy": int(end[:4]), "fp": "X"}
    if start:
        f["start"] = start
    return f


def synthetic_facts(years=range(2019, 2026), last_quarter=(2026, 2), drop_capex=False, use_revenues_tag_for=None):
    rev, cfo, capex, gp, oi, ni, sh, cash, rpo = ([] for _ in range(9))
    base = 100.0
    qrev = {}
    for y in list(years) + [last_quarter[0]]:
        for q in range(1, 5):
            if (y, q) > last_quarter:
                break
            qrev[(y, q)] = base
            base += 10
    for (y, q), r in qrev.items():
        s, e = f"{y}-{QE[q][0]}", f"{y}-{QE[q][1]}"
        if q < 4:
            filed, form, accn = f"{y}-{FILED[q]}", "10-Q", f"Q{y}{q}"
            rev.append(_fact(s, e, r * 1e6, form, filed, accn))
            gp.append(_fact(s, e, r * 0.5e6, form, filed, accn))
            oi.append(_fact(s, e, r * 0.1e6, form, filed, accn))
            ni.append(_fact(s, e, r * 0.05e6, form, filed, accn))
            sh.append(_fact(s, e, 100e6 + q * 1e6, form, filed, accn))
            # cash-flow items are reported year-to-date only (as in most 10-Qs)
            ytd = sum(qrev[(y, k)] for k in range(1, q + 1))
            cfo.append(_fact(f"{y}-01-01", e, ytd * 0.2e6, form, filed, accn))
            if not drop_capex:
                capex.append(_fact(f"{y}-01-01", e, ytd * 0.05e6, form, filed, accn))
            cash.append(_fact(None, e, 50e6 + r * 1e6, form, filed, accn))
            rpo.append(_fact(None, e, 500e6 + r * 1e6, form, filed, accn))
        else:
            filed, form, accn = f"{y + 1}-02-20", "10-K", f"K{y}"
            fy = sum(qrev[(y, k)] for k in range(1, 5))
            s0 = f"{y}-01-01"
            rev.append(_fact(s0, e, fy * 1e6, form, filed, accn))
            gp.append(_fact(s0, e, fy * 0.5e6, form, filed, accn))
            oi.append(_fact(s0, e, fy * 0.1e6, form, filed, accn))
            ni.append(_fact(s0, e, fy * 0.05e6, form, filed, accn))
            sh.append(_fact(s0, e, 104e6, form, filed, accn))
            cfo.append(_fact(s0, e, fy * 0.2e6, form, filed, accn))
            if not drop_capex:
                capex.append(_fact(s0, e, fy * 0.05e6, form, filed, accn))
            cash.append(_fact(None, e, 50e6 + r * 1e6, form, filed, accn))
            rpo.append(_fact(None, e, 500e6 + r * 1e6, form, filed, accn))
    rev_tag = {"RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": rev}}}
    if use_revenues_tag_for:
        keep = [f for f in rev if f["end"] not in use_revenues_tag_for]
        moved = [f for f in rev if f["end"] in use_revenues_tag_for]
        rev_tag = {"RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": keep}},
                   "Revenues": {"units": {"USD": moved}}}
    g = {**rev_tag,
         "GrossProfit": {"units": {"USD": gp}}, "OperatingIncomeLoss": {"units": {"USD": oi}},
         "NetIncomeLoss": {"units": {"USD": ni}},
         "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": cfo}},
         "WeightedAverageNumberOfDilutedSharesOutstanding": {"units": {"shares": sh}},
         "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": cash}},
         "RevenueRemainingPerformanceObligation": {"units": {"USD": rpo}}}
    if not drop_capex:
        g["PaymentsToAcquirePropertyPlantAndEquipment"] = {"units": {"USD": capex}}
    dei = {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
        _fact(None, f.get("end"), 105e6, f["form"], f["filed"], f["accn"]) for f in rev if f["form"] == "10-Q"]}}}
    return {"cik": 1, "entityName": "Synthetic Co", "facts": {"us-gaap": g, "dei": dei}}


def q(history, period):
    return next(r for r in history["quarters"] if r["period"] == period)


def a(history, period):
    return next(r for r in history["annual"] if r["period"] == period)


# --------------------------------------------------------------------------- 1-3 history builder

class FundamentalHistoryTests(unittest.TestCase):
    def test_generic_baseline_builder(self):
        h = bfh.build_history(synthetic_facts())
        cov = bfh.coverage(h)
        self.assertTrue(cov["meets_5y"] and cov["meets_8q"])
        fy = a(h, "FY2025")["metrics"]
        self.assertAlmostEqual(fy["revenue"]["value"], sum(100 + 10 * i for i in range(24, 28)))
        self.assertEqual(fy["revenue"]["tag"], "RevenueFromContractWithCustomerExcludingAssessedTax")
        self.assertEqual(fy["revenue"]["form"], "10-K")
        self.assertAlmostEqual(fy["gross_margin_pct"]["value"], 50.0)
        self.assertAlmostEqual(fy["fcf_margin_pct"]["value"], 15.0)
        self.assertEqual(h["quarters"][-1]["period"], "Q2 FY2026")

    def test_quarterly_standalone_derivation(self):
        h = bfh.build_history(synthetic_facts())
        q2 = q(h, "Q2 FY2025")["metrics"]
        self.assertAlmostEqual(q2["cfo"]["value"], q2["revenue"]["value"] * 0.2)  # H1 YTD - Q1, not H1
        self.assertIn("minus", q2["cfo"]["derived"])
        q4 = q(h, "Q4 FY2025")["metrics"]
        self.assertAlmostEqual(q4["revenue"]["value"], 100 + 10 * 27)  # FY - 9M
        self.assertIsNone(q4["diluted_shares"])  # weighted averages are never differenced
        # YTD value with a different fiscal-year start is not differenced
        facts = synthetic_facts()
        for f in facts["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"]:
            if f["end"] == "2025-06-30":
                f["start"] = "2024-12-15"
        self.assertIsNone(q(bfh.build_history(facts), "Q2 FY2025")["metrics"]["cfo"])

    def test_missing_tag_and_fallback_and_precedence(self):
        h = bfh.build_history(synthetic_facts(drop_capex=True, use_revenues_tag_for={"2025-06-30"}))
        m = q(h, "Q2 FY2025")["metrics"]
        self.assertIsNone(m["capex"])          # missing, not zero
        self.assertIsNone(m["fcf"])
        self.assertEqual(m["revenue"]["tag"], "Revenues")
        self.assertTrue(m["revenue"]["tag_fallback"])
        self.assertIsNone(m["backlog"])        # company KPI without a configured tag
        facts = synthetic_facts()
        rev = facts["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"]
        orig = next(f for f in rev if f["end"] == "2025-03-31")
        rev.append({**orig, "val": orig["val"] + 5e6, "form": "10-Q/A", "filed": "2025-07-01", "accn": "AMEND"})
        rev.append({**orig, "val": 1.0, "form": "8-K", "filed": "2025-08-01", "accn": "EIGHTK"})
        h2 = bfh.build_history(facts)
        self.assertEqual(q(h2, "Q1 FY2025")["metrics"]["revenue"]["accn"], "AMEND")  # latest amendment wins
        h3 = bfh.build_history(facts, as_of="2025-06-01")                             # amendment not yet filed
        self.assertEqual(q(h3, "Q1 FY2025")["metrics"]["revenue"]["accn"], orig["accn"])


# --------------------------------------------------------------------------- 4 transitions, rules

class ThesisAndRuleTests(unittest.TestCase):
    def test_thesis_transition_classification(self):
        c = rs.classify_transition
        self.assertEqual(c("uncertain", "improving"), "positive")
        self.assertEqual(c("improving", "supported"), "positive")
        self.assertEqual(c("supported", "improving"), "neutral")
        self.assertEqual(c("supported", "weakening"), "negative")
        self.assertEqual(c("weakening", "invalidated"), "negative")
        self.assertEqual(c("supported", "supported"), "unchanged")
        self.assertEqual(c(None, "supported"), "new")
        statuses = rs.THESIS_STATUSES
        self.assertEqual(len(rs.THESIS_TRANSITIONS), len(statuses) * (len(statuses) - 1))
        prev = {"as_of": "2026-01-01", "thesis": {"x": {"status": "supported", "evidence_fp": "a"}}}
        cur = {"as_of": "2026-02-01", "thesis": {"x": {"status": "improving", "evidence_fp": "a"}}}
        d = state_diff.diff_states(prev, cur)
        self.assertFalse(d["negative"])
        self.assertIn("[neutral] x: supported → improving", " ".join(d["thesis"]))

    def test_market_and_invalidation_rules_mean_reassess(self):
        res = rs.evaluate_market_rules({"reassess_price": [10, 20]}, 21.0, 15.0)
        self.assertEqual([r["state"] for r in res], ["not_triggered", "triggered"])
        self.assertEqual(res[1]["action"], "REASSESS")
        inval = {"rules": [
            {"id": "gm2q", "checks": [{"metric": "gm", "warning": "<50%", "consecutive_quarters": 2}]},
            {"id": "any", "logic": "any", "checks": [{"metric": "a", "warning": "<0"}, {"metric": "b", "warning": "<0"}]},
            {"id": "manual", "state": "not_triggered"}]}
        out = {r["rule"]: r for r in rs.evaluate_invalidation(inval, {"a": {"value": 1}, "b": {"value": -1}},
                                                                {"gm": [55, 49, 48]})}
        self.assertEqual(out["gm2q"]["state"], "triggered")
        self.assertEqual(out["any"]["state"], "triggered")
        self.assertEqual(out["manual"]["evaluation"], "manual")
        for r in out.values():
            self.assertNotIn(r.get("action"), ("BUY", "SELL"))

    def test_status_has_catalysts_and_change_date(self):
        text = rs.status("PL")
        for section in ("## Current action", "## Thesis summary", "## Valuation summary", "## Expectation gap",
                        "## Monitoring rules", "## Next catalysts", "Latest change date"):
            self.assertIn(section, text)


# --------------------------------------------------------------------------- 5 legacy migration

class LegacyMigrationTests(unittest.TestCase):
    def test_legacy_migration_cannot_overwrite_newer_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for t in ("PL", "AAPL"):
                shutil.copytree(ROOT / "research" / t, root / "research" / t,
                                ignore=shutil.ignore_patterns("raw"))
            files = [p for p in (root / "research").rglob("*") if p.is_file()]
            before = {p: p.read_bytes() for p in files}
            migrate_legacy_state.set_root(root)
            try:
                migrate_legacy_state.migrate_pl()
                migrate_legacy_state.migrate_aapl()
            finally:
                migrate_legacy_state.set_root(ROOT)
            self.assertEqual([str(p) for p in files if p.read_bytes() != before[p]], [])
            with (root / "research/PL/market/prices.csv").open() as fh:
                self.assertGreater(len(list(csv.DictReader(fh))), 1000)
        r = subprocess.run([sys.executable, str(ROOT / "scripts/migrate_legacy_state.py")],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--legacy-one-time", r.stderr)


# --------------------------------------------------------------------------- 6-9 state diff

def _snap(**kw):
    s = {"as_of": "2026-01-01", "retrospective": False, "action": "WATCH", "valuation_confidence": "low",
         "financials": {"latest_quarter": "Q1 FY2026", "quarter": {"revenue": 100.0, "gross_margin_pct": 50.0},
                        "ttm": {}, "other": {}},
         "management": {"statement_count": 1, "latest_period": "Q1 FY2026", "guidance": {}, "promises": {}},
         "thesis": {}, "valuation": {"price": 10.0, "methods": {"DCF": {"bear": 5, "base": 10, "bull": 20}},
                                     "map_position": "within the base-value spread across methods",
                                     "percentiles": {}},
         "expectation_gap": {}, "rules": {}, "next_catalysts": []}
    for k, v in kw.items():
        s[k] = v
    return s


class StateDiffTests(unittest.TestCase):
    def test_state_diff_detects_financial_change(self):
        prev = _snap()
        cur = _snap(as_of="2026-04-01", financials={"latest_quarter": "Q2 FY2026", "ttm": {}, "other": {},
                                                    "quarter": {"revenue": 120.0, "gross_margin_pct": 45.0}})
        d = state_diff.diff_states(prev, cur)
        self.assertTrue(any("revenue: 100.00 → 120.00" in x for x in d["positive"]))
        self.assertTrue(any("gross_margin_pct" in x for x in d["negative"]))
        self.assertTrue(any("Q1 FY2026 → Q2 FY2026" in x for x in d["financials"]))

    def test_state_diff_detects_promise_status_change(self):
        prom = {"P1": {"status": "pending", "claim": "rev 10-12", "actual": None}}
        prev = _snap(management={"statement_count": 1, "latest_period": "Q1", "guidance": {}, "promises": prom})
        cur_prom = {"P1": {"status": "missed", "claim": "rev 10-12", "actual": 8.0, "rule": "below low end"},
                    "P2": {"status": "pending", "claim": "new", "actual": None}}
        cur = _snap(as_of="2026-04-01",
                    management={"statement_count": 3, "latest_period": "Q2", "promises": cur_prom,
                                "guidance": {"FY2026|revenue": {"low": 400, "high": 420, "issued": "2026-03-01", "unit": "USD millions"}}})
        prev["management"]["guidance"] = {"FY2026|revenue": {"low": 380, "high": 400, "issued": "2026-01-01", "unit": "USD millions"}}
        d = state_diff.diff_states(prev, cur)
        self.assertTrue(any("P1: pending → missed" in x for x in d["negative"]))
        self.assertTrue(any("新承諾 P2" in x for x in d["promises"]))
        self.assertTrue(any("guidance raised FY2026 revenue" in x for x in d["positive"]))
        self.assertEqual(d["promise_counts"], {"missed": 1, "pending": 1})

    def test_state_diff_detects_valuation_zone_change(self):
        prev = _snap()
        cur = _snap(as_of="2026-02-01", valuation={**_snap()["valuation"], "price": 25.0,
                                                   "map_position": "above all modeled bull values"})
        d = state_diff.diff_states(prev, cur)
        self.assertTrue(any("valuation zone: within the base-value spread across methods → above all modeled bull values"
                            in x for x in d["valuation"]))
        self.assertFalse(d["positive"] or d["negative"])  # price alone is not a fundamental change
        text = state_diff.render_report("ZZZ", d, cur)
        for h in ("## Positive", "## Negative", "## Unchanged", "## Financial changes", "## Management wording",
                  "## Promise tracker", "## Thesis changes", "## Valuation changes", "## Expectation gap",
                  "## Monitoring triggers", "## Action", "## Confidence", "## Next catalysts"):
            self.assertIn(h, text)

    def test_expectation_gap_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rs.init_company("ZZZ", root=root)
            vpath = root / "research/ZZZ/valuation/latest.json"
            exp = {"internal_base": {"g": 0.25}, "bull": {"g": 0.35}}
            for d, implied in (("2026-01-01", 0.36), ("2026-02-01", 0.30), ("2026-03-01", 0.302)):
                vpath.write_text(json.dumps({"as_of": d, "price": 1, "valuation_confidence": "low",
                                             "expectations": {**exp, "market_implied": {"g": implied}}}))
                rows = rs.record_expectation_gap("ZZZ", root)
            self.assertEqual([r["direction"] for r in rows], ["no prior state", "narrowing", "stable"])
            rs.record_expectation_gap("ZZZ", root)  # same date again: upsert, not duplicate
            self.assertEqual(len(rs.read_gap_history(root / "research/ZZZ/valuation/expectation-gap-history.csv")), 3)
            self.assertEqual(rows[1]["gap_vs_bull"], "-0.05")


# --------------------------------------------------------------------------- 10 valuation history

class ValuationHistoryTests(unittest.TestCase):
    def test_historical_valuation_no_lookahead(self):
        facts = synthetic_facts()
        builds = [(fd, bfh.build_history(facts, as_of=fd)) for fd in bvh.filing_dates(facts)]
        builds = [(fd, h) for fd, h in builds if h["quarters"]]
        shares = bvh.cover_shares(facts)
        before = bvh.snapshot_at(builds, shares, "2025-08-09")   # Q2 10-Q filed 2025-08-10
        after = bvh.snapshot_at(builds, shares, "2025-08-10")
        self.assertEqual(before["period"], "Q1 FY2025")
        self.assertEqual(after["period"], "Q2 FY2025")
        self.assertLessEqual(before["filed"], "2025-08-09")
        self.assertIsNone(bvh.snapshot_at(builds, shares, "2010-01-01"))
        row = bvh.row_for("2025-08-10", "x", ("2025-08-10", 10.0), after)
        self.assertAlmostEqual(row["ev_sales"], round(row["ev_m"] / row["revenue_ttm_m"], 2))
        self.assertIsNone(bvh._ratio(-5, 10))  # negative numerator / denominator: not meaningful
        pct = bvh.percentiles([{"date": f"2025-{m:02d}-28", "kind": "month_end", "ev_sales": float(m),
                                "ev_ebit": None, "pe": None, "p_fcf": None} for m in range(1, 13)],
                              {"date": "2025-12-28", "ev_sales": 6.0, "ev_ebit": None, "pe": None, "p_fcf": None},
                              "2025-01-01")
        self.assertEqual(pct["ev_sales"]["1y"], 50.0)
        self.assertIsNone(pct["ev_sales"]["3y"])
        self.assertIn("insufficient", pct["ev_sales"]["3y_note"])


# --------------------------------------------------------------------------- management / promises

class ManagementTests(unittest.TestCase):
    TEXT = ("Outlook\nFor the third quarter of fiscal year 2027, ending October 31, 2026, Acme expects revenue to be "
            "in the range of approximately $101 million to $105 million. Adjusted EBITDA loss is expected to be in "
            "the range of approximately ($6) to ($1) million for the quarter. Capital expenditures are expected to "
            "be in the range of approximately $30 million and $37 million for the quarter. For the full fiscal year "
            "2027, Acme expects revenue to be in the range of approximately $430 million to $441 million. "
            "Non-GAAP gross margin is expected to be in the range of approximately 55% to 57%.\nAcme has not reconciled")

    def test_guidance_parsing_and_promise_lifecycle(self):
        g = bmh.parse_outlook(self.TEXT, "2026-09-03")
        got = {(x["period"], x["metric"]): (x["low"], x["high"]) for x in g}
        self.assertEqual(got[("Q3 FY2027", "revenue")], (101.0, 105.0))
        self.assertEqual(got[("Q3 FY2027", "adjusted_ebitda")], (-6.0, -1.0))
        self.assertEqual(got[("FY2027", "non_gaap_gross_margin")], (55.0, 57.0))
        self.assertEqual(bmh.judge("revenue", 101, 105, 104)[0], "delivered")
        self.assertEqual(bmh.judge("revenue", 101, 105, 100)[0], "partially_delivered")
        self.assertEqual(bmh.judge("revenue", 101, 105, 90)[0], "missed")
        history = {"quarters": [{"period": "Q3 FY2027", "metrics": {"revenue": {"value": 106.0, "filed": "2026-12-05",
                                                                             "form": "10-Q", "accn": "X"}}}],
                   "annual": []}
        for x in g:
            x["source"] = "test"
        before = bmh.update_promises("ACME", [], g, history, {}, "2026-11-01")
        self.assertTrue(all(p["status"] == "pending" for p in before))  # outcome not yet public
        after = bmh.update_promises("ACME", before, g, history, {}, "2026-12-10")
        rev = next(p for p in after if p["promise_id"] == "ACME-2026-09-03-q3-revenue")
        self.assertEqual((rev["status"], rev["actual_result"], rev["resolved_date"]), ("delivered", 106.0, "2026-12-05"))
        ebitda = next(p for p in after if p["promise_id"] == "ACME-2026-09-03-q3-ebitda")
        self.assertEqual(ebitda["status"], "pending")  # non-GAAP actual not available
        changes = bmh.guidance_changes(g + [{**g[3], "issued": "2026-12-05", "low": 440.0, "high": 450.0}])
        self.assertEqual(changes[0]["change"], "raised")
        self.assertIn("not a credibility score", bmh.promise_counts(after)["caveat"])


# --------------------------------------------------------------------------- 11 monthly review

class MonthlyReviewTests(unittest.TestCase):
    def test_monthly_review_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for t, cur_kw in (("AAA", {"rules": {"r1": {"state": "triggered", "type": "fundamental"}}}), ("BBB", {})):
                d = root / "research" / t
                (d / "thesis").mkdir(parents=True)
                (d / "thesis/current.yaml").write_text(yaml.safe_dump({"ticker": t, "components": {}}))
                (d / "snapshots").mkdir()
                prev = _snap(as_of="2026-09-15", rules={"r1": {"state": "not_triggered", "type": "fundamental"}})
                cur = _snap(as_of="2026-10-20", **cur_kw) if cur_kw else _snap(as_of="2026-10-20",
                            rules={"r1": {"state": "not_triggered", "type": "fundamental"}})
                (d / "snapshots/2026-09-15.json").write_text(json.dumps(prev))
                (d / "snapshots/2026-10-20.json").write_text(json.dumps(cur))
            res = mrr.run("2026-10", root)
            self.assertEqual(res["priorities"], {"AAA": "High", "BBB": "Low"})
            text = (root / "research/reviews/2026-10-monthly-review.md").read_text()
            for i in range(1, 12):
                self.assertIn(f"## {i}. ", text)
            self.assertIn("AAA: newly triggered → REASSESS: r1", text)


# --------------------------------------------------------------------------- 12-13 INIT / UPDATE

def _offline_company(root: Path, ticker: str, facts, filings=()):
    raw = root / "research" / ticker / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "companyfacts.json").write_text(json.dumps(facts))
    recent = {"form": [f[0] for f in filings], "filingDate": [f[1] for f in filings],
              "reportDate": [f[1] for f in filings], "accessionNumber": [f"A-{i}" for i in range(len(filings))],
              "primaryDocument": ["x.htm"] * len(filings), "items": [""] * len(filings),
              "acceptanceDateTime": [""] * len(filings)}
    (raw / "submissions.json").write_text(json.dumps({"filings": {"recent": recent}}))
    m = root / "research" / ticker / "market"
    m.mkdir(parents=True, exist_ok=True)
    with (m / "prices.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close", "volume", "source", "retrieved_at"])
        for y in range(2019, 2027):
            for mo in range(1, 13):
                if (y, mo) <= (2026, 9):
                    w.writerow([f"{y}-{mo:02d}-15", 10, 10, 10, 10 + (y - 2019), 1000, "test", "test"])


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_creates_baseline_not_empty_shell(self):
        _offline_company(self.root, "SYN", synthetic_facts(), [("10-Q", "2026-08-10")])
        res = rp.init("SYN", "1", "Synthetic Co", self.root, offline=True, skip_prices=True, as_of="2026-09-30")
        base = self.root / "research/SYN"
        self.assertTrue(rs._read_json(base / "financials/coverage.json")["meets_8q"])
        thesis = yaml.safe_load((base / "thesis/current.yaml").read_text())
        self.assertTrue(thesis["components"] and thesis["draft_auto"])
        latest = json.loads((base / "valuation/latest.json").read_text())
        self.assertEqual(set(next(iter(latest["methods"].values()))), {"bear", "base", "bull"})
        for k in rs.FORBIDDEN_DECISION_KEYS:
            self.assertNotIn(k, json.dumps(latest))
        self.assertTrue((base / "valuation/historical-multiples.csv").exists())
        self.assertTrue((base / "valuation/assumption-check.json").exists())
        self.assertTrue(yaml.safe_load((base / "monitoring/rules.yaml").read_text())["monitoring"]["fundamental"])
        self.assertEqual(len(state_diff.list_snapshots("SYN", self.root)), 1)
        self.assertTrue(Path(res["report"]).exists())
        self.assertEqual(len([s for s in res["steps"] if s["step"] > 0]), 15)

    def test_update_preserves_old_history(self):
        _offline_company(self.root, "SYN", synthetic_facts(last_quarter=(2026, 1)), [("10-Q", "2026-05-10")])
        rp.init("SYN", "1", "Synthetic Co", self.root, offline=True, skip_prices=True, as_of="2026-06-01")
        base = self.root / "research/SYN"
        hist_rows = (base / "financials/historical.csv").read_text().splitlines()
        _offline_company(self.root, "SYN", synthetic_facts(last_quarter=(2026, 2)),
                         [("10-Q", "2026-05-10"), ("10-Q", "2026-08-10")])
        res = rp.update("SYN", "1", self.root, offline=True, skip_prices=True, as_of="2026-09-01")
        self.assertEqual([s["as_of"] for s in state_diff.list_snapshots("SYN", self.root)], ["2026-06-01", "2026-09-01"])
        self.assertEqual(len(json.loads((base / "thesis/history.json").read_text())), 2)
        dates = {r["as_of"] for r in rs.read_valuation_history(base / "valuation/history.csv")}
        self.assertEqual(dates, {"2026-06-01", "2026-09-01"})
        new_rows = set((base / "financials/historical.csv").read_text().splitlines())
        self.assertTrue(set(hist_rows) <= new_rows)
        self.assertIn("Q1 FY2026 → Q2 FY2026", res["text"])
        self.assertIn("revenue:", res["text"])
        self.assertTrue((base / "reports/2026-09-01-change-report.md").exists())


# --------------------------------------------------------------------------- 14-15 regressions

class PLRegressionTests(unittest.TestCase):
    base = ROOT / "research/PL"

    def test_pl_history_and_assumption_check(self):
        h = json.loads((self.base / "financials/history.json").read_text())
        cov = bfh.coverage(h)
        self.assertTrue(cov["meets_5y"] and cov["meets_8q"])
        self.assertTrue({"FY2022", "FY2023", "FY2024", "FY2025", "FY2026"} <= set(cov["annual_periods"]))
        self.assertAlmostEqual(a(h, "FY2026")["metrics"]["revenue"]["value"], 307.727, places=3)
        q1, q2 = q(h, "Q1 FY2027")["metrics"], q(h, "Q2 FY2027")["metrics"]
        filings = json.loads((self.base / "filings-data.json").read_text())["six_months_ended_2026_07_31"]
        self.assertAlmostEqual(q1["revenue"]["value"] + q2["revenue"]["value"], filings["revenue"], places=2)
        self.assertAlmostEqual(q1["capex"]["value"] + q2["capex"]["value"], filings["total_capex"], places=2)
        self.assertAlmostEqual(q1["cfo"]["value"] + q2["cfo"]["value"], filings["cash_from_operations"], places=2)
        self.assertAlmostEqual(q2["rpo"]["value"], filings["rpo"], delta=0.05)  # XBRL rounds to 0.1m
        chk = {(c["scenario"], c["assumption"]): c["reading"]
               for c in json.loads((self.base / "valuation/assumption-check.json").read_text())["checks"]}
        self.assertEqual(chk[("base", "revenue_cagr_5y")], "reasonable")
        self.assertEqual(chk[("bull", "revenue_cagr_5y")], "aggressive")
        self.assertEqual(chk[("base", "fcf_margin_y5")], "aggressive")
        self.assertEqual(chk[("bull", "fcf_margin_y5")], "very aggressive")

    def test_pl_multi_period_state_and_histories(self):
        snaps = state_diff.list_snapshots("PL")
        self.assertGreaterEqual(len(snaps), 4)
        self.assertTrue(any(s["retrospective"] for s in snaps))
        for s in snaps:
            if s["retrospective"]:
                self.assertIsNone(s["action"])  # no fabricated past recommendation
        self.assertTrue(any(not s["retrospective"] and s["as_of"] == "2026-10-11" for s in snaps))
        stmts = json.loads((self.base / "management/statements.json").read_text())
        self.assertGreaterEqual(len({s["period"] for s in stmts if s.get("extraction") == "auto"}), 8)
        prom = json.loads((self.base / "management/promises.json").read_text())
        self.assertTrue({"delivered", "pending"} <= {p["status"] for p in prom})
        self.assertTrue(all("actual_result" in p and "resolved_date" in p for p in prom))
        with (self.base / "valuation/historical-multiples.csv").open() as fh:
            rows = [r for r in csv.DictReader(fh) if r["kind"] == "month_end"]
        self.assertGreaterEqual(len(rows), 36)
        self.assertTrue(all(r["fundamentals_filed"] <= r["date"] for r in rows))  # no look-ahead
        with (self.base / "market/fundamental-price-timeline.csv").open() as fh:
            self.assertGreaterEqual(len(list(csv.DictReader(fh))), 8)
        gaps = rs.read_gap_history(self.base / "valuation/expectation-gap-history.csv")
        self.assertGreaterEqual(len(gaps), 2)

    def test_pl_scenario_model_reproduces_stored_values(self):
        args = dict(rev0=435.5, multiple=None)
        v = lambda g, m, mult, r: bd.value_per_share(435.5, g, m, mult, r, 375, 410, -0.06)
        self.assertAlmostEqual(v(0.10, 0.08, 18, 0.12), 2.43, places=2)
        self.assertAlmostEqual(v(0.25, 0.20, 25, 0.105), 11.60, places=2)
        self.assertAlmostEqual(v(0.35, 0.25, 30, 0.095), 25.18, places=2)
        self.assertAlmostEqual(bd.solve_implied_cagr(17.18, 435.5, 0.20, 25, 0.105, 375, 410, -0.06), 0.361, places=3)
        del args


class AAPLRegressionTests(unittest.TestCase):
    def test_generic_builder_matches_extract_aapl(self):
        raw = ROOT / "research/AAPL/raw/companyfacts.json"
        if not raw.exists():
            self.skipTest("AAPL raw companyfacts not cached (git-ignored)")
        h = bfh.build_history(json.loads(raw.read_text()), as_of="2026-10-11")
        old = json.loads((ROOT / "research/AAPL/financial-data.json").read_text())
        pairs = (("revenue", "revenue"), ("net_income", "net_income"), ("cfo", "cfo"), ("capex", "capex_ppe"),
                 ("ebit", "operating_income"), ("sbc", "sbc"), ("diluted_shares", "diluted_shares"), ("cash", "cash"))
        checked = 0
        for olds, news in ((old["annual"], h["annual"]), (old["quarter_trend"], h["quarters"])):
            for rec in olds:
                new = next(r for r in news if r["period_end"] == rec["end"])["metrics"]
                for k, nk in pairs:
                    if k in rec:
                        self.assertAlmostEqual(bfh._v(new, nk), rec[k], delta=0.5, msg=f"{rec['label']} {k}")
                        checked += 1
        self.assertGreaterEqual(checked, 85)
        self.assertEqual(len(old["annual"]), 5)
        self.assertEqual(len(old["quarter_trend"]), 8)

    def test_aapl_valuation_features_preserved(self):
        base = ROOT / "research/AAPL"
        latest = json.loads((base / "valuation/latest.json").read_text())
        self.assertEqual(latest["reverse_dcf"]["status"], "quantified")
        self.assertAlmostEqual(latest["reverse_dcf"]["implied_growth"], 0.148, places=3)
        self.assertEqual(rs.catch_up(latest)["earnings"][1]["static_price_pe"], 32.5)
        self.assertEqual(latest["valuation_map"]["current_position"], "above all modeled bull values")
        for k in rs.FORBIDDEN_DECISION_KEYS:
            self.assertNotIn(k, json.dumps(latest))
        self.assertTrue(rs.read_valuation_history(base / "valuation/history.csv"))
        self.assertTrue((ROOT / "scripts/extract_aapl.py").exists())  # not deleted


if __name__ == "__main__":
    unittest.main()
