#!/usr/bin/env python3
"""Management semantic diff (Level 4): structured claims + cross-quarter comparison.

Level 3 tagged statements by keyword and averaged a tone score. Level 4 turns the
same stored evidence (management/statements.json, management/guidance.json and the
cached earnings releases in raw/filings/) into structured claims and compares them
topic by topic across quarters on explicit dimensions:

  quantitative_guidance  ranges for the same metric / target period (raised, lowered, ...)
  timing                 milestone target dates for the same subject (slipped, pulled in)
  confidence_shift       hedged vs committed wording (wording only; low confidence)
  bottleneck             constraint / delay / qualification wording appearing or disappearing
  customer_demand        demand / contract / backlog wording
  capex_stance           investment acceleration vs discipline wording
  margin_stance          expansion vs pressure wording
  product_launch         milestone progress words (qualified, delivered, launched)

Each finding is written as
  FACT            verbatim text (or a labelled paraphrase) with source and date
  CHANGE          what differs from the previous quarter
  INTERPRETATION  what it may mean, never stronger than the evidence
  CONFIDENCE      high / medium / low
Wording-only changes are never interpreted as a fundamental change; numbers or dated
milestones are required for that. Everything here is `draft_auto` and, unless the
confidence is high, `review_required: true`.

Structured claim types: point_guidance, range_guidance, qualitative_guidance,
timing_promise, operational_milestone. A qualitative statement such as "Margins
should improve in H2" stays qualitative_guidance (direction + timing, no numbers).

Outputs (research/<TICKER>/management/):
  claims.json          structured claims
  semantic-diff.json   findings by topic / dimension
  semantic-diff.md     Traditional Chinese summary table

Usage: python3 scripts/management_semantic_diff.py PL [--as-of YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import level4_common as l4  # noqa: E402

FORWARD = re.compile(r"\b(expect|expects|expected|anticipate|plan|plans|planned|target|targeted|targeting|on track|"
                     r"will|should|scheduled|aim|aims|intend|guid|outlook|look forward|remains? on track)\w*", re.I)
COMMITTED = ("on track", "will ", "committed", "confident", "record", "remain on track", "remains on track")
HEDGED = ("may ", "could ", "potential", "subject to", "pending", "if ", "uncertain", "approximately", "assuming",
          "depend", "risk", "we believe")
BOTTLENECK = ("constrain", "supply", "capacity", "delay", "bottleneck", "shortage", "qualification", "failure",
              "anomaly", "rework", "slip", "push", "backlog of work", "tank test")
DEMAND = ("demand", "pipeline", "bookings", "backlog", "contract", "orders", "customer", "renewal", "award", "won ")
CAPEX_UP = ("invest", "expand capacity", "build-out", "build out", "increase capex", "scaling", "new facility")
CAPEX_DOWN = ("disciplined", "reduce capex", "lower capex", "moderate", "capital efficiency")
MARGIN_UP = ("margin expansion", "expand", "improve", "higher margin", "record gross margin", "record margin")
MARGIN_DOWN = ("margin pressure", "compress", "lower margin", "decline in margin", "headwind")
PROGRESS = ("completed", "qualified", "delivered", "shipped", "launched", "achieved", "first light", "commissioned",
            "arrived", "successful")
METRIC_TOPIC = {"revenue": "revenue", "gross_margin": "margins", "non_gaap_gross_margin": "margins",
                "adjusted_ebitda": "profitability", "capex": "capex", "gaap_operating_expenses": "opex",
                "non_gaap_operating_expenses": "opex", "basic_shares_guided": "dilution", "sbc": "dilution"}
DEFAULT_SUBJECT_WORDS = ("launch", "debut", "first flight", "first launch", "availability", "commercial service")

_TIMING = [
    (re.compile(r"\bQ([1-4])[,\s]+(?:FY)?\s?(20\d\d)\b", re.I), "q"),
    (re.compile(r"\b(first|second|third|fourth) quarter of (?:fiscal (?:year )?)?(20\d\d)\b", re.I), "qw"),
    (re.compile(r"\b(first|second) half of (?:fiscal (?:year )?)?(20\d\d)\b", re.I), "h"),
    (re.compile(r"\bH([12])\s?(20\d\d)\b", re.I), "hn"),
    (re.compile(r"\b(?:by |before )?(?:the )?end of (20\d\d)\b", re.I), "y"),
    (re.compile(r"\b(later this year|this year|by year[- ]end|end of the year)\b", re.I), "ty"),
    (re.compile(r"\b(next year)\b", re.I), "ny"),
    (re.compile(r"\bin (20\d\d)\b", re.I), "y"),
]
_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}


def parse_timing(text: str, source_date: str) -> Optional[Dict[str, Any]]:
    """First timing token → {label, end (ISO date of the window end), precision}. Never an exact day."""
    year_now = int(source_date[:4]) if source_date else date.today().year
    for rx, kind in _TIMING:
        m = rx.search(text)
        if not m:
            continue
        if kind == "q":
            q, y = int(m.group(1)), int(m.group(2))
            return {"label": f"Q{q} {y}", "end": f"{y}-{[3, 6, 9, 12][q - 1]:02d}-{[31, 30, 30, 31][q - 1]}",
                    "precision": "quarter"}
        if kind == "qw":
            q, y = _ORD[m.group(1).lower()], int(m.group(2))
            return {"label": f"Q{q} {y}", "end": f"{y}-{[3, 6, 9, 12][q - 1]:02d}-{[31, 30, 30, 31][q - 1]}",
                    "precision": "quarter"}
        if kind in ("h", "hn"):
            h = _ORD.get(m.group(1).lower(), None) if kind == "h" else int(m.group(1))
            y = int(m.group(2))
            return {"label": f"H{h} {y}", "end": f"{y}-{'06-30' if h == 1 else '12-31'}", "precision": "half"}
        if kind == "y":
            y = int(m.group(1))
            if y < 2000 or y > year_now + 15:
                continue
            return {"label": f"{y}", "end": f"{y}-12-31", "precision": "year"}
        if kind == "ty":
            return {"label": f"{year_now} ({m.group(1)})", "end": f"{year_now}-12-31", "precision": "year"}
        if kind == "ny":
            return {"label": f"{year_now + 1} (next year)", "end": f"{year_now + 1}-12-31", "precision": "year"}
    return None


def _hits(text: str, words) -> List[str]:
    s = text.lower()
    return sorted({w.strip() for w in words if w in s})


def _cid(*parts: Any) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


# --------------------------------------------------------------------------- release texts

def release_documents(ticker: str, root: Path = ROOT) -> List[Dict[str, Any]]:
    """Cached earnings-release exhibits in raw/filings/<accession>/ (git-ignored, local only)."""
    import sec_data  # local import: only needed when cached releases exist
    base = l4.company_dir(ticker, root)
    sub = l4.read_json(base / "raw/submissions.json", {}) or {}
    filed: Dict[str, str] = {}
    r = (sub.get("filings") or {}).get("recent") or {}
    for i, acc in enumerate(r.get("accessionNumber") or []):
        filed[acc] = r["filingDate"][i]
    cik = str(sub.get("cik") or "")
    docs = []
    for d in sorted((base / "raw/filings").glob("*")):
        for f in sorted(d.glob("*.htm")):
            if not re.search(r"ex-?99|ex991|exhibit991", f.name, re.I):
                continue
            try:
                text = sec_data.html_to_text(f.read_text(errors="ignore"))
            except Exception:
                continue
            url = (sec_data.filing_base_url(cik, d.name) + f.name) if cik else f"raw/filings/{d.name}/{f.name}"
            docs.append({"accession": d.name, "filed": filed.get(d.name, ""), "url": url, "text": text})
    return sorted(docs, key=lambda x: x["filed"])


def _sentences(text: str) -> List[str]:
    out = []
    lower = text.lower()
    cut = len(text)
    for marker in ("forward-looking statements", "use of non-gaap financial measures", "conference call information"):
        i = lower.find(marker, 1500)
        if i > 0:
            cut = min(cut, i)
    for line in text[:cut].split("\n"):
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z“\"(])", line.strip(" •\t")):
            if 30 <= len(s) <= 500:
                out.append(s.strip())
    return out


# --------------------------------------------------------------------------- claims

def guidance_claims(guidance: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for g in guidance:
        point = g.get("low") == g.get("high")
        out.append({
            "claim_id": _cid("g", g["issued"], g["period"], g["metric"]),
            "topic": METRIC_TOPIC.get(g["metric"], g["metric"]), "claim_type": "point_guidance" if point else "range_guidance",
            "period": g["period"], "metric": g["metric"], "lower": g.get("low"), "upper": g.get("high"),
            "unit": g.get("unit"), "timing": g["period"], "source_date": g["issued"], "source": g.get("source", ""),
            "statement": (g.get("statement") or "").strip(), "verbatim": True,
            "confidence": "high", "evidence_quality": "HIGH",
            "basis": "official quantified guidance (earnings release)",
        })
    return out


NOT_A_LAUNCH = re.compile(r"launch (complex|pad|site|services?|contracts?|agreements?|vehicles?|business|infrastructure)"
                         r"|launch,? test|electron launch contracts")


def milestone_class(low: str) -> Optional[str]:
    """Normalized milestone kind so that only like-for-like milestones are compared over time."""
    if re.search(r"first launch|debut launch|maiden|first flight|inaugural", low):
        return "first_launch"
    cleaned = NOT_A_LAUNCH.sub(" ", low)
    for kind, rx in (("launch", r"\blaunch"), ("arrival", r"arriv"), ("delivery", r"deliver|ship"),
                     ("commissioning", r"commission"), ("availability", r"availab"),
                     ("completion", r"complet|open"), ("closing", r"\bclose")):
        if re.search(rx, cleaned):
            return kind
    return None


def statement_claim(text: str, source_date: str, source: str, period: str, topic: str, verbatim: bool,
                    subjects: List[str]) -> Optional[Dict[str, Any]]:
    """Forward-looking statement → qualitative_guidance / timing_promise / operational_milestone."""
    if not FORWARD.search(text):
        return None
    timing = parse_timing(text, source_date)
    subject = next((s for s in subjects if re.search(rf"\b{re.escape(s)}\b", text, re.I)), None)
    low = text.lower()
    milestone = milestone_class(low)
    if subject and timing and milestone:
        ctype = "operational_milestone"
    elif timing and milestone:
        ctype = "timing_promise"
        subject = subject or "unspecified"
    else:
        direction = None
        if any(w in low for w in ("improve", "expand", "increase", "grow", "higher", "accelerat")):
            direction = "up"
        elif any(w in low for w in ("decline", "decrease", "lower", "compress", "pressure", "soft")):
            direction = "down"
        if not direction:
            return None
        ctype = "qualitative_guidance"
    metric = None
    for k, words in (("gross_margin", ("margin",)), ("revenue", ("revenue", "sales")), ("capex", ("capex", "capital expend")),
                     ("cash_flow", ("cash flow", "free cash")), ("backlog", ("backlog",))):
        if any(w in low for w in words):
            metric = k
            break
    return {
        "claim_id": _cid("s", source_date, text[:120]),
        "topic": topic, "claim_type": ctype, "period": period, "metric": metric,
        "lower": None, "upper": None, "unit": None,  # qualitative: never converted to numbers
        "timing": timing["label"] if timing else None, "timing_end": timing["end"] if timing else None,
        "timing_precision": timing["precision"] if timing else None,
        "subject": subject, "milestone": milestone,
        "direction": None if ctype != "qualitative_guidance" else
        ("up" if any(w in low for w in ("improve", "expand", "increase", "grow", "higher", "accelerat")) else "down"),
        "source_date": source_date, "source": source, "statement": text, "verbatim": verbatim,
        "confidence": "medium" if verbatim else "low",
        "evidence_quality": "MEDIUM", "basis": "earnings release statement (rule-based extraction)",
    }


def extract_claims(ticker: str, root: Path = ROOT, as_of: Optional[str] = None,
                   use_releases: bool = True) -> List[Dict[str, Any]]:
    base = l4.company_dir(ticker, root)
    as_of = l4.today(as_of)
    guidance = [g for g in (l4.read_json(base / "management/guidance.json", []) or []) if g.get("issued", "") <= as_of]
    statements = [s for s in (l4.read_json(base / "management/statements.json", []) or [])
                  if str(s.get("date", "")) <= as_of]
    ov = l4.read_yaml(base / "config/kpis.yaml", {}) or {}
    subjects = list(ov.get("milestone_subjects") or [])
    claims = guidance_claims(guidance)
    seen = set()
    for s in statements:
        c = statement_claim(s.get("statement", ""), str(s.get("date", "")), s.get("source", ""), s.get("period", ""),
                            s.get("topic", ""), bool(s.get("verbatim")), subjects)
        if c and c["claim_id"] not in seen:
            seen.add(c["claim_id"])
            claims.append(c)
    if use_releases and subjects:
        known = {c["statement"][:80] for c in claims}
        for doc in release_documents(ticker, root):
            if doc["filed"] and doc["filed"] > as_of:
                continue
            for sent in _sentences(doc["text"]):
                if sent[:80] in known or not any(re.search(rf"\b{re.escape(x)}\b", sent, re.I) for x in subjects):
                    continue
                c = statement_claim(sent, doc["filed"], doc["url"], "", "product_launch", True, subjects)
                if c and c["claim_type"] in ("operational_milestone", "timing_promise") and c["claim_id"] not in seen:
                    seen.add(c["claim_id"])
                    known.add(sent[:80])
                    claims.append(c)
    for c in claims:
        c["draft_auto"] = c["claim_type"] not in ("range_guidance", "point_guidance")
        c["review_required"] = c["confidence"] != "high"
    return sorted(claims, key=lambda c: (c["source_date"], c["claim_type"], c["claim_id"]))


# --------------------------------------------------------------------------- diff

def _finding(topic: str, dim: str, fact: List[str], change: str, interp: str, conf: str,
             sources: List[str], **extra: Any) -> Dict[str, Any]:
    out = {"topic": topic, "dimension": dim, "FACT": fact, "CHANGE": change, "INTERPRETATION": interp,
           "CONFIDENCE": conf, "sources": sorted(set(x for x in sources if x)),
           "draft_auto": True, "review_required": conf != "high"}
    out.update(extra)
    return out


def _fmt_range(lo: Any, hi: Any, unit: str) -> str:
    return f"{lo}" if lo == hi else f"{lo}–{hi}" + (f" {unit}" if unit else "")


def guidance_diff(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Same metric and target period re-guided → raised / lowered / narrowed / widened / maintained."""
    out = []
    by_key: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for c in claims:
        if c["claim_type"] in ("range_guidance", "point_guidance"):
            by_key.setdefault((c["metric"], c["period"]), []).append(c)
    for (metric, period), cs in sorted(by_key.items()):
        cs = sorted(cs, key=lambda c: c["source_date"])
        for a, b in zip(cs, cs[1:]):
            mid_a = (a["lower"] + a["upper"]) / 2
            mid_b = (b["lower"] + b["upper"]) / 2
            w_a, w_b = a["upper"] - a["lower"], b["upper"] - b["lower"]
            if abs(mid_b - mid_a) < 1e-9:
                kind = "narrowed" if w_b < w_a else "widened" if w_b > w_a else "maintained"
            else:
                kind = "raised" if mid_b > mid_a else "lowered"
            spending = metric in ("capex", "gaap_operating_expenses", "non_gaap_operating_expenses")
            if kind in ("raised", "lowered") and spending:
                interp = (f"支出計畫{'上調' if kind == 'raised' else '下調'}；這是投資節奏的改變，"
                          "本身不代表基本面變好或變差，需搭配營收與現金流判讀。")
            elif kind == "raised":
                interp = "管理層對該期間的量化預期提高（官方數字）；仍需等實際數字驗證。"
            elif kind == "lowered":
                interp = "管理層對該期間的量化預期下修（官方數字），屬需要重新評估的訊號；原因需看說明。"
            else:
                interp = "區間中點未變；僅不確定性範圍調整。"
            out.append(_finding(
                METRIC_TOPIC.get(metric, metric), "quantitative_guidance",
                [f"{a['source_date']}: {metric} {period} {_fmt_range(a['lower'], a['upper'], a['unit'])}",
                 f"{b['source_date']}: {metric} {period} {_fmt_range(b['lower'], b['upper'], b['unit'])}"],
                f"{kind}（中點 {mid_a:g} → {mid_b:g}）", interp, "high", [a["source"], b["source"]],
                metric=metric, period=period, kind=kind, as_of=b["source_date"]))
    return out


