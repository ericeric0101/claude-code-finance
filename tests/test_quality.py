"""Research OS quality evaluation layer tests (offline).

Covers the quality event schema, auto-created pending events (scan / update / init /
monthly), human review, missed events, correction history, false positives / negatives,
summary aggregation, insufficient-sample handling, module and ticker attribution, the
no-hindsight-return rule, Level 4 regression, the monthly quality section and the
dashboard quality block."""
import csv
import inspect
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import monthly_research_review as mrr  # noqa: E402
import quality_log as ql  # noqa: E402
import quality_review as qr  # noqa: E402
import quality_summary as qs  # noqa: E402
import research_command_center as cc  # noqa: E402
import research_dashboard as dash  # noqa: E402
import research_pipeline as rp  # noqa: E402

DAY = "2026-10-13"


def _root():
    tmp = tempfile.TemporaryDirectory()
    return tmp, Path(tmp.name)


def _auto(root, ticker="PL", priority="HIGH", cls="B", eid=None, workflow="scan-research"):
    item = {"event_id": eid or f"{ticker}-{DAY}-x-{priority}{cls}", "ticker": ticker, "event_type": "major_contract",
            "priority": priority, "category": cls, "category_name": "TARGETED_UPDATE", "source": "issuer press release",
            "reason": "test", "details": {}, "timestamp": DAY}
    return ql.record_queue_items([item], DAY, workflow, root)["quality_event_ids"][0]


class SchemaTests(unittest.TestCase):
    def test_quality_event_schema(self):
        e = ql.new_event(workflow="update-stock", ticker="pl", event_id="PL-1", event_type="earnings_release", day=DAY,
                         system_output={"classification": "A", "priority": "HIGH", "guidance_items": 4},
                         references=["research/PL/reports/x.md"])
        ql.validate(e)
        for k in ("quality_event_id", "date", "ticker", "event_id", "event_type", "workflow", "system_output",
                  "human_review", "corrections", "references", "review_status"):
            self.assertIn(k, e)
        self.assertEqual(e["ticker"], "PL")
        self.assertEqual(e["review_status"], "pending")
        self.assertEqual(e["review_requirement"], "required")              # HIGH must be reviewed
        for f in ql.BOOL_FIELDS:
            self.assertEqual(e["human_review"][f], "unknown")              # explicit, never ""
        bad = json.loads(json.dumps(e))
        bad["human_review"]["priority_correct"] = ""
        with self.assertRaises(ql.QualityError):
            ql.validate(bad)
        with self.assertRaises(ql.QualityError):
            ql.new_event(workflow="nope", ticker="PL", event_id="x", event_type="y", day=DAY, system_output={})
        # CSV has all required columns and explicit tri-state values
        tmp, root = _root()
        with tmp:
            ql.record([e], root)
            with ql.log_path(root).open() as fh:
                rows = list(csv.DictReader(fh))
            for col in ("date", "ticker", "event_id", "event_type", "workflow", "source_reference",
                        "event_detected_correctly", "event_classification_correct", "priority_correct",
                        "guidance_extracted_correctly", "management_change_correct", "kpi_extraction_correct",
                        "promise_resolution_correct", "thesis_update_useful", "valuation_update_useful",
                        "monitoring_trigger_correct", "false_positive", "false_negative", "missed_information",
                        "manual_correction_required", "manual_correction_type", "research_value", "confidence",
                        "review_status", "reviewed_by", "reviewed_at", "notes"):
                self.assertIn(col, rows[0])
            self.assertEqual(rows[0]["priority_correct"], "unknown")
            self.assertNotIn("", [rows[0][c] for c in ("false_positive", "false_negative", "research_value")])


