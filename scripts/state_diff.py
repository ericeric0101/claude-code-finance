#!/usr/bin/env python3
"""Full research-state snapshots and the multi-domain "What Changed Since Last Review" diff.

A snapshot (research/<TICKER>/snapshots/<as_of>.json) freezes, at one date:
financials (latest reported quarter + TTM), management (guidance, statements,
promises), thesis (status + evidence fingerprint), valuation (price, scenarios,
map position, historical percentiles), expectation gap, monitoring-rule states,
action / confidence and next catalysts.

`diff_states(prev, cur)` compares two snapshots domain by domain:
  A financials  B management  C thesis  D valuation  E expectation gap  F monitoring
and classifies each change as positive / negative / neutral. Price movement on
its own is reported as a valuation change and never as a fundamental change.

`retrospective=True` marks a snapshot rebuilt later from data that was public
at its as_of date (no look-ahead); it carries no recommendation unless one was
actually recorded then.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import research_state as rs  # noqa: E402

FIN_KEYS = ("revenue", "revenue_yoy_pct", "gross_margin_pct", "operating_margin_pct", "fcf", "sbc",
            "diluted_shares", "debt", "cash_and_investments", "rpo", "rpo_yoy_pct", "backlog")
TTM_KEYS = ("revenue", "fcf", "sbc", "operating_income")
# direction of "good" for financial deltas; None = report only
FIN_GOOD = {"revenue": 1, "revenue_yoy_pct": 1, "gross_margin_pct": 1, "operating_margin_pct": 1, "fcf": 1,
            "fcf_ttm": 1, "operating_income_ttm": 1, "revenue_ttm": 1, "rpo": 1, "rpo_yoy_pct": 1, "backlog": 1,
            "cash_and_investments": None, "debt": -1, "sbc": None, "sbc_ttm": None, "diluted_shares": -1,
            "normalized_fcf": 1}
MATERIAL = {"revenue_yoy_pct": 2.0, "gross_margin_pct": 1.0, "operating_margin_pct": 2.0, "rpo_yoy_pct": 5.0}


def _hv(m: Dict[str, Any], k: str) -> Optional[float]:
    x = (m or {}).get(k)
    return x.get("value") if isinstance(x, dict) else x


def _fingerprint(items: List[Any]) -> str:
    return hashlib.sha1(json.dumps(items, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]


def financial_section(history: Optional[Dict[str, Any]], latest_fin: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"latest_quarter": None, "quarter": {}, "ttm": {}, "other": {}}
    if history:
        qs = [q for q in history.get("quarters", []) if _hv(q["metrics"], "revenue") is not None]
        if qs:
            last = qs[-1]
            out["latest_quarter"] = last["period"]
            out["latest_quarter_end"] = last["period_end"]
            out["quarter"] = {k: _hv(last["metrics"], k) for k in FIN_KEYS}
            for k in TTM_KEYS:
                vals = [_hv(q["metrics"], k) for q in qs[-4:]]
                out["ttm"][f"{k}_ttm"] = round(sum(vals), 4) if len(vals) == 4 and None not in vals else None
            filed = [p.get("filed") for p in last["metrics"].values() if isinstance(p, dict) and p.get("filed")]
            out["latest_filed"] = max(filed) if filed else None
    m = (latest_fin or {}).get("metrics", {})
    for key, alias in (("fcf_ex_deferred_revenue", "normalized_fcf"), ("backlog", "backlog")):
        if _hv(m, key) is not None:
            out["other"][alias] = {"value": _hv(m, key), "period": (m.get(key) or {}).get("period")}
    if not out["latest_quarter"]:
        out["latest_quarter"] = (latest_fin or {}).get("latest_reported_period")
    return out


def management_section(base: Path, as_of: str) -> Dict[str, Any]:
    statements = [s for s in rs._read_json(base / "management/statements.json", []) or []
                  if str(s.get("date", "")) <= as_of]
    guidance = [g for g in rs._read_json(base / "management/guidance.json", []) or [] if g["issued"] <= as_of]
    latest: Dict[str, Dict[str, Any]] = {}
    for g in sorted(guidance, key=lambda g: g["issued"]):
        latest[f"{g['period']}|{g['metric']}"] = {"low": g["low"], "high": g["high"], "issued": g["issued"],
                                                  "unit": g["unit"]}
    promises = {}
    for p in rs._read_json(base / "management/promises.json", []) or []:
        if str(p.get("statement_date", "")) > as_of:
            continue
        st = p.get("status", "pending")
        if p.get("resolved_date") and str(p["resolved_date"]) > as_of and st not in ("pending", "superseded"):
            st = "pending"  # outcome not yet public at as_of
        promises[p["promise_id"]] = {"status": st, "claim": str(p.get("management_claim", ""))[:160],
                                     "actual": p.get("actual_result") if st != "pending" else None,
                                     "rule": p.get("resolution_rule") if st != "pending" else None}
    periods = sorted({s.get("period") for s in statements if s.get("period")})
    latest_period = max(statements, key=lambda s: s.get("date", ""))["period"] if statements else None
    tone = {}
    for s in statements:
        if s.get("period") == latest_period and "tone" in s:
            tone.setdefault(s["topic"], []).append(s["tone"])
    return {"statement_count": len(statements), "periods": periods, "latest_period": latest_period,
            "latest_tone_by_topic": {k: round(sum(v) / len(v), 2) for k, v in tone.items()},
            "guidance": latest, "promises": promises}


def build_snapshot(ticker: str, root: Path = rs.ROOT, as_of: Optional[str] = None,
                   retrospective: bool = False, history: Optional[Dict[str, Any]] = None,
                   price: Optional[Tuple[str, float]] = None, note: str = "") -> Dict[str, Any]:
    """Assemble the current state of every domain. For a retrospective snapshot pass
    `history` built with the same as_of cutoff and the then-latest close as `price`."""
    base = rs.company_dir(ticker, root)
    thesis = rs._read_yaml(base / "thesis/current.yaml") or {}
    latest = rs._read_json(base / "valuation/latest.json", {}) or {}
    as_of = as_of or str(thesis.get("as_of") or latest.get("as_of"))
    if history is None:
        history = rs._read_json(base / "financials/history.json")
    fin = financial_section(history, rs._read_json(base / "financials/latest.json", {}) or {})
    pct = rs._read_json(base / "valuation/historical-percentiles.json") or {}
    snap: Dict[str, Any] = {
        "ticker": ticker.upper(), "as_of": as_of, "retrospective": retrospective,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "note": note,
        "financials": fin, "management": management_section(base, as_of),
    }
    if retrospective:
        snap.update({"action": None, "valuation_confidence": None, "thesis": {}, "next_catalysts": [],
                     "rules": {}, "expectation_gap": {},
                     "valuation": {"price": price[1] if price else None, "price_date": price[0] if price else None,
                                   "methods": {}, "map_position": None, "percentiles": {}},
                     "recommendation_note": "retrospective = true: no recommendation existed at this date; "
                                            "only public data as of the date is recorded."})
        return snap
    comps = thesis.get("components") or {}
    snap["action"] = thesis.get("action")
    snap["valuation_confidence"] = thesis.get("valuation_confidence") or latest.get("valuation_confidence")
    snap["thesis"] = {k: {"status": c.get("status"), "importance": c.get("importance"),
                          "evidence_count": len(c.get("evidence") or []),
                          "evidence_fp": _fingerprint(c.get("evidence") or [])} for k, c in comps.items()}
    snap["next_catalysts"] = list(thesis.get("next_catalysts") or [])
    close = rs.latest_close(base)
    snap["valuation"] = {
        "price": latest.get("price"), "price_date": latest.get("price_date"),
        "latest_close": close["close"] if close else None, "latest_close_date": close["date"] if close else None,
        "methods": latest.get("methods") or {},
        "map_position": (latest.get("valuation_map") or {}).get("current_position"),
        "reverse_dcf_implied_growth": (latest.get("reverse_dcf") or {}).get("implied_growth"),
        "percentiles": {k: {w: v.get(w) for w in ("current", "1y", "3y", "since_listing")}
                        for k, v in (pct.get("percentiles") or {}).items()},
    }
    exp = latest.get("expectations") or {}
    snap["expectation_gap"] = (rs.expectation_gap(exp["market_implied"], exp.get("internal_base", {}),
                                                  exp.get("bull", {})) if exp.get("market_implied") else {})
    snap["rules"] = {r["rule"]: {"state": r["state"], "type": r["type"],
                                 "value": r.get("value") if r["type"] != "invalidation" else r.get("values")}
                     for r in rs.check_rules(ticker, root)}
    return snap


def save_snapshot(ticker: str, snap: Dict[str, Any], root: Path = rs.ROOT, overwrite: bool = False) -> Path:
    d = rs.company_dir(ticker, root) / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{snap['as_of']}.json"
    if path.exists() and not overwrite:
        old = json.loads(path.read_text())
        if old.get("retrospective") is False and snap.get("retrospective"):
            raise ValueError(f"{path.name}: refusing to replace a real snapshot with a retrospective one")
    path.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def list_snapshots(ticker: str, root: Path = rs.ROOT) -> List[Dict[str, Any]]:
    d = rs.company_dir(ticker, root) / "snapshots"
    return [json.loads(p.read_text()) for p in sorted(d.glob("*.json"))] if d.exists() else []


# --------------------------------------------------------------------------- diff

def _fmt(v: Any) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


def _delta_item(name: str, a: Optional[float], b: Optional[float], good: Optional[int],
                material: float = 0.0) -> Tuple[str, str]:
    """(classification, text). Relative change for levels, point change for _pct metrics."""
    if a is None and b is None:
        return "missing", f"{name}: 無資料"
    if a is None:
        return "new", f"{name}: 新增 {_fmt(b)}"
    if b is None:
        return "missing", f"{name}: {_fmt(a)} → 無資料"
    if abs(b - a) < 1e-9:
        return "unchanged", f"{name}: {_fmt(b)}（未變）"
    if name.endswith("_pct"):
        change = f"{b - a:+.2f} pp"
        mag = abs(b - a)
    elif a > 0:
        change = f"{(b / a - 1) * 100:+.1f}%"
        mag = abs(b / a - 1) * 100
    else:  # relative change is meaningless from a negative or zero base
        change = f"Δ {b - a:+,.2f}"
        mag = 100.0
    text = f"{name}: {_fmt(a)} → {_fmt(b)}（{change}）"
    if good is None or mag < max(material, 0.5):
        return "neutral", text
    return ("positive" if (b - a) * good > 0 else "negative"), text


def diff_states(prev: Optional[Dict[str, Any]], cur: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"prev_as_of": (prev or {}).get("as_of"), "cur_as_of": cur.get("as_of"),
                           "prev_retrospective": (prev or {}).get("retrospective"),
                           "positive": [], "negative": [], "unchanged": [],
                           "financials": [], "management": [], "promises": [], "thesis": [], "valuation": [],
                           "expectation_gap": [], "monitoring": []}
    if prev is None:
        out["baseline"] = True
        return out

    def add(domain: str, kind: str, text: str) -> None:
        out[domain].append(f"[{kind}] {text}")
        if kind in ("positive", "negative"):
            out[kind].append(f"{domain}: {text}")
        elif kind in ("unchanged",):
            out["unchanged"].append(f"{domain}: {text}")

    # A. Financials
    pf, cf = prev.get("financials") or {}, cur.get("financials") or {}
    new_period = pf.get("latest_quarter") != cf.get("latest_quarter")
    add("financials", "neutral" if new_period else "unchanged",
        f"latest reported quarter: {pf.get('latest_quarter')} → {cf.get('latest_quarter')}"
        if new_period else f"latest reported quarter: {cf.get('latest_quarter')}（無新財報）")
    for k in FIN_KEYS:
        kind, text = _delta_item(k, (pf.get("quarter") or {}).get(k), (cf.get("quarter") or {}).get(k),
                                 FIN_GOOD.get(k), MATERIAL.get(k, 0.0))
        if kind != "missing" or new_period:
            add("financials", kind, text)
    for k in ("revenue_ttm", "fcf_ttm", "operating_income_ttm", "sbc_ttm"):
        kind, text = _delta_item(k, (pf.get("ttm") or {}).get(k), (cf.get("ttm") or {}).get(k), FIN_GOOD.get(k))
        if kind != "missing":
            add("financials", kind, text)
    for k in ("normalized_fcf", "backlog"):
        a, b = ((pf.get("other") or {}).get(k) or {}), ((cf.get("other") or {}).get(k) or {})
        if a or b:
            kind, text = _delta_item(k, a.get("value"), b.get("value"), FIN_GOOD.get(k))
            add("financials", kind, text + (f" [{b.get('period')}]" if b.get("period") else ""))

    # B. Management
    pm, cm = prev.get("management") or {}, cur.get("management") or {}
    added = cm.get("statement_count", 0) - pm.get("statement_count", 0)
    if cm.get("latest_period") != pm.get("latest_period"):
        add("management", "neutral", f"新一季管理層陳述：{pm.get('latest_period')} → {cm.get('latest_period')}"
                                      f"（+{added} 則）")
    else:
        add("management", "unchanged", f"無新管理層陳述（最新 {cm.get('latest_period')}）")
    for topic, t in sorted((cm.get("latest_tone_by_topic") or {}).items()):
        pt = (pm.get("latest_tone_by_topic") or {}).get(topic)
        if pt is not None and cm.get("latest_period") != pm.get("latest_period") and abs(t - pt) >= 0.5:
            add("management", "neutral", f"措辭（{topic}）：{'更有信心' if t > pt else '更謹慎'}"
                                          f"（語氣分數 {pt} → {t}；僅措辭，不代表基本面）")
    pg, cg = pm.get("guidance") or {}, cm.get("guidance") or {}
    for key, g in sorted(cg.items()):
        old = pg.get(key)
        period, metric = key.split("|")
        if old is None:
            add("management", "neutral", f"新 guidance {period} {metric}: {g['low']}–{g['high']} {g['unit']}（{g['issued']}）")
        elif (old["low"], old["high"]) != (g["low"], g["high"]):
            mid_o, mid_n = (old["low"] + old["high"]) / 2, (g["low"] + g["high"]) / 2
            kind = "neutral" if metric == "capex" else ("positive" if mid_n > mid_o else "negative")
            verb = "raised" if mid_n > mid_o else "lowered"
            add("management", kind, f"guidance {verb} {period} {metric}: {old['low']}–{old['high']} → "
                                    f"{g['low']}–{g['high']} {g['unit']}")
    pp, cp = pm.get("promises") or {}, cm.get("promises") or {}
    for pid, p in sorted(cp.items()):
        old = pp.get(pid)
        if old is None:
            add("promises", "neutral", f"新承諾 {pid}（{p['status']}）")
        elif old["status"] != p["status"]:
            kind = {"delivered": "positive", "missed": "negative", "partially_delivered": "negative"}.get(p["status"], "neutral")
            add("promises", kind, f"{pid}: {old['status']} → {p['status']}" +
                (f"（actual {p['actual']}" + (f"；{p['rule']}" if p.get("rule") else "") + "）"
                 if p.get("actual") is not None else ""))
    counts: Dict[str, int] = {}
    for p in cp.values():
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    out["promise_counts"] = counts

    # C. Thesis
    pt_, ct = prev.get("thesis") or {}, cur.get("thesis") or {}
    if not pt_ and ct:
        add("thesis", "neutral", "前一狀態無 thesis（retrospective 或尚未建立）；本次為第一個 thesis 狀態")
    for name, c in ct.items():
        p = pt_.get(name)
        if not p:
            continue
        kind = rs.classify_transition(p["status"], c["status"])
        if kind == "unchanged":
            add("thesis", "unchanged", f"{name}: {c['status']}")
        else:
            note = rs.TRANSITION_NOTES.get((p["status"], c["status"]), "")
            add("thesis", kind, f"{name}: {p['status']} → {c['status']}" + (f"（{note}）" if note else ""))
        if p.get("evidence_fp") != c.get("evidence_fp"):
            add("thesis", "neutral", f"{name}: 證據更新（{p.get('evidence_count')} → {c.get('evidence_count')} 則）")

    # D. Valuation
    pv, cv = prev.get("valuation") or {}, cur.get("valuation") or {}
    pa = pv.get("latest_close") or pv.get("price")
    ca = cv.get("latest_close") or cv.get("price")
    if pa and ca:
        add("valuation", "neutral" if abs(ca / pa - 1) > 1e-9 else "unchanged",
            f"price: {pa} ({pv.get('latest_close_date') or pv.get('price_date')}) → {ca} "
            f"({cv.get('latest_close_date') or cv.get('price_date')})（{(ca / pa - 1) * 100:+.1f}%；股價變動不是基本面證據）")
    for m, vals in (cv.get("methods") or {}).items():
        old = (pv.get("methods") or {}).get(m)
        cur_s = f"{vals.get('bear')}/{vals.get('base')}/{vals.get('bull')}"
        if old is None:
            add("valuation", "neutral", f"{m}: {cur_s}（新增）")
        else:
            old_s = f"{old.get('bear')}/{old.get('base')}/{old.get('bull')}"
            add("valuation", "unchanged" if old_s == cur_s else "neutral",
                f"{m}: {old_s} → {cur_s}" if old_s != cur_s else f"{m}: {cur_s}（未變）")
    if pv.get("map_position") != cv.get("map_position"):
        add("valuation", "neutral", f"valuation zone: {pv.get('map_position')} → {cv.get('map_position')}")
    else:
        add("valuation", "unchanged", f"valuation zone: {cv.get('map_position')}")
    for mult, p in (cv.get("percentiles") or {}).items():
        o = (pv.get("percentiles") or {}).get(mult) or {}
        if not o:
            add("valuation", "neutral", f"{mult} historical percentile 首次建立：3Y {p.get('3y')}; since listing "
                                        f"{p.get('since_listing')}（current {p.get('current')}）")
            continue
        add("valuation", "neutral" if o != p else "unchanged",
            f"{mult} historical percentile 3Y: {o.get('3y')} → {p.get('3y')}; since listing: "
            f"{o.get('since_listing')} → {p.get('since_listing')}（current {p.get('current')}）")
    if prev.get("valuation_confidence") != cur.get("valuation_confidence"):
        add("valuation", "neutral", f"valuation confidence: {prev.get('valuation_confidence')} → {cur.get('valuation_confidence')}")

    # E. Expectation gap
    pe_, ce = prev.get("expectation_gap") or {}, cur.get("expectation_gap") or {}
    for k, g in ce.items():
        o = pe_.get(k)
        if not o:
            add("expectation_gap", "neutral", f"{k}: 首次量化 market {g['market_implied']} vs base {g['internal_base']} / "
                                              f"bull {g['bull']}（gap vs base {g['gap_vs_base']:+.3f}）")
            continue
        d = abs(g["gap_vs_base"]) - abs(o["gap_vs_base"])
        direction = "stable" if abs(d) <= 0.005 else ("widening" if d > 0 else "narrowing")
        add("expectation_gap", "unchanged" if direction == "stable" else "neutral",
            f"{k}: gap vs base {o['gap_vs_base']:+.3f} → {g['gap_vs_base']:+.3f}（{direction}）")
    if not ce:
        add("expectation_gap", "unchanged", "未量化")

    # F. Monitoring
    pr, cr = prev.get("rules") or {}, cur.get("rules") or {}
    for rule, r in sorted(cr.items()):
        o = (pr.get(rule) or {}).get("state")
        st = r["state"]
        if st == "triggered" and o != "triggered":
            add("monitoring", "negative" if r["type"] != "market" else "neutral",
                f"newly triggered → REASSESS: {rule}（{r['type']}；之前 {o or '無規則狀態（retrospective 或新規則）'}；"
                f"value {_fmt(r.get('value'))}）")
        elif st == "triggered":
            add("monitoring", "unchanged", f"still triggered: {rule}（{r['type']}）")
        elif o == "triggered":
            add("monitoring", "positive" if r["type"] != "market" else "neutral", f"resolved: {rule}（{r['type']}）")
        elif st == "missing_data":
            add("monitoring", "unchanged", f"missing data: {rule}")
    out["action"] = (prev.get("action"), cur.get("action"))
    out["confidence"] = (prev.get("valuation_confidence"), cur.get("valuation_confidence"))
    return out


def render_report(ticker: str, d: Dict[str, Any], cur: Dict[str, Any], note: str = "") -> str:
    t = ticker.upper()
    lines = [f"# What Changed Since Last Review — {t}｜自上次檢視以來的變化", ""]
    if note:
        lines += [f"> {note}", ""]
    if d.get("baseline"):
        lines += [f"基準狀態日期為 {cur.get('as_of')}；沒有先前的研究狀態可供比較。",
                  "以下各項皆為下次更新的比較起點。", ""]
    else:
        retro = "（前一狀態為 retrospective，僅含當時公開資料、無當時建議）" if d.get("prev_retrospective") else ""
        lines += [f"比較：{d['prev_as_of']} → {d['cur_as_of']}{retro}", ""]

    def section(title: str, items: List[str]) -> None:
        lines.extend([f"## {title}"] + ([f"- {i}" for i in items] or ["- 無"]) + [""])

    section("Positive 正面變化", d["positive"])
    section("Negative 負面變化", d["negative"])
    section("Unchanged 未變化", d["unchanged"][:25])
    section("Financial changes 財務變化", d["financials"])
    section("Management wording 管理層措辭與 guidance", d["management"])
    counts = d.get("promise_counts") or {}
    section("Promise tracker 承諾追蹤", d["promises"] + ([
        "目前計數：" + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
        + "（僅計數，非管理層可信度分數）"] if counts else []))
    section("Thesis changes 論點變化", d["thesis"])
    section("Valuation changes 估值變化", d["valuation"])
    section("Expectation gap 預期落差", d["expectation_gap"])
    section("Monitoring triggers 監控規則（觸發 = REASSESS，非買賣訊號）", d["monitoring"])
    a, c = d.get("action") or (cur.get("action"), cur.get("action")), d.get("confidence") or (
        cur.get("valuation_confidence"), cur.get("valuation_confidence"))
    lines += ["## Action 研究分類", f"- {a[0]} → {a[1]}" if a[0] != a[1] else f"- {a[1]}（未變）", "",
              "## Confidence 估值信心", f"- {c[0]} → {c[1]}" if c[0] != c[1] else f"- {c[1]}（未變）", "",
              "## Next catalysts 下一個催化劑"]
    lines += [f"- {x}" for x in cur.get("next_catalysts") or []] or ["- 尚無紀錄"]
    lines += ["", "僅有股價變動不視為基本面已改變的證據。"]
    return "\n".join(lines) + "\n"
