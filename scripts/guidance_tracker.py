#!/usr/bin/env python3
"""Guidance-vs-actual engine (Level 4): what management said vs what happened.

Builds on Level 3 (management/guidance.json + promises.json from
build_management_history.py) and adds:

1. Guidance normalization: bulleted "<Quarter> <Year> Guidance ... expects:" blocks
   (e.g. RKLB) that the Level 3 prose parser misses are parsed from the cached
   releases in raw/filings/ and merged into guidance.json (existing rows kept).
2. Definition-aware resolution. Every guided metric must have a recorded company
   definition and a comparison basis in research/<T>/config/kpis.yaml
   (`guidance_metrics`). Audit rule: when the company metric definition differs
   from the actual we can measure, or is not recorded, the promise is NOT
   auto-resolved: status `not_evaluable`, `comparison_basis` explains why.
3. Lifecycle fields on promises.json: metric_definition, comparison_basis,
   resolution_confidence, actual_source, draft_auto, review_required.
4. Timing promises from structured claims (management_semantic_diff): a later claim
   that moves the same milestone later marks the earlier promise `delayed`.

Statuses: pending, delivered, partially_delivered, missed, delayed, superseded,
not_evaluable. Spending plans (capex, opex) outside the range are deviations from
plan; underspending is not by itself a negative signal.

When no guidance exists the output says so explicitly:
"No explicit evaluable management guidance found." Promises are never fabricated.

Outputs: management/promises.json (updated in place),
         management/guidance-vs-actual.{json,md}

Usage: python3 scripts/guidance_tracker.py PL [--as-of YYYY-MM-DD] [--no-parse]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_management_history as bmh  # noqa: E402
import level4_common as l4  # noqa: E402
import management_semantic_diff as msd  # noqa: E402

STATUSES = ("pending", "delivered", "partially_delivered", "missed", "delayed", "superseded", "not_evaluable")
EVALUABLE_BASES = ("gaap_match", "definition_match", "same_company_metric", "calculated_gaap")
NO_GUIDANCE = "No explicit evaluable management guidance found."
SPENDING = ("capex", "gaap_operating_expenses", "non_gaap_operating_expenses", "sbc")

BULLET_METRICS = [
    (r"non-gaap gross margin", "non_gaap_gross_margin"),
    (r"gaap gross margin", "gross_margin"),
    (r"non-gaap operating expense", "non_gaap_operating_expenses"),
    (r"gaap operating expense", "gaap_operating_expenses"),
    (r"space systems revenue", "space_systems_revenue"),
    (r"launch services revenue", "launch_services_revenue"),
    (r"adjusted ebitda", "adjusted_ebitda"),
    (r"interest (?:expense|income)", "net_interest"),
    (r"basic (?:weighted average )?(?:common )?shares", "basic_shares_guided"),
    (r"capital expenditure", "capex"),
    (r"^revenue", "revenue"),
]
_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_VAL = re.compile(r"\(?\$?\s?(\d[\d,]*(?:\.\d+)?)\)?\s*(million|billion|%)?", re.I)


def _period_label(q: Optional[str], year: str) -> str:
    return f"Q{_ORD[q.lower()]} FY{year}" if q else f"FY{year}"


def parse_bullet_guidance(text: str, issued: str, url: str) -> List[Dict[str, Any]]:
    """'<First|..> Quarter 2026 Guidance / Full Year 2026 Guidance ... expects: • Metric between $X and $Y.'"""
    out: List[Dict[str, Any]] = []
    for m in re.finditer(r"(?i)(?:(first|second|third|fourth) quarter|full year|fiscal year)\s+(20\d\d)\s+guidance", text):
        q, year = m.group(1), m.group(2)
        period = _period_label(q, year)
        block = text[m.end(): m.end() + 2500]
        stop = re.search(r"(?i)see .use of non-gaap|conference call|forward-looking", block)
        block = block[: stop.start()] if stop else block
        for bullet in re.split(r"\s*•\s*", block)[1:]:
            line = bullet.strip().split("\n")[0].strip().rstrip(".")
            low = line.lower()
            metric = next((k for rx, k in BULLET_METRICS if re.search(rx, low)), None)
            if not metric:
                continue
            nums = [(float(v.replace(",", "")), (u or "").lower()) for v, u in _VAL.findall(line)]
            nums = [(v, u) for v, u in nums if not (1990 < v < 2100 and not u)]
            if not nums:
                continue
            unit = "%" if any(u == "%" for _, u in nums) else \
                ("millions of shares" if metric == "basic_shares_guided" else
                 "USD billions" if any(u == "billion" for _, u in nums) else "USD millions")
            vals = [v for v, u in nums if (u == "%") == (unit == "%")][:2]
            if not vals:
                continue
            if len(vals) == 2 and not re.search(r"(?i)between|\bto\b|\band\b\s*\(?\$?\s?\d|[-–]\s*\(?\$?\d", line):
                vals = vals[:1]  # "of 641 million, including approximately 41 million ..." is point guidance
            if "loss" in low and metric == "adjusted_ebitda":
                vals = [-abs(v) for v in vals]
            out.append({"issued": issued, "period": period, "metric": metric, "low": min(vals), "high": max(vals),
                        "unit": unit, "statement": line[:400], "source": url, "parser": "guidance_tracker bullet block"})
    for m in re.finditer(r"(?i)stock-based compensation is (?:currently )?expected to range from \$?(\d[\d.,]*) million to "
                         r"\$?(\d[\d.,]*) million in Q([1-4]) (20\d\d)", text):
        out.append({"issued": issued, "period": f"Q{m.group(3)} FY{m.group(4)}", "metric": "sbc",
                    "low": float(m.group(1)), "high": float(m.group(2)), "unit": "USD millions",
                    "statement": m.group(0)[:400], "source": url, "parser": "guidance_tracker sentence"})
    return out


def normalize_guidance(ticker: str, root: Path = ROOT, as_of: Optional[str] = None) -> Dict[str, Any]:
    """Merge bullet-format guidance from cached releases into guidance.json (existing rows win)."""
    base = l4.company_dir(ticker, root)
    path = base / "management/guidance.json"
    existing = l4.read_json(path, []) or []
    keys = {(g["issued"], g["period"], g["metric"]) for g in existing}
    added = []
    for doc in msd.release_documents(ticker, root):
        if not doc["filed"] or (as_of and doc["filed"] > as_of):
            continue
        for g in parse_bullet_guidance(doc["text"], doc["filed"], doc["url"]):
            k = (g["issued"], g["period"], g["metric"])
            if k not in keys:
                keys.add(k)
                added.append(g)
    if added:
        merged = sorted(existing + added, key=lambda g: (g["issued"], g["period"], g["metric"]))
        l4.write_json(path, merged)
    return {"added": len(added), "total": len(existing) + len(added)}


# --------------------------------------------------------------------------- actuals

def _record(history: Dict[str, Any], period: str) -> Optional[Dict[str, Any]]:
    recs = history.get("quarters") if period.startswith("Q") else history.get("annual")
    return next((r for r in recs or [] if r.get("period") == period), None)


def _filed(rec: Dict[str, Any]) -> str:
    return max((p.get("filed") or "" for p in rec["metrics"].values() if isinstance(p, dict) and p.get("filed")),
               default="")


def actual_value(spec: Dict[str, Any], period: str, history: Dict[str, Any], reported: Dict[str, Any]
                 ) -> Tuple[str, Optional[float], str, str, str]:
    """(state, value, source, reported_date, confidence); state in reported / not_reported / missing."""
    typ = spec.get("type")
    rec = _record(history, period)
    if typ == "reported_kpis":
        k = reported.get(period) or {}
        key = spec["key"] if period.startswith("Q") else f"fy_{spec['key']}"
        if key in (k.get("values") or {}):
            return "reported", float(k["values"][key]), f"company earnings release {k.get('source')}", \
                k.get("date", ""), "high"
        return ("missing" if rec else "not_reported"), None, "", "", ""
    if rec is None:
        return "not_reported", None, "", "", ""
    m = rec["metrics"]
    if typ == "sec_history":
        p = m.get(spec["metric"])
        v = p.get("value") if isinstance(p, dict) else p
        if v is None:
            return "missing", None, "", _filed(rec), ""
        # medium confidence when the quarter was derived by YTD differencing (possibly from recast comparatives)
        parts = {"capex": ("capex_ppe", "capitalized_software"), "gross_margin_pct": ("gross_profit", "revenue"),
                 "operating_margin_pct": ("operating_income", "revenue")}.get(spec["metric"], (spec["metric"],))
        derived = any(isinstance(m.get(x), dict) and m[x].get("derived") for x in parts)
        src = (f"SEC {p.get('form')} {p.get('accn')} ({spec['metric']})" if isinstance(p, dict) and p.get("accn")
               else f"financials/history.json {spec['metric']}" + (f" = {p.get('calculation')}" if isinstance(p, dict)
                                                                     and p.get("calculation") else ""))
        return "reported", float(v), src, _filed(rec), "medium" if derived else "high"
    if typ == "calculation" and spec.get("formula") == "gross_profit - operating_income":
        gp, oi = m.get("gross_profit"), m.get("operating_income")
        gv = gp.get("value") if isinstance(gp, dict) else gp
        ov = oi.get("value") if isinstance(oi, dict) else oi
        if gv is None or ov is None:
            return "missing", None, "", _filed(rec), ""
        return "reported", round(gv - ov, 3), "Calculation: GAAP gross profit - operating income (financials/history.json)", \
            _filed(rec), "medium"
    return "missing", None, "", "", ""


def judge(metric: str, low: float, high: float, actual: float, kind: str = "") -> Tuple[str, str]:
    if kind == "spending_plan" or metric in SPENDING:
        if low <= actual <= high:
            return "delivered", "within guided spending range"
        edge = low if actual < low else high
        if abs(actual - edge) <= 0.02 * max(abs(edge), 1e-9):
            return "delivered", "at the edge of the guided spending range (within 2% tolerance)"
        side = "underspent" if actual < low else "overspent"
        dev = (low - actual) / max(abs(low), 1e-9) if actual < low else (actual - high) / max(abs(high), 1e-9)
        note = f"{side} vs plan by {dev:.0%}; a spending-plan deviation, not by itself a negative signal"
        return ("partially_delivered" if dev < 0.10 else "missed"), note
    return bmh.judge(metric, low, high, actual)


# --------------------------------------------------------------------------- resolution

def resolve_promises(ticker: str, root: Path = ROOT, as_of: Optional[str] = None) -> Dict[str, Any]:
    t = ticker.upper()
    base = l4.company_dir(t, root)
    as_of = l4.today(as_of)
    history = l4.read_json(base / "financials/history.json", {}) or {}
    reported = l4.read_json(base / "management/reported-kpis.json", {}) or {}
    guidance = [g for g in (l4.read_json(base / "management/guidance.json", []) or []) if g["issued"] <= as_of]
    existing = l4.read_json(base / "management/promises.json", []) or []
    ov = l4.read_yaml(base / "config/kpis.yaml", {}) or {}
    gmetrics = ov.get("guidance_metrics") or {}
    # Level 3 lifecycle (creation, supersession) stays the source of promise ids and fields.
    promises = bmh.update_promises(t, existing, guidance, history, reported, as_of) if guidance else existing
    rows = []
    for p in promises:
        g = p.get("guidance")
        if not g:
            p.setdefault("metric_definition", None)
            p.setdefault("comparison_basis", "qualitative / milestone (analyst-resolved)")
            p.setdefault("resolution_confidence", "analyst" if p.get("status") != "pending" else None)
            p.setdefault("actual_source", None)
            continue
        spec = gmetrics.get(g["metric"])
        prev_status = p.get("status")
        p["evaluated_by"] = "guidance_tracker.py"
        p["draft_auto"] = True
        if not spec:
            p["metric_definition"] = None
            p["comparison_basis"] = "unverified"
        else:
            p["metric_definition"] = {"company": spec.get("company_definition"),
                                      "actual": spec.get("actual_definition") or spec.get("company_definition")}
            p["comparison_basis"] = spec.get("comparison_basis", "unverified")
        state, value, src, rdate, conf = actual_value((spec or {}).get("actual") or {}, g["period"], history, reported) \
            if spec else ("not_reported" if _record(history, g["period"]) is None else "missing", None, "", "", "")
        if rdate and rdate > as_of:
            state = "not_reported"
        superseded = prev_status == "superseded"
        if state == "not_reported":
            p["status"] = "superseded" if superseded else "pending"
            p.update({"actual_result": None, "actual_source": None, "resolution_confidence": None,
                      "resolution_rule": "period not yet reported" + (f"; {p.get('superseded_by')}" if superseded else ""),
                      "resolved_date": None})
        elif p["comparison_basis"] not in EVALUABLE_BASES:
            reason = ("metric definition mismatch: " + str((spec or {}).get("company_definition", "")).strip()[:160]
                      + " vs " + str((spec or {}).get("actual_definition", "")).strip()[:120]
                      if p["comparison_basis"] == "definition_mismatch"
                      else "company metric definition not recorded in config/kpis.yaml guidance_metrics")
            p.update({"status": "not_evaluable", "comparison_basis": p["comparison_basis"] if spec else
                      "comparison_basis_mismatch", "actual_result": value, "actual_source": src or None,
                      "resolution_confidence": None, "resolution_rule": reason, "resolved_date": None})
        elif state == "missing":
            p.update({"status": "not_evaluable", "actual_result": None, "actual_source": None,
                      "resolution_confidence": None,
                      "resolution_rule": "period reported but the actual on the guided basis is not in local state",
                      "resolved_date": None})
        else:
            status, rule = judge(g["metric"], g["low"], g["high"], value, (spec or {}).get("kind", ""))
            p.update({"status": status, "actual_result": value, "actual_source": src, "resolution_confidence": conf,
                      "resolution_rule": rule, "resolved_date": rdate or as_of})
            ev = f"Actual {g['metric']} {value} vs guided {g['low']}..{g['high']} ({src})"
            if ev not in (p.get("evidence") or []):
                p["evidence"] = [e for e in (p.get("evidence") or []) if not e.startswith(f"Actual {g['metric']} ")] + [ev]
        p["review_required"] = p.get("resolution_confidence") != "high" and p["status"] not in ("pending", "superseded")
        p["last_checked"] = as_of
        rows.append(p)
    timing = timing_promises(t, root, as_of, promises)
    promises = [p for p in promises if not p.get("promise_id", "").startswith(f"{t}-milestone-")] + timing
    l4.write_json(base / "management/promises.json", promises)
    return {"promises": promises, "guidance_rows": rows, "timing": timing}


def timing_promises(ticker: str, root: Path, as_of: str, promises: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One promise per (subject, milestone) target; earlier targets that slipped become `delayed`."""
    base = l4.company_dir(ticker, root)
    claims = l4.read_json(base / "management/claims.json", []) or []
    old = {p["promise_id"]: p for p in promises if p.get("promise_id", "").startswith(f"{ticker}-milestone-")}
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for c in claims:
        if c.get("claim_type") == "operational_milestone" and c.get("milestone") == "first_launch" and c.get("timing_end") \
                and c.get("source_date", "") <= as_of:
            groups.setdefault((c["subject"], c["milestone"]), []).append(c)
    out = []
    for (subj, ms), cs in sorted(groups.items()):
        targets: List[Dict[str, Any]] = []
        for c in sorted(cs, key=lambda c: c["source_date"]):
            if targets and targets[-1]["timing_end"] == c["timing_end"]:
                continue
            targets.append(c)
        for i, c in enumerate(targets):
            pid = f"{ticker}-milestone-{subj.lower()}-{ms}-{c['source_date']}"
            nxt = targets[i + 1] if i + 1 < len(targets) else None
            if nxt and nxt["timing_end"] > c["timing_end"]:
                status, rule = "delayed", f"target moved {c['timing']} → {nxt['timing']} ({nxt['source_date']})"
            elif nxt:
                status, rule = "superseded", f"target restated as {nxt['timing']} ({nxt['source_date']})"
            elif c["timing_end"] < as_of:
                status, rule = "pending", "target window passed; completion evidence not in local state — review"
            else:
                status, rule = "pending", "target window not reached"
            p = dict(old.get(pid, {}))
            p.update({"promise_id": pid, "topic": "operational milestone", "statement_date": c["source_date"],
                      "management_claim": c["statement"][:300], "target_date": c["timing"],
                      "expected_result": f"{subj} {ms.replace('_', ' ')} by end of {c['timing']}",
                      "source": c["source"], "status": status, "resolution_rule": rule,
                      "metric_definition": None, "comparison_basis": "timing claim (same subject and milestone)",
                      "resolution_confidence": "medium" if status in ("delayed", "superseded") else None,
                      "actual_result": None, "actual_source": nxt["source"] if nxt else None,
                      "resolved_date": nxt["source_date"] if nxt and status == "delayed" else None,
                      "draft_auto": True, "review_required": True, "evaluated_by": "guidance_tracker.py",
                      "evidence": [f"claim {c['source_date']}: {c['statement'][:160]}"] +
                                  ([f"later claim {nxt['source_date']}: {nxt['statement'][:160]}"] if nxt else []),
                      "last_checked": as_of})
            out.append(p)
    return out


