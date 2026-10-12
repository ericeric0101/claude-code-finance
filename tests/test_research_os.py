import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import price_reaction
import recommendation
import research_state as rs

PROJECT_SKILLS = ("equity-research-orchestrator", "management-change", "thesis-monitor",
                  "valuation-monitor", "market-reaction", "research-monitor", "research-review")


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path} has no YAML frontmatter"
    return yaml.safe_load(m.group(1))


class SkillLayoutTests(unittest.TestCase):
    def test_every_skill_has_valid_frontmatter(self):
        for skill_md in (ROOT / ".claude/skills").glob("*/SKILL.md"):
            meta = frontmatter(skill_md)
            self.assertEqual(meta["name"], skill_md.parent.name)
            self.assertTrue(meta.get("description"))

    def test_required_skills_exist(self):
        for name in ("finance-skill", "stock-analysis", "my-equity-research", *PROJECT_SKILLS):
            self.assertTrue((ROOT / ".claude/skills" / name / "SKILL.md").is_file(), name)

    def test_codex_entries_are_symlinks_not_copies(self):
        for skill in (ROOT / ".claude/skills").iterdir():
            entry = ROOT / ".agents/skills" / skill.name
            self.assertTrue(entry.is_symlink(), f"{entry} must be a symlink to the canonical skill")
            self.assertEqual(entry.resolve(), skill.resolve())

    def test_slash_commands_delegate_to_orchestrator_or_review(self):
        for name in ("init-stock", "update-stock", "deep-stock", "watch-stock", "monthly-research"):
            text = (ROOT / ".claude/commands" / f"{name}.md").read_text()
            self.assertTrue("equity-research-orchestrator" in text or "research-review" in text)


class PolicyTests(unittest.TestCase):
    def test_state_has_no_mechanical_entry_fields(self):
        for t in ("AAPL", "PL"):
            text = (ROOT / "research" / t / "valuation/latest.json").read_text()
            for key in rs.FORBIDDEN_DECISION_KEYS:
                self.assertNotIn(key, text)
            self.assertNotIn("buy_range", json.dumps(recommendation.build_summary(
                json.loads((ROOT / "research" / t / "recommendation-input.json").read_text()))))

    def test_record_valuation_rejects_haircut_buy_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rs.init_company("ZZZ", root=root)
            latest = {"as_of": "2026-01-01", "methods": {"DCF": {"bear": 1, "base": 2, "bull": 3}},
                      "buy_range": [1.6, 1.8]}
            (root / "research/ZZZ/valuation/latest.json").write_text(json.dumps(latest))
            with self.assertRaises(ValueError):
                rs.record_valuation("ZZZ", root)

    def test_market_rules_mean_reassess(self):
        for t in ("AAPL", "PL"):
            market = yaml.safe_load((ROOT / "research" / t / "monitoring/rules.yaml").read_text())["monitoring"]["market"]
            self.assertIn("reassess", market["meaning"])
            self.assertIn("not an entry price", market["meaning"])


class MigrationRegressionTests(unittest.TestCase):
    def test_aapl_state(self):
        base = ROOT / "research/AAPL"
        latest = json.loads((base / "valuation/latest.json").read_text())
        inp = json.loads((base / "recommendation-input.json").read_text())
        self.assertEqual(latest["methods"], inp["valuation_methods"])
        self.assertEqual(latest["reverse_dcf"]["status"], "quantified")
        self.assertEqual(latest["reverse_dcf"]["implied_growth"], inp["reverse_dcf"]["implied_growth"])
        self.assertEqual(latest["valuation_map"]["current_position"], "above all modeled bull values")
        self.assertEqual(rs.catch_up(latest)["earnings"][1]["static_price_pe"], 32.5)  # 10%, 2 years
        thesis = yaml.safe_load((base / "thesis/current.yaml").read_text())
        self.assertEqual(thesis["action"], "WATCH")
        self.assertNotIn("175", json.dumps(latest["methods"]))
        self.assertFalse(rs.validate_thesis(thesis))

    def test_pl_state(self):
        base = ROOT / "research/PL"
        latest = json.loads((base / "valuation/latest.json").read_text())
        thesis = yaml.safe_load((base / "thesis/current.yaml").read_text())
        self.assertIn("Speculative", thesis["research_role"])
        self.assertEqual(latest["valuation_confidence"], "low")
        self.assertEqual(latest["valuation_map"]["current_position"], "between base and bull estimates")
        self.assertTrue(latest["reverse_dcf"]["status"].startswith("illustrative"))
        self.assertLess(latest["reverse_dcf"]["base_growth"], latest["reverse_dcf"]["implied_growth"])
        rev = rs.catch_up(latest)["revenue"]
        self.assertEqual([r for r in rev if r["annual_revenue_growth_pct"] == 25.0 and r["years"] == 3][0]["static_ev_sales"], 6.9)
        self.assertIn("dilution_caveat", rs.catch_up(latest))
        self.assertEqual(thesis["components"]["per_share_value_vs_dilution"]["status"], "weakening")
        metrics = json.loads((base / "financials/latest.json").read_text())["metrics"]
        self.assertEqual(metrics["fcf_ex_deferred_revenue"]["value"], -25.786)
        self.assertLess(metrics["rpo_change_vs_fy_end_pct"]["value"], 0)
        hist = rs.read_valuation_history(base / "valuation/history.csv")
        self.assertEqual(hist[0]["base"], "12")
        self.assertFalse(rs.validate_thesis(thesis))