def timing_diff(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Same subject's milestone target moved: slipped (later) / pulled_in (earlier)."""
    out = []
    by_subj: Dict[str, List[Dict[str, Any]]] = {}
    for c in claims:
        if c["claim_type"] in ("operational_milestone", "timing_promise") and c.get("timing_end") \
                and c.get("subject") not in (None, "unspecified"):
            by_subj.setdefault(c["subject"], []).append(c)
    for subj, cs in sorted(by_subj.items()):
        cs = sorted(cs, key=lambda c: (c["source_date"], c["timing_end"]))
        # one representative per source date: the launch-like milestone if present
        per_date: Dict[str, Dict[str, Any]] = {}
        for c in cs:
            cur = per_date.get(c["source_date"])
            if cur is None or (c.get("milestone") == "first_launch" and cur.get("milestone") != "first_launch"):
                per_date[c["source_date"]] = c
        seq = [per_date[d] for d in sorted(per_date)]
        # compare like-for-like milestones only (first launch vs first launch, ...)
        kinds = {c.get("milestone") for c in seq}
        if "first_launch" in kinds:
            seq = [c for c in seq if c.get("milestone") == "first_launch"]
        for a, b in zip(seq, seq[1:]):
            if a["timing_end"] == b["timing_end"]:
                continue
            later = b["timing_end"] > a["timing_end"]
            same_milestone = (a.get("milestone") == b.get("milestone"))
            conf = "medium" if same_milestone else "low"
            interp = (f"{subj} 時程{'延後' if later else '提前'}（{a['timing']} → {b['timing']}）。"
                      + ("時程延後是可驗證的承諾變化；是否影響論點取決於該里程碑對營收 / 成本的重要性。" if later
                         else "時程提前，仍需實際完成才算兌現。")
                      + ("" if same_milestone else "兩句話描述的里程碑不同（"
                         f"{a.get('milestone')} vs {b.get('milestone')}），比較只供參考。"))
            out.append(_finding("product_launch", "timing",
                                [f"{a['source_date']}: “{a['statement'][:220]}”", f"{b['source_date']}: “{b['statement'][:220]}”"],
                                f"{'slipped' if later else 'pulled_in'}: {a['timing']} → {b['timing']}", interp, conf,
                                [a["source"], b["source"]], subject=subj, kind="slipped" if later else "pulled_in",
                                from_claim=a["claim_id"], to_claim=b["claim_id"], as_of=b["source_date"]))
    return out


def wording_diff(statements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Latest vs previous period per topic on wording dimensions. Wording ≠ fundamentals."""
    out = []
    periods = sorted({(str(s.get("date", "")), s.get("period", "")) for s in statements if s.get("period")})
    if len(periods) < 2:
        return out
    (d0, p0), (d1, p1) = periods[-2], periods[-1]
    prev = [s for s in statements if s.get("period") == p0]
    cur = [s for s in statements if s.get("period") == p1]
    dims = (("bottleneck", BOTTLENECK, None), ("customer_demand", DEMAND, None), ("capex_stance", CAPEX_UP, CAPEX_DOWN),
            ("margin_stance", MARGIN_UP, MARGIN_DOWN), ("product_launch", PROGRESS, None),
            ("confidence_shift", COMMITTED, HEDGED))
    for dim, up, down in dims:
        a_txt = " ".join(s.get("statement", "") for s in prev)
        b_txt = " ".join(s.get("statement", "") for s in cur)
        a_up, b_up = _hits(a_txt, up), _hits(b_txt, up)
        a_dn, b_dn = (_hits(a_txt, down), _hits(b_txt, down)) if down else ([], [])
        new_up, gone_up = sorted(set(b_up) - set(a_up)), sorted(set(a_up) - set(b_up))
        new_dn, gone_dn = sorted(set(b_dn) - set(a_dn)), sorted(set(a_dn) - set(b_dn))
        if not (new_up or gone_up or new_dn or gone_dn):
            continue
        ex = next((s for s in cur if _hits(s.get("statement", ""), (new_up or new_dn or up))), cur[0] if cur else {})
        change = "; ".join(x for x in (
            f"新出現：{', '.join(new_up)}" if new_up else "", f"消失：{', '.join(gone_up)}" if gone_up else "",
            f"新出現（反向詞）：{', '.join(new_dn)}" if new_dn else "", f"消失（反向詞）：{', '.join(gone_dn)}" if gone_dn else "")
            if x)
        interp = {
            "bottleneck": "限制 / 延遲相關用語的出現或消失；需對照具體里程碑或數字，用語本身不代表營運惡化或改善。",
            "customer_demand": "需求相關用語變化；以 RPO、backlog、營收等數字為準。",
            "capex_stance": "投資立場用語變化；以 capex guidance 與實際現金流量為準。",
            "margin_stance": "毛利率立場用語變化；以 guidance 與實際毛利率為準。",
            "product_launch": "產品 / 里程碑進度用語；已完成的事項需有日期與來源。",
            "confidence_shift": "僅為措辭差異（承諾性 vs 保留性用語），不足以推論基本面變化。",
        }[dim]
        out.append(_finding(dim if dim != "confidence_shift" else "tone", dim,
                            [f"{p0}（{d0}）關鍵詞：{', '.join(a_up + a_dn) or '無'}",
                             f"{p1}（{d1}）關鍵詞：{', '.join(b_up + b_dn) or '無'}",
                             f"例句（{p1}）：“{(ex.get('statement') or '')[:200]}”"],
                            change, interp, "low", [ex.get("source", "")], period_from=p0, period_to=p1,
                            as_of=d1))
    return out


def qualitative_findings(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for c in claims:
        if c["claim_type"] != "qualitative_guidance":
            continue
        out.append(_finding(c["topic"] or "guidance", "qualitative_guidance",
                            [f"{c['source_date']}: “{c['statement'][:220]}”"],
                            f"質化方向：{c['direction']}" + (f"，時點 {c['timing']}" if c.get("timing") else "，未給時點"),
                            "質化 guidance，不轉成數字；只能在之後以實際數字檢查方向是否成立。",
                            "low" if not c["verbatim"] else "medium", [c["source"]], claim_id=c["claim_id"],
                            as_of=c["source_date"]))
    return out[-10:]


BANNED = ("fundamentals deteriorated", "tone slightly cautious", "基本面惡化")


def run(ticker: str, root: Path = ROOT, as_of: Optional[str] = None, write: bool = True,
        use_releases: bool = True) -> Dict[str, Any]:
    t = ticker.upper()
    base = l4.company_dir(t, root)
    as_of = l4.today(as_of)
    claims = extract_claims(t, root, as_of, use_releases)
    statements = [s for s in (l4.read_json(base / "management/statements.json", []) or []) if str(s.get("date", "")) <= as_of]
    findings = guidance_diff(claims) + timing_diff(claims) + wording_diff(statements) + qualitative_findings(claims)
    for f in findings:
        txt = " ".join([f["CHANGE"], f["INTERPRETATION"]]).lower()
        assert not any(b in txt for b in BANNED), f"banned inference in {f}"
    counts: Dict[str, int] = {}
    for c in claims:
        counts[c["claim_type"]] = counts.get(c["claim_type"], 0) + 1
    out = {"ticker": t, "as_of": as_of, "claim_counts": counts, "findings": findings,
           "method": "rule-based structured comparison (no LLM); wording-only findings are low confidence",
           "draft_auto": True, "review_required": True}
    if write:
        l4.write_json(base / "management/claims.json", claims)
        l4.write_json(base / "management/semantic-diff.json", out)
        (base / "management/semantic-diff.md").write_text(render(t, out), encoding="utf-8")
    out["claims"] = claims
    return out


def render(ticker: str, out: Dict[str, Any]) -> str:
    L = [f"# {ticker} 管理層語意比較（semantic diff，{out['as_of']}）", "",
         "> draft_auto：規則式比較，非分析師定稿。FACT = 原文或標明的 paraphrase；CHANGE = 與前期差異；"
         "INTERPRETATION 不得強於證據；只有措辭變化時信心為 low，且不推論基本面變化。", "",
         "Claims：" + (", ".join(f"{k} {v}" for k, v in sorted(out["claim_counts"].items())) or "無"), ""]
    if not out["findings"]:
        L.append("沒有可比較的跨期變化。")
    order = {"quantitative_guidance": 0, "timing": 1, "qualitative_guidance": 3}
    for f in sorted(out["findings"], key=lambda f: (order.get(f["dimension"], 2), f.get("as_of", "")), reverse=False)[-40:]:
        L += [f"## {f['topic']} · {f['dimension']}（{f.get('as_of', '')}）", ""]
        L += [f"- FACT: {x}" for x in f["FACT"]]
        L += [f"- CHANGE: {f['CHANGE']}", f"- INTERPRETATION: {f['INTERPRETATION']}",
              f"- CONFIDENCE: {f['CONFIDENCE']}" + ("（review_required）" if f["review_required"] else ""), ""]
    return "\n".join(L)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--as-of")
    ap.add_argument("--no-releases", action="store_true", help="only statements.json / guidance.json")
    args = ap.parse_args(argv)
    out = run(args.ticker, as_of=args.as_of, use_releases=not args.no_releases)
    dims: Dict[str, int] = {}
    for f in out["findings"]:
        dims[f["dimension"]] = dims.get(f["dimension"], 0) + 1
    print(f"{out['ticker']}: claims {out['claim_counts']}; findings {dims}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