# --------------------------------------------------------------------------- report

def summarize(promises: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for p in promises:
        counts[p.get("status", "?")] = counts.get(p.get("status", "?"), 0) + 1
    guided = [p for p in promises if p.get("guidance")]
    evaluable = [p for p in guided if p.get("status") in ("delivered", "partially_delivered", "missed")]
    return {"counts": counts, "guidance_promises": len(guided), "evaluated": len(evaluable),
            "not_evaluable": sum(p.get("status") == "not_evaluable" for p in promises),
            "message": None if guided else NO_GUIDANCE,
            "caveat": "Counts only; not a credibility score."}


def render(ticker: str, as_of: str, promises: List[Dict[str, Any]], summ: Dict[str, Any]) -> str:
    L = [f"# {ticker} Guidance vs Actual（{as_of}）", "",
         "> draft_auto：自動結案只在公司 metric 定義與實際值口徑一致時進行；口徑不一致或未記錄定義 → not_evaluable。"
         "Spending plan（capex / opex）偏離區間是「與計畫不同」，少花不等於負面。", ""]
    if summ["message"]:
        L += [summ["message"], ""]
    L += ["狀態計數：" + (", ".join(f"{k} {v}" for k, v in sorted(summ["counts"].items())) or "無"), "",
          "| Promise | Metric | Period | Guided | Actual | Status | Basis | Confidence | Rule |", "|---|---|---|---|---|---|---|---|---|"]
    for p in sorted(promises, key=lambda p: (p.get("statement_date", ""), p["promise_id"]))[-60:]:
        g = p.get("guidance") or {}
        guided = f"{g.get('low')}–{g.get('high')} {g.get('unit', '')}" if g else (p.get("target_date") or "")
        L.append(f"| {p['promise_id']} | {g.get('metric', p.get('topic', ''))} | {g.get('period', p.get('target_date', ''))} | "
                 f"{guided} | {p.get('actual_result') if p.get('actual_result') is not None else '—'} | {p.get('status')} | "
                 f"{p.get('comparison_basis') or '—'} | {p.get('resolution_confidence') or '—'} | "
                 f"{(p.get('resolution_rule') or '').replace('|', '/')[:120]} |")
    return "\n".join(L) + "\n"


def track(ticker: str, root: Path = ROOT, as_of: Optional[str] = None, parse: bool = True,
          write: bool = True) -> Dict[str, Any]:
    t = ticker.upper()
    as_of = l4.today(as_of)
    norm = normalize_guidance(t, root, as_of) if parse else {"added": 0}
    msd.run(t, root, as_of, write=True)
    res = resolve_promises(t, root, as_of)
    summ = summarize(res["promises"])
    out = {"ticker": t, "as_of": as_of, "guidance_added": norm["added"], **summ,
           "rows": [{k: p.get(k) for k in ("promise_id", "status", "actual_result", "comparison_basis",
                                             "resolution_confidence", "resolution_rule", "actual_source",
                                             "review_required")} | {"guidance": p.get("guidance")}
                    for p in res["promises"]]}
    if write:
        base = l4.company_dir(t, root)
        l4.write_json(base / "management/guidance-vs-actual.json", out)
        (base / "management/guidance-vs-actual.md").write_text(render(t, as_of, res["promises"], summ), encoding="utf-8")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--as-of")
    ap.add_argument("--no-parse", action="store_true", help="skip release parsing (use guidance.json as is)")
    args = ap.parse_args(argv)
    out = track(args.ticker, as_of=args.as_of, parse=not args.no_parse)
    print(f"{out['ticker']}: +{out['guidance_added']} guidance rows; {out['counts']}"
          + (f"; {out['message']}" if out["message"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