BASELINE = "2026-10-11"


class StateSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / "research/PL", self.root / "research/PL")
        self._rewind_to_baseline(self.root / "research/PL", BASELINE)

    @staticmethod
    def _rewind_to_baseline(base: Path, as_of: str) -> None:
        # Live PL state keeps growing with real updates; tests start from the baseline.
        tpath = base / "thesis/current.yaml"
        doc = yaml.safe_load(tpath.read_text())
        doc["as_of"] = as_of
        tpath.write_text(yaml.safe_dump(doc, sort_keys=False))
        vpath = base / "valuation/latest.json"
        latest = json.loads(vpath.read_text())
        latest["as_of"] = as_of
        vpath.write_text(json.dumps(latest))
        hpath = base / "thesis/history.json"
        hpath.write_text(json.dumps([h for h in json.loads(hpath.read_text()) if h["as_of"] <= as_of]))
        cpath = base / "valuation/history.csv"
        lines = cpath.read_text().splitlines(keepends=True)
        cpath.write_text("".join(lines[:1] + [l for l in lines[1:] if l.split(",", 1)[0] <= as_of]))

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_never_overwrites_existing_research(self):
        before = {p: p.read_bytes() for p in (self.root / "research/PL").rglob("*") if p.is_file()}
        result = rs.init_company("PL", root=self.root)
        self.assertEqual(result["created"], [])
        for p, data in before.items():
            self.assertEqual(p.read_bytes(), data)

    def test_thesis_history_upsert(self):
        path = self.root / "research/PL/thesis/current.yaml"
        doc = yaml.safe_load(path.read_text())
        rs.snapshot_thesis("PL", root=self.root)  # same date: replace, not duplicate
        self.assertEqual(len(json.loads((self.root / "research/PL/thesis/history.json").read_text())), 1)
        doc["as_of"] = "2026-12-15"
        doc["components"]["backlog_visibility"]["status"] = "improving"
        path.write_text(yaml.safe_dump(doc, sort_keys=False))
        rs.snapshot_thesis("PL", root=self.root)
        hist = json.loads((self.root / "research/PL/thesis/history.json").read_text())
        self.assertEqual([h["as_of"] for h in hist], ["2026-10-11", "2026-12-15"])
        self.assertEqual(hist[0]["components"]["backlog_visibility"]["status"], "weakening")
        report = rs.change_report("PL", self.root)
        self.assertIn("backlog_visibility: weakening → improving", report)

    def test_thesis_rejects_unknown_status(self):
        path = self.root / "research/PL/thesis/current.yaml"
        doc = yaml.safe_load(path.read_text())
        doc["components"]["liquidity"]["status"] = "great"
        path.write_text(yaml.safe_dump(doc, sort_keys=False))
        with self.assertRaises(ValueError):
            rs.snapshot_thesis("PL", root=self.root)

    def test_valuation_history_upsert(self):
        vpath = self.root / "research/PL/valuation/latest.json"
        latest = json.loads(vpath.read_text())
        rs.record_valuation("PL", self.root)
        self.assertEqual(len(rs.read_valuation_history(self.root / "research/PL/valuation/history.csv")), 1)
        latest["as_of"] = "2026-12-15"
        latest["methods"]["five-year scenario DCF"]["base"] = 13
        vpath.write_text(json.dumps(latest))
        rows = rs.record_valuation("PL", self.root)
        self.assertEqual([(r["as_of"], r["base"]) for r in rows], [("2026-10-11", "12"), ("2026-12-15", "13")])
        self.assertIn("3/12/25 → 3/13/25", rs.change_report("PL", self.root))

    def test_baseline_change_report(self):
        report = rs.change_report("PL", self.root)
        self.assertIn("# What Changed Since Last Review — PL", report)
        self.assertIn("no prior research state", report)
        for section in ("## Positive", "## Negative", "## Unchanged", "## Promises",
                        "## Valuation", "## Expectation gap", "## Action", "## Confidence",
                        "## Next catalysts"):
            self.assertIn(section, report)


