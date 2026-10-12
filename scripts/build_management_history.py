#!/usr/bin/env python3
"""Management history: statements, guidance, cross-quarter changes and promise lifecycle.

Sources (Tier 1 only, automated): SEC 8-K Item 2.02 earnings exhibits (EX-99.1).
10-Q / 10-K figures enter through financials/history.json. Transcripts are not
fetched; their absence never blocks the workflow (Tier 2, optional, manual).

Steps
  1. earnings events   : 8-K Item 2.02 filings -> market/events.csv (merged, never dropped)
  2. statements        : sentences quoted verbatim from each release, tagged by topic
                         -> management/statements.json (merged with existing entries)
  3. guidance          : structured ranges (period, metric, low, high) -> management/guidance.json
  4. reported KPIs     : company-reported non-GAAP figures in each release
                         (non-GAAP gross margin, adjusted EBITDA) -> management/reported-kpis.json
  5. changes           : per topic, quarter-over-quarter comparison -> management/changes.md
  6. promises          : guidance becomes promises; each is resolved against reported
                         actuals once the target period is reported -> management/promises.json

Topic tagging and tone are keyword heuristics (labelled low confidence). A tone
change is recorded as wording, never as evidence that fundamentals changed.
No management credibility score is produced.

Usage (network): python3 scripts/build_management_history.py PL --cik 1836833 [--quarters 8]
Offline re-run from cached raw/ files: add --offline
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_fundamental_history import _v, load_history  # noqa: E402

TOPICS: List[Tuple[str, Tuple[str, ...]]] = [
    ("guidance", ("expects revenue", "expect revenue", "outlook", "expected to be in the range", "guidance",
                  "expects to", "for the full fiscal year", "for the full year")),
    ("backlog_rpo", ("remaining performance obligation", "rpo", "backlog")),
    ("dilution", ("at-the-market", "atm program", "share repurchase", "buyback", "convertible", "warrant",
                  "dilution", "equity offering", "shares of common stock")),
    ("cash_flow", ("free cash flow", "cash provided by operating", "cash flow", "cash, cash equivalents")),
    ("capex", ("capital expenditure", "capex")),
    ("margins", ("gross margin", "adjusted ebitda", "operating margin", "operating leverage", "profitab")),
    ("constraints", ("constraint", "supply chain", "shortage", "delay", "headwind", "bottleneck", "capacity",
                     "tariff", "shutdown", "continuing resolution")),
    ("customer_qualification", ("qualif", "certif", "accredit", "authorization to operate", "fedramp")),
    ("product_launch", ("launch", "satellite", "beta", "introduc", "unveil", "release of", "new product",
                        "manufactur")),
    ("customers", ("customer", "contract", "award", "agreement", "renewal", "partnership", "partnered", "signed")),
    ("demand", ("demand", "pipeline", "momentum", "traction", "record revenue", "growth")),
]
CONFIDENT = ("record", "strong", "outstanding", "accelerat", "exceed", "momentum", "confident", "robust",
             "significant", "landmark", "incredible", "traction", "expand", "beat")
CAUTIOUS = ("uncertain", "headwind", "delay", "challeng", "soft", "cautious", "decline", "pressure", "slower",
            "weak", "risk", "shutdown", "lower than", "pushed", "timing")
STOP_SECTIONS = ("forward-looking statements", "use of non-gaap", "about planet", "about ", "webcast and conference",
                 "has not reconciled", "condensed consolidated", "investor contact", "press contact")
METRIC_WORDS = [
    ("non_gaap_gross_margin", ("non-gaap gross margin",)),
    ("gross_margin", ("gross margin",)),
    ("adjusted_ebitda", ("adjusted ebitda",)),
    ("capex", ("capital expenditure", "capex")),
    ("operating_income", ("operating income", "operating loss")),
    ("eps", ("per share",)),
    ("revenue", ("revenue",)),
]
ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4}


# --------------------------------------------------------------------------- parsing helpers

def sentences(text: str) -> List[str]:
    out = []
    lower = text.lower()
    cut = len(text)
    for marker in ("forward-looking statements", "use of non-gaap financial measures\n", "about planet labs"):
        i = lower.find(marker, 2000)
        if i > 0:
            cut = min(cut, i)
    for line in text[:cut].split("\n"):
        line = line.strip(" •\t")
        if len(line) < 40:
            continue
        for s in re.split(r"(?:(?<=[.!?])|(?<=[.!?][”\"]))\s+(?=[A-Z“\"(])", line):
            s = s.strip()
            if 40 <= len(s) <= 600 and not re.match(r"^[\d$(),.%\s-]+$", s):
                out.append(s)
    return out


def topic_of(sentence: str) -> Optional[str]:
    s = sentence.lower()
    if any(k in s for k in STOP_SECTIONS[:4]):
        return None
    if ("expect" in s or "outlook" in s) and re.search(r"\$\s?\(?\d|\d+%", s) and \
            re.search(r"fiscal year|quarter|full year", s):
        return "guidance"
    for topic, words in TOPICS:
        if topic == "guidance":
            continue
        if any(w in s for w in words):
            return topic
    return None


def tone(sentence: str) -> int:
    s = sentence.lower()
    return sum(w in s for w in CONFIDENT) - sum(w in s for w in CAUTIOUS)


def _num(tok: str) -> Optional[float]:
    tok = tok.replace(",", "")
    neg = "(" in tok or tok.strip().startswith("-")
    m = re.search(r"\d+(?:\.\d+)?", tok)
    if not m:
        return None
    v = float(m.group())
    return -v if neg else v


_NUM = re.compile(r"\(\$?\s?\d[\d,]*(?:\.\d+)?\)(?:\s*(?:million|billion))?|\$\s?\d[\d,]*(?:\.\d+)?(?:\s*(?:million|billion))?|\d+(?:\.\d+)?\s?%")


def _period_of(text: str) -> Optional[str]:
    low = text.lower()
    m = re.search(r"(first|second|third|fourth) (?:fiscal )?quarter(?: of)?(?: fiscal(?: year)?)? (\d{4})", low)
    if m:
        return f"Q{ORDINAL[m.group(1)]} FY{m.group(2)}"
    m = re.search(r"(?:full )?fiscal (?:year )?(\d{4})", low) or re.search(r"full year (\d{4})", low)
    return f"FY{m.group(1)}" if m else None


def parse_guidance_sentence(sentence: str, period: str, issued: str) -> Optional[Dict[str, Any]]:
    cl = sentence.lower()
    metric = next((name for name, words in METRIC_WORDS if any(w in cl for w in words)), None)
    if not metric or not re.search(r"expect|range|between|outlook", cl):
        return None
    toks = _NUM.findall(sentence)
    if not toks:
        return None
    unit = "%" if any("%" in t for t in toks) else ("USD billions" if any("billion" in t for t in toks) else "USD millions")
    vals = [_num(t) for t in toks if ("%" in t) == (unit == "%")]
    vals = [v for v in vals if v is not None][:2]
    if not vals:
        return None
    if "loss" in cl and metric in ("adjusted_ebitda", "operating_income") and not any("(" in t for t in toks):
        vals = [-abs(v) for v in vals]
    return {"issued": issued, "period": period, "metric": metric, "low": min(vals), "high": max(vals),
            "unit": unit, "statement": sentence.strip()[:400]}


def parse_outlook(text: str, issued: str) -> List[Dict[str, Any]]:
    """Structured guidance from the release's Outlook section; later sentences inherit
    the period named at the start of their paragraph ("For the third quarter of fiscal year 2027 ...")."""
    low = text.lower()
    start = low.find("outlook")
    while start >= 0 and not re.search(r"expect", low[start:start + 600]):
        start = low.find("outlook", start + 7)
    if start < 0:
        return []
    ends = [i for i in (low.find("has not reconciled", start), low.find("forward-looking", start),
                        low.find("webcast", start)) if i > 0]
    section = text[start:min(ends) if ends else start + 3000].replace("–", "-")
    out = []
    for para in re.split(r"(?i)(?=\bfor (?:the )?(?:full )?(?:fiscal year|first|second|third|fourth|full year))", section):
        period = _period_of(para[:200])
        if not period:
            continue
        for sent in re.split(r"(?<=\.)\s+", para):
            g = parse_guidance_sentence(sent, period, issued)
            if g:
                out.append(g)
    return out


def parse_reported_kpis(text: str) -> Dict[str, float]:
    """Company-reported non-GAAP figures stated in the release (quarter and, in Q4, full year)."""
    low = text.lower().replace("’", "'")
    out: Dict[str, float] = {}
    pats = {
        "non_gaap_gross_margin": r"(?:first|second|third|fourth) quarter non-gaap gross margin was (?:a record )?(\d+(?:\.\d+)?)%",
        "fy_non_gaap_gross_margin": r"full (?:fiscal )?year non-gaap gross margin was (?:a record )?(\d+(?:\.\d+)?)%",
    }
    for k, pat in pats.items():
        m = re.search(pat, low)
        if m:
            out[k] = float(m.group(1))
    ebitda = {
        "adjusted_ebitda": r"(?:first|second|third|fourth) quarter adjusted ebitda(?: (profit|loss|income))? was (?:a )?(\(?)\$\(?(\d+(?:\.\d+)?)",
        "fy_adjusted_ebitda": r"full (?:fiscal )?year adjusted ebitda(?: (profit|loss|income))? was (?:a )?(\(?)\$\(?(\d+(?:\.\d+)?)",
    }
    for k, pat in ebitda.items():
        m = re.search(pat, low)
        if m:
            v = float(m.group(3))
            out[k] = -v if (m.group(1) == "loss" or m.group(2)) else v
    return out


# --------------------------------------------------------------------------- periods

def reported_period(filed: str, quarter_ends: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    """Latest fiscal quarter (label, end) ending 10-120 days before the release."""
    f = date.fromisoformat(filed)
    cands = [(lab, e) for lab, e in quarter_ends if 5 <= (f - date.fromisoformat(e)).days <= 120]
    return max(cands, key=lambda x: x[1]) if cands else None


def release_timing(acceptance: str) -> str:
    """amc / bmo / during from the EDGAR acceptance timestamp (UTC)."""
    if not acceptance:
        return "unknown"
    try:
        ts = datetime.fromisoformat(acceptance.replace("Z", "+00:00")).astimezone(ZoneInfo("America/New_York"))
    except ValueError:
        return "unknown"
    t = ts.hour * 60 + ts.minute
    return "amc" if t >= 16 * 60 else ("bmo" if t < 9 * 60 + 30 else "during session")


# --------------------------------------------------------------------------- promises

def promise_id(ticker: str, g: Dict[str, Any]) -> str:
    per = g["period"].lower().replace(" fy", "-fy")  # "q3-fy2027" / "fy2027"
    if per.startswith("q"):
        per = per.split("-")[0]  # existing ids use "q3"
    else:
        per = "fy" + per[-2:]
    short = {"revenue": "revenue", "non_gaap_gross_margin": "gm", "gross_margin": "gm",
             "adjusted_ebitda": "ebitda", "capex": "capex"}.get(g["metric"], g["metric"])
    return f"{ticker}-{g['issued']}-{per}-{short}"


def actual_for(metric: str, period: str, history: Dict[str, Any], kpis: Dict[str, Dict[str, Any]]
               ) -> Optional[Tuple[float, str, str]]:
    """(value, source, reported_date) for a guidance metric/period, or None if not yet reported."""
    recs = history["quarters"] if period.startswith("Q") else history["annual"]
    rec = next((r for r in recs if r["period"] == period), None)
    if rec is None:
        return None
    m = rec["metrics"]
    filed = max((p.get("filed") or "" for p in m.values() if isinstance(p, dict) and p.get("filed")), default="")
    if metric == "revenue" and _v(m, "revenue") is not None:
        return _v(m, "revenue"), f"SEC {m['revenue'].get('form')} {m['revenue'].get('accn')} (revenue)", filed
    if metric == "capex" and _v(m, "capex") is not None:
        return _v(m, "capex"), "SEC cash flow: PP&E purchases + capitalized software (financials/history.json)", filed
    if metric == "gross_margin" and _v(m, "gross_margin_pct") is not None:
        return _v(m, "gross_margin_pct"), "GAAP gross margin (financials/history.json)", filed
    k = kpis.get(period) or {}
    key = metric if period.startswith("Q") else f"fy_{metric}"
    if key in k.get("values", {}):
        return k["values"][key], f"company earnings release {k.get('source')}", k.get("date", filed)
    return None


def judge(metric: str, low: float, high: float, actual: float) -> Tuple[str, str]:
    """delivered / partially_delivered / missed with the rule used (direction-aware)."""
    if metric == "capex":  # a spending plan: inside the range is delivery; outside is a deviation
        basis = " (capex = PP&E purchases + capitalized software; company definition may differ)"
        if low <= actual <= high:
            return "delivered", "within guided spending range" + basis
        side = "underspent" if actual < low else "overspent"
        tol = 0.1 * max(abs(high), 1)
        return ("partially_delivered", f"{side} vs plan by <10%" + basis) if low - tol <= actual <= high + tol \
            else ("missed", f"{side} vs plan by >=10%" + basis)
    if actual >= low:
        return "delivered", "at or above low end of range"
    shortfall = (low - actual) / max(abs(low), 1)
    return ("partially_delivered", "below low end by <2%") if shortfall < 0.02 else ("missed", "below low end of range")


def update_promises(ticker: str, existing: List[Dict[str, Any]], guidance: List[Dict[str, Any]],
                    history: Dict[str, Any], kpis: Dict[str, Dict[str, Any]], as_of: str) -> List[Dict[str, Any]]:
    by_id = {p["promise_id"]: dict(p) for p in existing}
    latest_issue: Dict[Tuple[str, str], str] = {}
    for g in guidance:
        k = (g["period"], g["metric"])
        latest_issue[k] = max(latest_issue.get(k, ""), g["issued"])
    for g in guidance:
        if g["issued"] > as_of:
            continue
        pid = promise_id(ticker, g)
        p = by_id.get(pid, {})
        p.update({k: p.get(k) or v for k, v in {
            "promise_id": pid, "topic": "guidance", "statement_date": g["issued"],
            "management_claim": g["statement"], "target_date": g["period"],
            "expected_result": f"{g['metric']} {g['low']}..{g['high']} {g['unit']} for {g['period']}",
            "source": g.get("source", ""), "evidence": [], "status": "pending"}.items()})
        p["guidance"] = {k: g[k] for k in ("period", "metric", "low", "high", "unit")}
        by_id[pid] = p
    for pid, p in by_id.items():
        g = p.get("guidance")
        if not g:
            p.setdefault("actual_result", None)
            p.setdefault("resolved_date", None)
            continue
        act = actual_for(g["metric"], g["period"], history, kpis)
        if act is None:
            later = latest_issue.get((g["period"], g["metric"]), "")
            if later > p["statement_date"] and later <= as_of:
                p["status"] = "superseded"
                p["superseded_by"] = f"guidance issued {later}"
            p.setdefault("actual_result", None)
            p.setdefault("resolved_date", None)
            p["last_checked"] = as_of
            continue
        value, source, reported = act
        if reported and reported > as_of:
            continue
        status, rule = judge(g["metric"], g["low"], g["high"], value)
        if g["metric"] in ("non_gaap_gross_margin", "adjusted_ebitda") and "release" not in source:
            status, rule = "pending", "actual not reported on the guided (non-GAAP) basis"
        later = latest_issue.get((g["period"], g["metric"]), "")
        p.update({"status": status, "actual_result": value, "resolution_rule": rule,
                  "resolved_date": reported or as_of, "last_checked": as_of})
        if later > p["statement_date"]:
            p["superseded_by"] = f"guidance issued {later} (outcome still evaluated vs this range)"
        ev = f"Actual {g['metric']} {value} vs guided {g['low']}..{g['high']} ({source})"
        if ev not in p.get("evidence", []):
            p["evidence"] = list(p.get("evidence", [])) + [ev]
    return sorted(by_id.values(), key=lambda p: (p.get("statement_date", ""), p["promise_id"]))


def promise_counts(promises: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for p in promises:
        counts[p.get("status", "?")] = counts.get(p.get("status", "?"), 0) + 1
    return {"counts": counts, "caveat": "Counts only; not a credibility score. Guidance ranges are set by "
                                        "management and mostly quantitative; a small sample says little."}


# --------------------------------------------------------------------------- changes.md

def guidance_changes(guidance: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for g in guidance:
        groups.setdefault((g["period"], g["metric"]), []).append(g)
    for (period, metric), gs in groups.items():
        gs = sorted(gs, key=lambda g: g["issued"])
        for a, b in zip(gs, gs[1:]):
            ma, mb = (a["low"] + a["high"]) / 2, (b["low"] + b["high"]) / 2
            tol = 0.25 if a["unit"] == "%" else max(abs(ma) * 0.01, 0.5)
            change = "maintained" if abs(mb - ma) <= tol else ("raised" if mb > ma else "lowered")
            if metric == "capex" and change != "maintained":
                change += " (spending plan)"
            out.append({"period": period, "metric": metric, "from": [a["low"], a["high"]], "to": [b["low"], b["high"]],
                        "issued_from": a["issued"], "issued_to": b["issued"], "change": change, "unit": a["unit"]})
    return out


def render_changes(ticker: str, statements: List[Dict[str, Any]], guidance: List[Dict[str, Any]],
                   promises: List[Dict[str, Any]], periods: List[str]) -> str:
    lines = [f"# {ticker} 管理層措辭與 guidance 跨季變化（Management changes）", "",
             "來源：SEC 8-K Item 2.02 財報新聞稿（Tier 1）原文引用；逐字稿未納入（Tier 2，非必要）。",
             "主題分類與語氣為關鍵字 heuristic（低信心）。語氣改變只記錄為措辭變化，不視為基本面惡化的證據。", ""]
    gc = guidance_changes(guidance)
    lines += ["## Guidance 變化（raised / maintained / lowered）", ""]
    if gc:
        lines += ["| 期間 | 指標 | 前次 | 本次 | 變化 |", "|---|---|---|---|---|"]
        for c in sorted(gc, key=lambda c: (c["issued_to"], c["period"], c["metric"])):
            lines.append(f"| {c['period']} | {c['metric']} | {c['from'][0]}–{c['from'][1]} {c['unit']}（{c['issued_from']}） | "
                         f"{c['to'][0]}–{c['to'][1]} {c['unit']}（{c['issued_to']}） | {c['change']} |")
    else:
        lines.append("- 同一期間僅有一次 guidance，無法比較。")
    lines += ["", "## 主題逐季比較", ""]
    auto = [s for s in statements if s.get("extraction") == "auto"]
    for topic, _ in TOPICS:
        rows = [s for s in auto if s["topic"] == topic]
        if not rows:
            continue
        lines += [f"### Topic: {topic}", ""]
        tones = []
        for per in periods[-8:]:
            ps = [s for s in rows if s["period"] == per]
            if not ps:
                lines.append(f"**{per}:** （無相關陳述）")
                tones.append(None)
                continue
            t = sum(s.get("tone", 0) for s in ps) / len(ps)
            tones.append(t)
            lines.append(f"**{per}:** “{ps[0]['statement'][:300]}”" + (f"（另 {len(ps) - 1} 則）" if len(ps) > 1 else ""))
        valid = [t for t in tones if t is not None]
        if len(valid) >= 2:
            d = valid[-1] - valid[-2]
            obs = "more confident" if d > 0.5 else ("more cautious" if d < -0.5 else "unchanged")
        else:
            obs = "insufficient periods"
        lines += ["", f"Observed change: language {obs}（關鍵字語氣分數 {['n/a' if t is None else round(t, 1) for t in tones]}）",
                  "Interpretation: 措辭訊號，需以報表數字確認；不單獨構成論點變化。",
                  "Confidence: low（keyword heuristic）", ""]
    pc = promise_counts(promises)
    lines += ["## Promise tracker", "", "- " + ", ".join(f"{k}: {v}" for k, v in sorted(pc["counts"].items())),
              f"- {pc['caveat']}", ""]
    for p in promises:
        if p.get("status") in ("missed", "partially_delivered"):
            lines.append(f"- {p['promise_id']}: {p['status']} — {p.get('evidence', [''])[-1]}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- main build

EVENT_HEADER = ["event_date", "event_type", "description", "source", "timing"]


def merge_events(path: Path, new: List[Dict[str, str]]) -> int:
    rows: Dict[Tuple[str, str], Dict[str, str]] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                rows[(r["event_date"], r["event_type"])] = r
    for r in new:
        key = (r["event_date"], r["event_type"])
        if key not in rows:
            rows[key] = r
        elif str(rows[key].get("timing", "")).startswith("unknown") and not r["timing"].startswith("unknown"):
            rows[key]["timing"] = f"{r['timing']} (EDGAR acceptance time)"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=EVENT_HEADER, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows[k] for k in sorted(rows))
    return len(rows)


def build(ticker: str, cik: str, root: Path = ROOT, n_quarters: int = 8, offline: bool = False,
          as_of: Optional[str] = None) -> Dict[str, Any]:
    import sec_data
    t = ticker.upper()
    base = root / "research" / t
    as_of = as_of or date.today().isoformat()
    history = load_history(t, root)
    if not history:
        raise ValueError("financials/history.json missing; run build_fundamental_history.py first")
    q_ends = [(r["period"], r["period_end"]) for r in history["quarters"]]
    sub = sec_data.submissions(cik, t, root, refresh=not offline)
    filings = [f for f in sec_data.recent_filings(sub, ("8-K",)) if "2.02" in (f.get("items") or "")
               and f["filed"] <= as_of]
    filings = sorted(filings, key=lambda f: f["filed"])[-(n_quarters + 1):]

    statements_auto, guidance, kpis, events = [], [], {}, []
    for f in filings:
        per = reported_period(f["filed"], q_ends)
        label = per[0] if per else f"release {f['filed']}"
        ex = sec_data.earnings_exhibit(cik, t, f["accession"], root)
        events.append({"event_date": f["filed"], "event_type": "8-K 2.02 earnings",
                       "description": f"{label} results" + (" and outlook" if ex else ""),
                       "source": ex["url"] if ex else sec_data.filing_base_url(cik, f["accession"]),
                       "timing": release_timing(f.get("acceptance", ""))})
        if not ex:
            continue
        kp = parse_reported_kpis(ex["text"])
        if kp:
            kpis[label] = {"values": kp, "source": ex["url"], "date": f["filed"]}
            # Q4 releases carry full-year figures for the fiscal year
            if label.startswith("Q4 "):
                fy = label.split(" ")[1]
                fyv = {k: v for k, v in kp.items() if k.startswith("fy_")}
                if fyv:
                    kpis[fy] = {"values": fyv, "source": ex["url"], "date": f["filed"]}
        for g in parse_outlook(ex["text"], f["filed"]):
            g["source"] = ex["url"]
            guidance.append(g)
        per_topic: Dict[str, int] = {}
        for s in sentences(ex["text"]):
            topic = topic_of(s)
            if topic is None:
                continue
            if per_topic.get(topic, 0) >= 3:
                continue
            per_topic[topic] = per_topic.get(topic, 0) + 1
            statements_auto.append({
                "period": label, "topic": topic, "statement": s, "verbatim": True, "source": ex["url"],
                "source_type": "8-K Item 2.02 earnings release (EX-99.1)", "date": f["filed"],
                "evidence_strength": "Tier 1 primary filing; verbatim management text",
                "interpretation": "", "tone": tone(s), "extraction": "auto",
                "classification": "Fact (quoted statement)"})

    # de-duplicate guidance (same issue/period/metric)
    gd: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for g in guidance:
        gd.setdefault((g["issued"], g["period"], g["metric"]), g)
    guidance = sorted(gd.values(), key=lambda g: (g["issued"], g["period"], g["metric"]))

    mdir = base / "management"
    mdir.mkdir(parents=True, exist_ok=True)
    existing = json.loads((mdir / "statements.json").read_text()) if (mdir / "statements.json").exists() else []
    seen = {(s.get("period"), s.get("topic"), s.get("statement")) for s in existing}
    for s in existing:
        s.setdefault("source_type", "analyst-curated from primary filing")
        s.setdefault("extraction", "manual")
    merged = existing + [s for s in statements_auto if (s["period"], s["topic"], s["statement"]) not in seen]
    (mdir / "statements.json").write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    old_g = json.loads((mdir / "guidance.json").read_text()) if (mdir / "guidance.json").exists() else []
    gkeys = {(g["issued"], g["period"], g["metric"]) for g in guidance}
    guidance = sorted([g for g in old_g if (g["issued"], g["period"], g["metric"]) not in gkeys] + guidance,
                      key=lambda g: (g["issued"], g["period"], g["metric"]))
    (mdir / "guidance.json").write_text(json.dumps(guidance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    old_k = json.loads((mdir / "reported-kpis.json").read_text()) if (mdir / "reported-kpis.json").exists() else {}
    old_k.update(kpis)
    (mdir / "reported-kpis.json").write_text(json.dumps(old_k, indent=2) + "\n", encoding="utf-8")

    promises_path = mdir / "promises.json"
    promises = update_promises(t, json.loads(promises_path.read_text()) if promises_path.exists() else [],
                               guidance, history, old_k, as_of)
    promises_path.write_text(json.dumps(promises, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    periods = sorted({s["period"] for s in statements_auto},
                     key=lambda p: next((e for lab, e in q_ends if lab == p), p))
    (mdir / "changes.md").write_text(render_changes(t, merged, guidance, promises, periods), encoding="utf-8")
    n_events = merge_events(base / "market/events.csv", events)
    return {"releases": len(filings), "periods": periods, "statements_added": len(merged) - len(existing),
            "statements_total": len(merged), "guidance_records": len(guidance), "events_total": n_events,
            **promise_counts(promises)}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--cik", required=True)
    ap.add_argument("--quarters", type=int, default=8)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--as-of")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args(argv)
    print(json.dumps(build(args.ticker, args.cik, args.root, args.quarters, args.offline, args.as_of), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