class AutoCreateTests(unittest.TestCase):
    def test_auto_create_pending_event(self):
        tmp, root = _root()
        with tmp:
            # the system may not self-grade: human fields passed as system output are dropped
            r = ql.record_workflow("update-stock", "PL", DAY, {"priority_correct": True, "thesis_update_useful": True,
                                                               "thesis_changed": True, "guidance_items": 3},
                                   ["research/PL/reports/x.md"], root=root)
            e = ql.get_event(r["quality_event_id"], root)
            self.assertEqual(e["review_status"], "pending")
            self.assertIsNone(e["reviewed_by"])
            self.assertEqual(e["human_review"]["priority_correct"], "unknown")
            self.assertEqual(e["human_review"]["thesis_update_useful"], "unknown")
            self.assertNotIn("priority_correct", e["system_output"])
            self.assertTrue(e["system_output"]["thesis_changed"])
            # idempotent: the same run does not create a duplicate
            ql.record_workflow("update-stock", "PL", DAY, {"guidance_items": 4}, [], root=root)
            self.assertEqual(len(ql.load_events(root)), 1)
            self.assertEqual(ql.load_events(root)[0]["system_output"]["guidance_items"], 4)
            # pipeline helper (used by init / update) records a pending event and never raises
            status, detail = rp.quality_event("init-stock", "RKLB", root, DAY, {"thesis_draft_auto": True}, [], [])
            self.assertEqual(status, "ok")
            self.assertIn("pending", detail)
        for fn in (rp.init, rp.update):
            self.assertIn("quality_event(", inspect.getsource(fn))

    def test_scan_and_monthly_create_events(self):
        tmp, root = _root()
        with tmp:
            shutil.copytree(ROOT / "config", root / "config")
            for t in ("PL", "RKLB", "AAPL"):
                shutil.copytree(ROOT / "research" / t, root / "research" / t,
                                ignore=shutil.ignore_patterns("raw", "scan-state.json"))
            out = cc.scan(root, DAY, skip_prices=True)
            q = json.loads((root / "research/queue/current.json").read_text())
            evs = ql.load_events(root)
            self.assertEqual(out["quality"]["added"], len(q["items"]))
            self.assertEqual({e["event_id"] for e in evs}, {i["event_id"] for i in q["items"]})
            self.assertTrue(all(e["review_status"] == "pending" for e in evs))
            hi = [e for e in evs if e["system_output"]["priority"] == "HIGH"]
            self.assertTrue(hi and all(e["review_requirement"] == "required" for e in hi))
            # a second scan with no new events adds a run-level event only
            out2 = cc.scan(root, DAY, skip_prices=True)
            self.assertEqual(len(out2["quality"]["quality_event_ids"]), 1)
            run_ev = ql.get_event(out2["quality"]["quality_event_ids"][0], root)
            self.assertEqual(run_ev["event_type"], "scan_run")
            n = len(ql.load_events(root))
            mrr.run("2026-10", root)
            monthly = [e for e in ql.load_events(root) if e["workflow"] == "monthly-research"]
            self.assertEqual(len(ql.load_events(root)), n + 1)
            self.assertEqual(monthly[0]["review_status"], "pending")


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = _root()
        self.qid = _auto(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_human_review_update(self):
        e = ql.review(self.qid, {"event_detected_correctly": "true", "priority_correct": "yes", "research_value": "high",
                                 "notes": "contract is material for the government-mix thesis"}, reviewer="CK",
                      root=self.root)
        self.assertEqual(e["review_status"], "reviewed")
        self.assertEqual(e["reviewed_by"], "CK")
        self.assertIs(e["human_review"]["priority_correct"], True)
        self.assertEqual(e["human_review"]["reviewed_priority"], "HIGH")
        self.assertEqual(e["human_review"]["research_value"], "HIGH")
        self.assertEqual(e["human_review"]["guidance_extracted_correctly"], "unknown")  # untouched = still unknown
        self.assertEqual(e["review_history"][-1]["by"], "CK")
        with self.assertRaises(ql.QualityError):
            ql.review(self.qid, {"priority_correct": "maybe"}, root=self.root)
        with self.assertRaises(ql.QualityError):
            ql.review(self.qid, {"made_up_field": "true"}, root=self.root)
        # CLI path
        rc = qr.main(["--root", str(self.root), "review", self.qid, "--thesis-update-useful", "not_applicable"])
        self.assertEqual(rc, 0)
        self.assertEqual(ql.get_event(self.qid, self.root)["human_review"]["thesis_update_useful"], "not_applicable")

    def test_correction_history(self):
        e = ql.review(self.qid, {"reviewed_priority": "MEDIUM"}, reason="routine contract extension, no thesis impact",
                      root=self.root)
        self.assertIs(e["human_review"]["priority_correct"], False)
        self.assertTrue(e["human_review"]["manual_correction_required"])
        ql.correct(self.qid, "classification", "C", "price-only item, no new filing", module="event_classifier",
                   root=self.root)
        corr = ql.load_corrections(self.root)
        self.assertEqual([c["field"] for c in corr], ["priority", "classification"])
        c = corr[0]
        for k in ("field", "system_value", "reviewed_value", "reason", "timestamp", "module", "ticker"):
            self.assertIn(k, c)
        self.assertEqual((c["before"], c["after"], c["module"]), ("HIGH", "MEDIUM", "priority_engine"))
        self.assertFalse(c["applied_to_rules"])                              # feedback only, no self-modification
        # corrections survive later reviews (append-only file + embedded copy)
        ql.review(self.qid, {"research_value": "LOW"}, root=self.root)
        self.assertEqual(len(ql.load_corrections(self.root)), 2)
        self.assertEqual(len(ql.get_event(self.qid, self.root)["corrections"]), 2)
        with self.assertRaises(ql.QualityError):
            ql.review(self.qid, {"reviewed_priority": "LOW"}, root=self.root)   # disagreement needs a reason
        with self.assertRaises(ql.QualityError):
            ql.correct(self.qid, "priority", "LOW", "", root=self.root)

    def test_false_positive_handling(self):
        e = ql.review(self.qid, {"false_positive": "true", "notes": "duplicate of the 8-K already in the queue"},
                      root=self.root)
        self.assertIs(e["human_review"]["false_positive"], True)
        self.assertIs(e["human_review"]["event_detected_correctly"], False)
        s = qs.summarize(self.root, "2026-10")
        self.assertEqual(s["event_detection"]["false_positives"], 1)
        self.assertEqual(s["event_detection"]["correct_detections"], 0)
        self.assertEqual(s["modules"]["event_detector"]["errors"], 1)


class MissedEventTests(unittest.TestCase):
    def test_missed_event_creation_and_false_negative(self):
        tmp, root = _root()
        with tmp:
            e = ql.add_missed_event(ticker="pl", event_date="2026-10-01", event_type="product_launch",
                                    source="https://investors.planet.com/x", why_material="Tanager-2 launch matters for "
                                    "the hyperspectral thesis component", expected_workflow="targeted-update",
                                    as_of=DAY, root=root)
            self.assertEqual(e["origin"], "manual_missed")
            self.assertIs(e["human_review"]["false_negative"], True)
            self.assertFalse(e["system_output"]["detected"])
            self.assertEqual(e["missed_event"]["expected_workflow"], "targeted-update")
            self.assertEqual(ql.load_corrections(root)[0]["module"], "event_detector")
            s = qs.summarize(root, "2026-10")
            self.assertEqual(s["event_detection"]["false_negatives"], 1)
            self.assertEqual(s["event_detection"]["missed_events"], 1)
            self.assertEqual(s["modules"]["event_detector"]["errors"], 1)     # counted once, not twice
            with self.assertRaises(ql.QualityError):                           # cannot be "missed" before it happened
                ql.add_missed_event(ticker="PL", event_date="2026-12-01", event_type="x", source="s",
                                    why_material="m", expected_workflow="w", as_of=DAY, root=root)
            rc = qr.main(["--root", str(root), "add-missed-event", "--ticker", "RKLB", "--event-date", "2026-10-02",
                          "--event-type", "capital_raise", "--source", "SEC 424B5", "--why-material",
                          "dilution is a core thesis component", "--expected-workflow", "targeted-update",
                          "--as-of", DAY])
            self.assertEqual(rc, 0)
            self.assertEqual(len(ql.list_events(root, ticker="RKLB")), 1)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = _root()
        tickers = ["PL", "PL", "PL", "RKLB", "RKLB", "AAPL"]
        self.ids = [_auto(self.root, t, "HIGH", "A", eid=f"{t}-{i}") for i, t in enumerate(tickers)]

    def tearDown(self):
        self.tmp.cleanup()

    def test_summary_aggregation(self):
        for i, qid in enumerate(self.ids):
            ql.review(qid, {"event_detected_correctly": True, "priority_correct": i != 0,
                            "classification_verdict": "correct" if i < 4 else "too_high",
                            "research_value": "HIGH" if i < 2 else "MEDIUM", "guidance_extracted_correctly": i != 3},
                      reason="test", root=self.root)
        res = qs.run("2026-10", self.root)
        s = res["summary"]
        self.assertTrue(Path(res["path"]).exists())
        self.assertEqual(s["coverage"]["events_reviewed"], 6)
        self.assertEqual(s["coverage"]["pending_reviews"], 0)
        self.assertEqual(s["priority"]["agreement"], {"numerator": 5, "denominator": 6, "value": round(5 / 6, 3)})
        self.assertEqual(s["classification"]["correct"], 4)
        self.assertEqual(s["classification"]["too_high"], 2)
        self.assertEqual(s["event_detection"]["precision"]["value"], 1.0)
        self.assertEqual(s["extraction"]["guidance_accuracy"]["numerator"], 5)
        self.assertEqual(s["research_value"]["HIGH"], 2)
        for h in ("Research OS Quality Summary", "## Coverage", "## Event Detection", "## Classification", "## Priority",
                  "## Extraction", "## Interpretation", "## Research Value", "## Manual Corrections",
                  "## Most Problematic Tickers", "## Most Reliable Modules", "## Weakest Modules",
                  "## Actions for Next Month", "Priority disagreement rate", "Guidance extraction accuracy"):
            self.assertIn(h, res["text"])

    def test_insufficient_sample_handling(self):
        for qid in self.ids[:3]:
            ql.review(qid, {"priority_correct": True}, root=self.root)
        s = qs.summarize(self.root, "2026-10")
        self.assertEqual(s["priority"]["agreement"]["value"], qs.INSUFFICIENT)
        self.assertEqual(s["event_detection"]["precision"]["value"], qs.INSUFFICIENT)
        text = qs.render(s)
        self.assertIn("insufficient_sample（3/3", text)
        self.assertNotIn("100%", text)                                          # no fake percentages
        self.assertEqual(s["most_reliable_modules"], [])

    def test_module_attribution(self):
        ql.review(self.ids[0], {"guidance_extracted_correctly": False, "management_change_correct": True,
                                "interpretation_verdict": "overinterpreted"}, reason="period mixed up",
                  extraction_errors=["guidance_tracker:wrong_period", "kpi_registry:wrong_metric_definition"],
                  root=self.root)
        s = qs.summarize(self.root, "2026-10")
        m = s["modules"]
        self.assertEqual(m["guidance_tracker"]["errors"], 1)
        self.assertEqual(m["guidance_tracker"]["extraction_errors"], 1)
        self.assertEqual(m["kpi_registry"]["extraction_errors"], 1)
        self.assertEqual(m["management_diff"]["correct"], 1)
        self.assertEqual(m["management_diff"]["errors"], 1)                    # overinterpretation
        self.assertEqual(s["extraction"]["metric_definition_errors"], 1)
        self.assertEqual(s["interpretation"]["overinterpreted"], 1)
        self.assertEqual(set(m), set(ql.MODULES))
        self.assertIn("guidance_tracker", s["weakest_modules_by_error_count"])

    def test_ticker_attribution(self):
        ql.review(self.ids[0], {"kpi_extraction_correct": False}, root=self.root)
        ql.review(self.ids[3], {"false_positive": True}, root=self.root)
        s = qs.summarize(self.root, "2026-10")
        t = s["tickers"]
        self.assertEqual((t["PL"]["events"], t["RKLB"]["events"], t["AAPL"]["events"]), (3, 2, 1))
        self.assertEqual(t["PL"]["error_modules"], {"kpi_registry": 1})
        self.assertEqual(t["RKLB"]["false_positives"], 1)
        self.assertEqual(t["AAPL"]["events_with_issues"], 0)
        self.assertEqual({x[0] for x in s["most_problematic_tickers"]}, {"PL", "RKLB"})


class HindsightTests(unittest.TestCase):
    def test_no_hindsight_return_scoring(self):
        tmp, root = _root()
        with tmp:
            qid = _auto(root)
            for text in ("The stock later rose 40%, so WATCH was wrong", "股價後來上漲，所以 valuation 錯",
                         "returns since the update were negative", "in hindsight the BUY was a mistake"):
                with self.assertRaises(ql.HindsightBiasError):
                    ql.review(qid, {"notes": text}, root=root)
                with self.assertRaises(ql.HindsightBiasError):
                    ql.correct(qid, "priority", "LOW", text, root=root)
            with self.assertRaises(ql.HindsightBiasError):
                ql.review(qid, {"forward_return": "0.2"}, root=root)
            # process-based notes are fine
            ql.review(qid, {"notes": "classification matched the 8-K item; guidance period was correct"}, root=root)
            # the summary never reads prices: changing them changes nothing
            before = qs.summarize(root, "2026-10")
            (root / "research/PL/market").mkdir(parents=True)
            (root / "research/PL/market/prices.csv").write_text("date,close\n2026-10-01,1\n2026-11-01,100\n")
            after = qs.summarize(root, "2026-10")
            for k in ("coverage", "event_detection", "priority", "modules", "tickers"):
                self.assertEqual(before[k], after[k])
        for mod in (ql, qs):
            src = inspect.getsource(mod)
            self.assertNotIn("prices.csv", src.replace("HINDSIGHT", ""))
            self.assertNotIn("l4.prices", src)


class IntegrationTests(unittest.TestCase):
    """Level 4 regression with the quality layer attached: dashboard + monthly review."""

    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.root = _root()
        shutil.copytree(ROOT / "config", cls.root / "config")
        for t in ("PL", "RKLB", "AAPL"):
            shutil.copytree(ROOT / "research" / t, cls.root / "research" / t,
                            ignore=shutil.ignore_patterns("raw", "scan-state.json"))
        cls.scan = cc.scan(cls.root, DAY, skip_prices=True)
        cls.seed = qr.seed(cls.root, DAY)
        evs = ql.list_events(cls.root, status="pending")
        ql.review(evs[0]["quality_event_id"], {"reviewed_priority": "LOW"}, reason="no thesis impact", root=cls.root)
        ql.add_missed_event(ticker="PL", event_date="2026-10-01", event_type="product_launch", source="IR release",
                            why_material="hyperspectral thesis", expected_workflow="targeted-update", as_of=DAY,
                            root=cls.root)
        cls.doc = dash.build(cls.root, DAY)
        cls.monthly = mrr.run("2026-10", cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_level4_regression(self):
        self.assertEqual(self.scan["priorities"][0]["ticker"], "PL")
        text = (self.root / "research/dashboard/current.md").read_text()
        for t in ("PL", "RKLB", "AAPL"):
            self.assertIn(f"| {t} |", text)
        for i in range(1, 23):
            self.assertIn(f"## {i}. ", self.monthly["text"])
        # quality events do not change the queue, priorities or any thesis
        pri = json.loads((self.root / "research/queue/priorities.json").read_text())
        self.assertEqual([r["ticker"] for r in pri["tickers"]], [r["ticker"] for r in self.scan["priorities"]])
        for t in ("PL", "RKLB", "AAPL"):
            self.assertEqual((self.root / f"research/{t}/thesis/current.yaml").read_text(),
                             (ROOT / f"research/{t}/thesis/current.yaml").read_text())

    def test_seed_events_pending(self):
        self.assertTrue(5 <= len(self.seed["quality_event_ids"]) <= 10)
        evs = {e["quality_event_id"]: e for e in ql.load_events(self.root)}
        seeded = [evs[q] for q in self.seed["quality_event_ids"]]
        self.assertEqual({e["ticker"] for e in seeded} - {"ALL"}, {"PL", "RKLB", "AAPL"})
        untouched = [e for e in seeded if not e["review_history"]]
        self.assertTrue(all(e["review_status"] == "pending" and e["reviewed_by"] is None for e in untouched))
        types = {e["event_type"] for e in seeded}
        for t in ("earnings_release", "major_contract", "major_price_move", "promise_delayed"):
            self.assertIn(t, types)

    def test_monthly_review_quality_section(self):
        text = self.monthly["text"]
        self.assertIn("## 23. Research OS Quality", text)
        sec = text.split("## 23. Research OS Quality", 1)[1]
        for k in ("Reviewed events", "Pending review", "False positives", "False negatives", "Priority disagreements",
                  "Manual corrections", "Weakest module", "Next quality improvement"):
            self.assertIn(k, sec)
        self.assertIn("不影響任何公司 thesis", sec)
        self.assertTrue((self.root / "research/quality/summaries/2026-10-quality-summary.md").exists())

    def test_dashboard_quality_summary(self):
        q = self.doc["quality"]
        for k in ("reviewed", "pending", "false_positives", "false_negatives", "priority_agreement", "largest_weakness"):
            self.assertIn(k, q)
        self.assertEqual(q["false_negatives"], 1)
        text = (self.root / "research/dashboard/current.md").read_text()
        block = text.split("## Research OS Quality", 1)[1].split("## Open research queue", 1)[0]
        for k in ("Reviewed events:", "Pending review:", "False positives:", "False negatives:",
                  "Priority agreement:", "Largest weakness:"):
            self.assertIn(k, block)
        self.assertLess(len(block.strip().splitlines()), 12)                  # stays short


if __name__ == "__main__":
    unittest.main()