class AnalyticsTests(unittest.TestCase):
    def test_expectation_gap_and_direction(self):
        cur = rs.expectation_gap({"rev_cagr": 0.30, "fcf_margin": 0.22},
                                 {"rev_cagr": 0.25, "fcf_margin": 0.20},
                                 {"rev_cagr": 0.35, "fcf_margin": 0.25})
        self.assertEqual(cur["rev_cagr"]["position"], "above base but within modeled bull growth")
        prev = rs.expectation_gap({"rev_cagr": 0.33, "fcf_margin": 0.22},
                                  {"rev_cagr": 0.25, "fcf_margin": 0.20},
                                  {"rev_cagr": 0.35, "fcf_margin": 0.25})
        self.assertEqual(rs.gap_direction(prev, cur), {"rev_cagr": "narrowing", "fcf_margin": "stable"})

    def test_fcf_catch_up_math(self):
        out = rs.catch_up({"price": 100, "catch_up": {"fcf_per_share": 4, "fcf_growth_rates": [0.10], "years": [2]}})
        self.assertEqual(out["fcf"][0]["future_fcf_per_share"], 4.84)
        self.assertEqual(out["fcf"][0]["static_price_p_fcf"], 20.7)

    def test_rule_evaluation(self):
        rules = {"monitoring": {"fundamental": {
            "gm": {"metric": "gm", "warning": "<52%"}, "dil": {"metric": "dil", "warning": ">5%"},
            "rpo": {"metric": "rpo", "warning": "<0%"}}}}
        res = {r["rule"]: r["state"] for r in rs.evaluate_rules(rules, {"gm": {"value": 51.0}, "dil": {"value": 2}})}
        self.assertEqual(res, {"gm": "triggered", "dil": "not_triggered", "rpo": "missing_data"})

    def test_price_reaction_observations(self):
        prices = [{"date": f"2026-01-{d:02d}", "open": 10.0, "close": 10.0, "volume": 100.0} for d in range(1, 22)]
        prices.append({"date": "2026-01-22", "open": 11.0, "close": 11.5, "volume": 300.0})
        prices += [{"date": f"2026-02-{d:02d}", "open": 11.0, "close": c, "volume": 100.0}
                   for d, c in zip(range(1, 6), (11.0, 10.5, 10.35, 10.8, 11.0))]
        r = price_reaction.event_reaction(prices, "2026-01-22")
        self.assertEqual(r["gap_pct"], 10.0)
        self.assertEqual(r["day_return_pct"], 15.0)
        self.assertEqual(r["volume_ratio_20d"], 3.0)
        self.assertEqual(r["max_drawdown_20d_pct"], -10.0)
        self.assertIn("gap", r["observation"])
        self.assertNotIn("smart money", json.dumps(r))


class PriceFreshnessTests(unittest.TestCase):
    def test_after_close_event_moves_t0_to_next_session(self):
        prices = [{"date": f"2026-03-{d:02d}", "open": 10.0, "close": 10.0 + d / 10, "volume": 100.0}
                  for d in range(1, 10)]
        self.assertEqual(price_reaction.event_reaction(prices, "2026-03-05")["t0"], "2026-03-05")
        self.assertEqual(price_reaction.event_reaction(prices, "2026-03-05", after_close=True)["t0"], "2026-03-06")

    def test_status_reports_latest_stored_close(self):
        lines = rs.latest_market_lines(ROOT / "research/PL", 17.18)
        self.assertTrue(lines and lines[0].startswith("Latest stored close"))
        self.assertIn("price_reaction.py fetch", lines[-1])

    def test_stored_prices_have_source_and_retrieval(self):
        for t in ("AAPL", "PL"):
            with (ROOT / "research" / t / "market/prices.csv").open() as fh:
                rows = list(csv.DictReader(fh))
            self.assertGreater(len(rows), 100)
            self.assertTrue(all(r["source"] and r["retrieved_at"] for r in rows))
            self.assertEqual(len({r["date"] for r in rows}), len(rows))


class SecretTests(unittest.TestCase):
    def test_no_secret_files_or_values_tracked(self):
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
        self.assertFalse([f for f in tracked if f == ".env" or (f.startswith(".env.") and f != ".env.example")])
        env = ROOT / ".env"
        if not env.exists():
            return
        secrets = []
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if len(value) >= 8:
                    secrets.append(value)
        leaks = []
        for f in tracked:
            p = ROOT / f
            if p.is_file() and p.stat().st_size < 5_000_000:
                text = p.read_text(errors="ignore")
                if any(s in text for s in secrets):
                    leaks.append(f)
        self.assertEqual(leaks, [], "secret value found in tracked files (values not shown)")


if __name__ == "__main__":
    unittest.main()
