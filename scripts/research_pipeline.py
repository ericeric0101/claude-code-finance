#!/usr/bin/env python3
"""INIT and UPDATE pipelines for the continuous research OS (entry points for
/init-stock and /update-stock; the orchestrator skill adds analyst judgment).

INIT  (never an empty shell)
   1 init state             2 acquire SEC data          3 build 5Y + 8Q history
   4 historical prices      5 earnings event list       6 management history
   7 initial promise tracker 8 stock-analysis QA (ratios, verify_data)
   9 thesis (auto-draft)   10 valuation (auto-draft)    11 assumption-vs-history check
  12 historical valuation  13 monitoring rules          14 snapshot
  15 baseline report
  Existing analyst-authored thesis / valuation / rules are never replaced by drafts.

UPDATE (incremental; never regenerates the baseline)
   1 read previous state (latest snapshot; one is saved first if none exists)
   2 identify last reviewed filing / event date
   3 fetch only new evidence (SEC filings after that date -> evidence/sources.json)
   4 update historical financials (merge)       5 update management statements
   6 resolve old promises   7 add new promises   8 re-evaluate thesis (rules; drafts only auto)
   9 re-run valuation only where inputs changed (price, start revenue, net cash)
  10 update historical valuation   11 run monitoring rules   12 save new snapshot
  13 true change report (reports/YYYY-MM-DD-change-report.md)

Network: SEC (finance-skill client) and prices (uv finance-skill env, yfinance /
Alpha Vantage). --offline reuses cached raw/ data and stored prices.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import assumption_history_check as ahc  # noqa: E402
import baseline_draft as bd  # noqa: E402
import build_fundamental_history as bfh  # noqa: E402
import build_management_history as bmh  # noqa: E402
import build_valuation_history as bvh  # noqa: E402
import price_reaction  # noqa: E402
import recommendation  # noqa: E402
import research_state as rs  # noqa: E402
import state_diff  # noqa: E402

UV = ["uv", "run", "--project", ".claude/skills/finance-skill/scripts", "python"]
SA = ROOT / ".claude/skills/stock-analysis/scripts"


def _log(steps: List[Dict[str, Any]], n: int, name: str, status: str, detail: Any = "") -> None:
    steps.append({"step": n, "name": name, "status": status, "detail": detail})
    print(f"[{n:>2}] {name}: {status}" + (f" — {detail}" if detail else ""), flush=True)


def _yaml_write(path: Path, data: Any) -> None:
    rs._require_yaml()
    path.write_text(rs.yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _is_empty_state(path: Path, key: str) -> bool:
    """True when a state file is missing or still the empty init skeleton."""
    if not path.exists():
        return True
    data = rs._read_yaml(path) if path.suffix == ".yaml" else rs._read_json(path)
    if not data:
        return True
    v = data.get(key)
    return not v or (isinstance(v, dict) and not any(v.values()))


def fetch_prices(ticker: str, root: Path, period: str = "max") -> str:
    cmds = [UV + ["scripts/price_reaction.py", "fetch", ticker, "--period", period]]
    if not price_reaction.benchmark_path("SPY", root).exists():
        cmds.append(UV + ["scripts/price_reaction.py", "fetch-benchmark", "SPY", "--period", "10y"])
    else:
        cmds.append(UV + ["scripts/price_reaction.py", "fetch-benchmark", "SPY", "--period", "1y"])
    out = []
    for c in cmds:
        r = subprocess.run(c, cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        out.append((r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1])
    return " | ".join(out)


def acquire_sec(ticker: str, cik: str, root: Path, offline: bool) -> Dict[str, Any]:
    import sec_data
    facts = sec_data.company_facts(cik, ticker, root, refresh=not offline)
    sub = sec_data.submissions(cik, ticker, root, refresh=not offline)
    filings = sec_data.recent_filings(sub, ("10-K", "10-Q", "8-K"))
    base = rs.company_dir(ticker, root)
    path = base / "evidence/sources.json"
    sources = rs._read_json(path, []) or []
    ids = {s.get("id") for s in sources}
    added = 0
    for f in filings[:40]:
        sid = f"sec-{f['accession']}"
        if sid in ids:
            continue
        sources.append({"id": sid, "tier": 1, "type": f["form"] + (f" (items {f['items']})" if f.get("items") else ""),
                        "period_end": f.get("report_date"), "filed": f["filed"],
                        "url": sec_data.filing_base_url(cik, f["accession"]) + f["primary"],
                        "retrieved_by": "research_pipeline.py"})
        added += 1
    sources.sort(key=lambda s: str(s.get("filed") or s.get("date") or ""))
    rs._write_json(path, sources)
    return {"entity": facts.get("entityName"), "filings_indexed": len(filings), "sources_added": added,
            "filings": filings}


def run_stock_analysis_qa(ticker: str, history: Dict[str, Any], root: Path, as_of: str) -> str:
    """ratios.py over the annual history and verify_data.py over the SEC datapoints."""
    base = rs.company_dir(ticker, root)
    qa = base / "qa"
    qa.mkdir(exist_ok=True)
    periods = []
    for a in history["annual"]:
        m = a["metrics"]
        v = lambda k: bfh._v(m, k)
        p = {"label": a["period"], "revenue": v("revenue"), "gross_profit": v("gross_profit"),
             "ebit": v("operating_income"), "pat": v("net_income"), "cfo": v("cfo"), "capex": v("capex"),
             "cash": v("cash"), "current_investments": v("short_term_investments"), "equity": v("equity"),
             "long_term_debt": v("debt"), "diluted_shares": v("diluted_shares"),
             "depreciation": v("depreciation_amortization")}
        periods.append({k: x for k, x in p.items() if x is not None})
    (qa / "ratios-input.json").write_text(json.dumps({
        "company": history.get("entity"), "currency": "USD millions", "basis": "consolidated US GAAP",
        "sector": "generic", "periods_order": "oldest_first", "periods": periods,
        "source": "financials/history.json (SEC companyfacts)"}, indent=2))
    datapoints = []
    for rec in history["annual"][-3:] + history["quarters"][-4:]:
        for k in ("revenue", "operating_income", "net_income", "cfo"):
            p = rec["metrics"].get(k)
            if isinstance(p, dict) and p.get("value") is not None and p.get("accn"):
                datapoints.append({"metric": k, "value": p["value"], "period": rec["period"],
                                   "basis": "consolidated", "unit": "USD millions",
                                   "source": f"SEC {p.get('form')} filed {p.get('filed')} accession {p.get('accn')}",
                                   "source_tier": 1})
    last_q = history["quarters"][-1] if history["quarters"] else None
    fy_end_month = date.fromisoformat(history["fiscal_year_ends"][-1]).strftime("%B") if history.get("fiscal_year_ends") else "December"
    (qa / "data-intake.json").write_text(json.dumps({
        "company": history.get("entity"), "ticker": ticker, "as_of": as_of, "reporting_basis": "consolidated",
        "currency": "USD", "units": "millions", "fiscal_year_end": fy_end_month,
        "latest_reported_period": {"period": last_q["period"] if last_q else None,
                                   "published": max((p.get("filed") for p in last_q["metrics"].values()
                                                     if isinstance(p, dict) and p.get("filed")), default=None) if last_q else None},
        "datapoints": datapoints, "not_available": []}, indent=2))
    res = []
    for script, args, out in (("ratios.py", [str(qa / "ratios-input.json"), "--json"], "ratios-output.json"),
                              ("verify_data.py", [str(qa / "data-intake.json")], "data-verification.txt")):
        r = subprocess.run([sys.executable, str(SA / script)] + args, capture_output=True, text=True)
        (qa / out).write_text(r.stdout or r.stderr)
        head = next((ln for ln in (r.stdout or r.stderr).splitlines() if ln.strip()), "")
        res.append(f"{script} exit {r.returncode}" + (f" ({head[:80]})" if script == "verify_data.py" else ""))
    return "; ".join(res) + " — valuation/score/challenge/lint need an analyst-written report"


def latest_price(base: Path) -> Optional[Dict[str, Any]]:
    return rs.latest_close(base)


def baseline_report(ticker: str, root: Path, steps: List[Dict[str, Any]], as_of: str) -> Path:
    base = rs.company_dir(ticker, root)
    hist = rs._read_json(base / "financials/history.json")
    cov = rs._read_json(base / "financials/coverage.json", {})
    chk = rs._read_json(base / "valuation/assumption-check.json", {})
    latest = rs._read_json(base / "valuation/latest.json", {})
    pct = rs._read_json(base / "valuation/historical-percentiles.json", {})
    prom = bmh.promise_counts(rs._read_json(base / "management/promises.json", []) or [])
    L = [f"# {ticker} 基準研究狀態（Baseline）— {as_of}", "",
         "> 自動建立的基準狀態：歷史數字為 SEC 一級來源（Fact / Calculation）；thesis、估值情境與監控規則為"
         " auto-draft（Assumption），需研究員複核後才代表研究判斷。此文件不是買賣建議。", "",
         "## 資料覆蓋", f"- 年度：{', '.join(cov.get('annual_periods', []))}（≥5 年：{cov.get('meets_5y')}）",
         f"- 季度：{', '.join(cov.get('quarter_periods', []))}（≥8 季：{cov.get('meets_8q')}）",
         f"- 公司特定 KPI：{cov.get('company_kpis_note', '')}", "", "## 歷史基本面（年度，USD m / %）", "",
         "| 期間 | 營收 | YoY | 毛利率 | 營業利益率 | FCF | SBC/營收 | 稀釋股數(m) |", "|---|---|---|---|---|---|---|---|"]
    for a in (hist or {}).get("annual", []):
        m = a["metrics"]
        f = lambda k, d=1: "n/a" if bfh._v(m, k) is None else f"{bfh._v(m, k):,.{d}f}"
        L.append(f"| {a['period']} | {f('revenue')} | {f('revenue_yoy_pct')} | {f('gross_margin_pct')} | "
                 f"{f('operating_margin_pct')} | {f('fcf')} | {f('sbc_pct_revenue')} | {f('diluted_shares')} |")
    L += ["", "## 假設 vs 歷史", ""] + [f"- {c['interpretation']}" for c in chk.get("checks", [])]
    L += ["", "## 估值（auto-draft）", f"- 價格 {latest.get('price')}（{latest.get('price_date')}）",
          f"- 情境：{json.dumps(latest.get('methods'), ensure_ascii=False)}",
          f"- 位置：{(latest.get('valuation_map') or {}).get('current_position')}",
          f"- Reverse DCF implied 5Y revenue CAGR：{(latest.get('reverse_dcf') or {}).get('implied_growth')}"]
    for k, p in (pct.get("percentiles") or {}).items():
        L.append(f"- 歷史 {k}：current {p.get('current')}；1Y pct {p.get('1y')}；3Y pct {p.get('3y')}；"
                 f"since listing {p.get('since_listing')}")
    L += ["", "## 管理層與承諾", f"- 承諾計數：{prom['counts']}（{prom['caveat']}）",
          "- 逐季措辭比較見 management/changes.md", "", "## 監控規則（觸發 = REASSESS）"]
    for r in rs.check_rules(ticker, root):
        L.append(f"- [{r['type']}] {r['rule']}: {r['state']}")
    L += ["", "## INIT 步驟紀錄"] + [f"- {s['step']}. {s['name']}: {s['status']}" for s in steps]
    out = base / "reports" / f"{as_of}-baseline-report.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    _index(base, as_of, "Baseline (INIT pipeline)", out.name)
    return out


def _index(base: Path, as_of: str, kind: str, name: str) -> None:
    idx = base / "reports/index.md"
    text = idx.read_text(encoding="utf-8") if idx.exists() else \
        "# Reports\n\n| Date | Type | Report |\n|---|---|---|\n"
    line = f"| {as_of} | {kind} | [{name}]({name}) |"
    if f"[{name}]" not in text:
        idx.write_text(text.rstrip("\n") + "\n" + line + "\n", encoding="utf-8")


def init(ticker: str, cik: str, company: str = "", root: Path = ROOT, offline: bool = False,
         skip_prices: bool = False, as_of: Optional[str] = None) -> Dict[str, Any]:
    t = ticker.upper()
    as_of = as_of or date.today().isoformat()
    base = rs.company_dir(t, root)
    steps: List[Dict[str, Any]] = []
    r = rs.init_company(t, company, cik, root)
    _log(steps, 1, "init state", "ok", f"{len(r['created'])} created, {len(r['kept'])} kept")
    sec = acquire_sec(t, cik, root, offline)
    company = company or sec["entity"] or t
    _log(steps, 2, "acquire SEC data", "ok", f"{sec['entity']}; {sec['sources_added']} sources added")
    facts = json.loads((base / "raw/companyfacts.json").read_text())
    ov = rs._read_json(base / "financials/tag-overrides.json", {}) or {}
    history = bfh.build_history(facts, overrides=ov)
    out = bfh.write_outputs(t, history, root)
    _log(steps, 3, "build 5Y + 8Q history", "ok" if out["meets_5y"] and out["meets_8q"] else "partial",
         f"{len(out['annual_periods'])} FY, {len(out['quarter_periods'])} quarters")
    rs.refresh_latest_financials(t, root)
    _log(steps, 4, "historical prices", "skipped (offline)" if skip_prices else "ok",
         "" if skip_prices else fetch_prices(t, root))
    m = bmh.build(t, cik, root, 8, offline, as_of)
    _log(steps, 5, "earnings event list", "ok", f"{m['events_total']} events")
    _log(steps, 6, "management history", "ok", f"{m['statements_total']} statements over {len(m['periods'])} periods")
    _log(steps, 7, "initial promise tracker", "ok", m["counts"])
    _log(steps, 0, "Level 4: KPI registry, semantic diff, guidance vs actual", *level4_refresh(t, root, as_of))
    try:
        qa = run_stock_analysis_qa(t, history, root, as_of)
        _log(steps, 8, "stock-analysis QA", "ok", qa)
    except Exception as exc:  # report, never silent
        _log(steps, 8, "stock-analysis QA", "failed", repr(exc)[:200])
    s = bd.facts_summary(history)
    src = "financials/history.json"
    tpath = base / "thesis/current.yaml"
    if _is_empty_state(tpath, "components"):
        _yaml_write(tpath, bd.draft_thesis(t, company, s, as_of, src))
        _log(steps, 9, "thesis", "auto-draft written")
    else:
        _log(steps, 9, "thesis", "kept existing analyst thesis")
    price = latest_price(base)
    vpath = base / "valuation/latest.json"
    if _is_empty_state(vpath, "methods"):
        if price and s["revenue_ttm"] and s["diluted_shares"]:
            latest, assumptions = bd.draft_valuation(t, s, price["close"], f"{price['date']} close", as_of)
            rs._write_json(vpath, latest)
            rs._write_json(base / "valuation/assumptions.json", assumptions)
            _log(steps, 10, "valuation", "auto-draft written", latest["methods"])
        else:
            _log(steps, 10, "valuation", "skipped", "missing price, TTM revenue or share count")
    else:
        _log(steps, 10, "valuation", "kept existing analyst valuation")
    try:
        chk = ahc.run(t, root)
        _log(steps, 11, "assumption-vs-history check", "ok", [c["classification"] for c in chk["checks"]])
    except Exception as exc:
        _log(steps, 11, "assumption-vs-history check", "failed", repr(exc)[:200])
    try:
        vh = bvh.build(t, root)
        _log(steps, 12, "historical valuation", "ok", f"{vh['month_ends']} month-ends, {vh['timeline_events']} earnings rows")
    except Exception as exc:
        _log(steps, 12, "historical valuation", "failed", repr(exc)[:200])
    rpath = base / "monitoring/rules.yaml"
    latest = rs._read_json(vpath, {}) or {}
    if _is_empty_state(rpath, "monitoring") or not ((rs._read_yaml(rpath) or {}).get("monitoring") or {}).get("fundamental"):
        rules, inval = bd.draft_rules(t, s, latest.get("methods") or {}, as_of)
        _yaml_write(rpath, rules)
        _yaml_write(base / "thesis/invalidation-rules.yaml", inval)
        _log(steps, 13, "monitoring rules", "auto-draft written")
    else:
        _log(steps, 13, "monitoring rules", "kept existing rules")
    if latest.get("methods"):
        rs.record_valuation(t, root)
        rs.record_expectation_gap(t, root)
    rs.snapshot_thesis(t, "INIT baseline (auto-draft where noted)", root)
    snap = state_diff.build_snapshot(t, root, as_of, note="INIT baseline")
    state_diff.save_snapshot(t, snap, root)
    _log(steps, 14, "snapshot", "ok", f"snapshots/{as_of}.json")
    rep = baseline_report(t, root, steps, as_of)
    _log(steps, 15, "baseline report", "ok", str(rep.relative_to(root)))
    return {"ticker": t, "steps": steps, "report": str(rep)}


def _reprice(base: Path, close: Dict[str, Any], as_of: str) -> List[str]:
    """Step 9: refresh price-dependent valuation fields only; scenario values stay."""
    path = base / "valuation/latest.json"
    latest = rs._read_json(path, {}) or {}
    changed = []
    if not latest.get("methods"):
        return ["no valuation state"]
    old_price = latest.get("price")
    if old_price is not None and abs(float(old_price) - close["close"]) < 1e-9:
        latest["as_of"] = as_of  # reviewed at as_of; inputs unchanged so nothing is re-run
        rs._write_json(path, latest)
        return [f"price unchanged ({close['close']} {close['date']}); valuation not re-run"]
    latest["price"], latest["price_date"] = close["close"], f"{close['date']} close ({close['source'][:40]})"
    vmap = recommendation.valuation_map(latest["methods"], close["close"])
    latest.setdefault("valuation_map", {})["current_position"] = vmap["current_position"]
    changed.append(f"price {old_price} → {close['close']}; zone {vmap['current_position']}")
    rd = latest.get("reverse_dcf") or {}
    held = rd.get("held_at_base_case") or {}
    assumptions = rs._read_json(base / "valuation/assumptions.json", {}) or {}
    start_rev = ((assumptions.get("methods") or {}).get("five-year scenario DCF") or {}).get("start_revenue", {}).get("value")
    if latest.get("draft_auto"):
        inp = latest.get("inputs") or {}
        start_rev, net, shares, m0 = inp.get("revenue_ttm"), inp.get("net_cash"), inp.get("diluted_shares"), None
        held = {**held, "start": None}
    else:
        net = (held.get("net_liquid_assets_m"))
        shares = held.get("diluted_shares_m")
        m0 = held.get("fcf_margin_fy2027_start", held.get("fcf_margin_start"))
    if start_rev and net is not None and shares and held.get("fcf_margin_y5"):
        implied = bd.solve_implied_cagr(close["close"], float(start_rev), held["fcf_margin_y5"],
                                        held.get("terminal_ev_fcf", held.get("terminal_ev_fcf", 25)),
                                        held["discount_rate"], float(net), float(shares), m0)
        if implied is not None:
            rd["implied_growth"] = implied
            rd["price_used"] = f"{close['close']} ({close['date']} close)"
            latest["reverse_dcf"] = rd
            exp = latest.setdefault("expectations", {})
            exp.setdefault("market_implied", {})["revenue_cagr_5y"] = implied
            changed.append(f"reverse DCF re-solved (same held assumptions): implied CAGR {implied:.1%}")
    latest["as_of"] = as_of
    rs._write_json(path, latest)
    return changed


def _touch_analyst_thesis(path: Path, as_of: str, report: str) -> None:
    """Minimal textual edit of an analyst-authored thesis: only as_of and
    last_update_report change; comments, wording and layout are preserved."""
    import re
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^as_of: .*$", f"as_of: '{as_of}'", text, count=1)
    if re.search(r"(?m)^last_update_report: ", text):
        text = re.sub(r"(?m)^last_update_report: .*$", f"last_update_report: {report}", text, count=1)
    else:
        text = re.sub(r"(?m)^(as_of: .*)$", rf"\1\nlast_update_report: {report}", text, count=1)
    path.write_text(text, encoding="utf-8")


def level4_refresh(ticker: str, root: Path, as_of: str) -> tuple:
    """Level 4 add-ons after the Level 3 management step; never fails the Level 3 pipeline."""
    try:
        import guidance_tracker
        import kpi_registry
        k = kpi_registry.build(ticker, root, as_of)
        g = guidance_tracker.track(ticker, root, as_of)
        return "ok", {"kpi_required_unavailable": k["required_unavailable"], "guidance_added": g["guidance_added"],
                      "promise_counts": g["counts"], "message": g["message"]}
    except Exception as exc:
        return "skipped", repr(exc)[:200]


def update(ticker: str, cik: str, root: Path = ROOT, offline: bool = False, skip_prices: bool = False,
           as_of: Optional[str] = None, note: str = "") -> Dict[str, Any]:
    t = ticker.upper()
    as_of = as_of or date.today().isoformat()
    base = rs.company_dir(t, root)
    steps: List[Dict[str, Any]] = []
    snaps = state_diff.list_snapshots(t, root)
    if not snaps:
        prev = state_diff.build_snapshot(t, root, note="pre-update state (first snapshot)")
        state_diff.save_snapshot(t, prev, root)
        snaps = [prev]
    prev = snaps[-1]
    _log(steps, 1, "read previous state", "ok", f"snapshot {prev['as_of']}")
    last_filed = ((prev.get("financials") or {}).get("latest_filed")) or "0000-00-00"
    _log(steps, 2, "last reviewed filing date", "ok", last_filed)
    if not skip_prices:
        _log(steps, 0, "refresh prices", "ok", fetch_prices(t, root, "1y"))
    sec = acquire_sec(t, cik, root, offline)
    new = [f for f in sec["filings"] if f["filed"] > last_filed]
    _log(steps, 3, "fetch new evidence", "ok",
         f"{len(new)} SEC filings since {last_filed}: " + ", ".join(f"{f['form']} {f['filed']}" for f in new[:8]))
    facts = json.loads((base / "raw/companyfacts.json").read_text())
    ov = rs._read_json(base / "financials/tag-overrides.json", {}) or {}
    old_hist = rs._read_json(base / "financials/history.json") or {}
    history = bfh.build_history(facts, overrides=ov)
    old_q = (old_hist.get("quarters") or [{}])[-1].get("period") if old_hist else None
    new_q = history["quarters"][-1]["period"] if history["quarters"] else None
    bfh.write_outputs(t, history, root)
    rs.refresh_latest_financials(t, root)
    _log(steps, 4, "update historical financials", "ok", f"latest quarter {old_q} → {new_q}")
    m = bmh.build(t, cik, root, 8, offline, as_of)
    _log(steps, 5, "update management statements", "ok", f"+{m['statements_added']} statements")
    _log(steps, 6, "resolve old promises", "ok", m["counts"])
    _log(steps, 7, "add new promises", "ok", f"{m['guidance_records']} guidance records tracked")
    _log(steps, 0, "Level 4: KPI registry, semantic diff, guidance vs actual", *level4_refresh(t, root, as_of))
    rules = rs.check_rules(t, root)
    inval = [r for r in rules if r["type"] == "invalidation" and r["state"] == "triggered"]
    thesis_path = base / "thesis/current.yaml"
    thesis = rs._read_yaml(thesis_path) or {}
    if thesis.get("draft_auto"):
        s = bd.facts_summary(history)
        draft = bd.draft_thesis(t, thesis.get("company", t), s, as_of, "financials/history.json")
        for k, c in draft["components"].items():
            if k in thesis.get("components", {}):
                thesis["components"][k].update({"status": c["status"], "evidence": c["evidence"], "last_updated": as_of})
        _log(steps, 8, "re-evaluate thesis", "auto-draft statuses recomputed from new data")
    else:
        _log(steps, 8, "re-evaluate thesis", "analyst thesis kept; REASSESS flags",
             [r["thesis_component"] for r in inval] or "no invalidation rule triggered")
    if thesis.get("draft_auto"):
        thesis["as_of"] = as_of
        _yaml_write(thesis_path, thesis)
    else:
        _touch_analyst_thesis(thesis_path, as_of, f"reports/{as_of}-change-report.md")
    close = rs.latest_close(base)
    _log(steps, 9, "valuation (only changed inputs)", "ok", _reprice(base, close, as_of) if close else "no price")
    try:
        vh = bvh.build(t, root)
        _log(steps, 10, "update historical valuation", "ok", vh["percentiles"].get("ev_sales"))
    except Exception as exc:
        _log(steps, 10, "update historical valuation", "failed", repr(exc)[:200])
    try:
        ahc.run(t, root)
    except Exception:
        pass
    rs.record_valuation(t, root)
    rs.record_expectation_gap(t, root)
    rules = rs.check_rules(t, root)
    _log(steps, 11, "monitoring rules", "ok", [r["rule"] for r in rules if r["state"] == "triggered"])
    rs.snapshot_thesis(t, note or "UPDATE pipeline", root)
    cur = state_diff.build_snapshot(t, root, as_of, note=note or "UPDATE pipeline")
    state_diff.save_snapshot(t, cur, root, overwrite=True)
    _log(steps, 12, "save snapshot", "ok", f"snapshots/{as_of}.json")
    prev_snap = next((s for s in reversed(state_diff.list_snapshots(t, root)) if s["as_of"] < as_of), prev)
    text = state_diff.render_report(t, state_diff.diff_states(prev_snap, cur), cur,
                                    f"UPDATE pipeline {as_of}；新 SEC 文件 {len(new)} 份。")
    out = base / "reports" / f"{as_of}-change-report.md"
    out.write_text(text, encoding="utf-8")
    _index(base, as_of, "Change report (UPDATE pipeline)", out.name)
    _log(steps, 13, "change report", "ok", str(out.relative_to(root)))
    try:  # Level 4: the full update covers the ticker's open A / B research-queue items
        import research_queue
        n = research_queue.complete_for_ticker(t, as_of, ("A", "B"), f"handled by UPDATE {as_of} ({out.name})", root)
        _log(steps, 0, "Level 4: research queue", "ok", f"{n} open items completed")
    except Exception as exc:
        _log(steps, 0, "Level 4: research queue", "skipped", repr(exc)[:200])
    return {"ticker": t, "steps": steps, "report": str(out), "text": text}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "update"):
        p = sub.add_parser(name)
        p.add_argument("ticker")
        p.add_argument("--cik", required=True, help="verified numeric SEC CIK")
        p.add_argument("--offline", action="store_true")
        p.add_argument("--skip-prices", action="store_true")
        p.add_argument("--as-of")
        p.add_argument("--root", type=Path, default=ROOT)
        if name == "init":
            p.add_argument("--company", default="")
        else:
            p.add_argument("--note", default="")
    a = ap.parse_args(argv)
    if not a.cik.isdigit():
        ap.error("--cik must be numeric")
    if a.cmd == "init":
        res = init(a.ticker, a.cik, a.company, a.root, a.offline, a.skip_prices, a.as_of)
    else:
        res = update(a.ticker, a.cik, a.root, a.offline, a.skip_prices, a.as_of, a.note)
    print(res["report"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
