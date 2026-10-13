#!/usr/bin/env python3
"""Monthly Research OS quality summary (process quality, not return prediction).

Reads research/quality/quality-events.jsonl and corrections.jsonl only — never prices or
returns — and writes research/quality/summaries/YYYY-MM-quality-summary.md (+ .json).

Metrics are simple counts and ratios with their numerator / denominator shown. A ratio
whose denominator is below MIN_SAMPLE (5) is reported as insufficient_sample instead of a
percentage. Only reviewed judgments count; "unknown" and "not_applicable" are excluded.

  Event precision      correct detected material events / detected events reviewed
  Event recall         detected material events / (detected material + missed material events)
  Priority agreement   reviewed priorities matching the system / reviewed priorities
  Guidance accuracy    correct guidance items / reviewed guidance items (event-level when
                       item counts are not given)
  Module agreement     correct module judgments / reviewed module judgments (see quality_log.BOOL_FIELDS)

Usage:
  python3 scripts/quality_summary.py --month 2026-10 [--print]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import quality_log as ql  # noqa: E402

MIN_SAMPLE = 5
INSUFFICIENT = "insufficient_sample"


def ratio(num: int, den: int) -> Dict[str, Any]:
    return {"numerator": num, "denominator": den,
            "value": round(num / den, 3) if den >= MIN_SAMPLE else INSUFFICIENT}


def fmt_ratio(r: Dict[str, Any]) -> str:
    if r["value"] == INSUFFICIENT:
        return f"{INSUFFICIENT}（{r['numerator']}/{r['denominator']}，n < {MIN_SAMPLE}）"
    return f"{r['value'] * 100:.0f}%（{r['numerator']}/{r['denominator']}）"


def _in_month(d: str, month: Optional[str]) -> bool:
    return month is None or str(d or "")[:7] == month


def _bool(e: Dict[str, Any], f: str) -> Any:
    return e["human_review"].get(f, ql.UNKNOWN)


def module_stats(events: List[Dict[str, Any]], corrections: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Per-module reviewed judgments: correct vs error, plus extraction errors and corrections."""
    st: Dict[str, Dict[str, Any]] = {m: {"correct": 0, "errors": 0, "extraction_errors": 0, "corrections": 0}
                                     for m in ql.MODULES}
    for e in events:
        hr = e["human_review"]
        for f, m in ql.BOOL_FIELDS.items():
            if not m or f == "false_negative":
                continue
            v = hr.get(f)
            if v not in (True, False):
                continue
            good = (v is False) if f in ql.ERROR_WHEN_TRUE else (v is True)
            if f == "false_positive" and hr.get("event_detected_correctly") in (True, False):
                continue  # already graded by event_detected_correctly; don't double count
            if f == "event_detected_correctly" and hr.get("false_negative") is True:
                continue  # a missed event is counted once, as a false negative
            st[m]["correct" if good else "errors"] += 1
        if hr.get("false_negative") is True:
            st["event_detector"]["errors"] += 1
        iv = hr.get("interpretation_verdict")
        im = hr.get("interpretation_module") or "management_diff"
        if iv in ("correct", "reasonable_but_uncertain"):
            st[im]["correct"] += 1
        elif iv in ("overinterpreted", "underinterpreted", "unsupported"):
            st[im]["errors"] += 1
        for x in hr.get("extraction_errors") or []:
            st[x["module"]]["extraction_errors"] += 1
    for c in corrections:
        if c.get("module") in st:
            st[c["module"]]["corrections"] += 1
    for m, s in st.items():
        s["reviewed"] = s["correct"] + s["errors"] + s["extraction_errors"]
        s["agreement"] = ratio(s["correct"], s["reviewed"])
    return st


def ticker_stats(events: List[Dict[str, Any]], corrections: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    st: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"events": 0, "reviewed": 0, "pending": 0, "false_positives": 0,
                                                        "false_negatives": 0, "errors": 0, "corrections": 0, "events_with_issues": 0,
                                                        "extraction_errors": Counter(), "error_modules": Counter(),
                                                        "low_confidence_interpretation": 0})
    for e in events:
        s = st[e["ticker"]]
        s["events"] += 1
        if e["review_status"] == "reviewed":
            s["reviewed"] += 1
        elif e["review_status"] == "pending":
            s["pending"] += 1
        hr = e["human_review"]
        s["false_positives"] += hr.get("false_positive") is True
        s["false_negatives"] += hr.get("false_negative") is True
        before = s["errors"]
        for f, m in ql.BOOL_FIELDS.items():
            v = hr.get(f)
            if f == "event_detected_correctly" and hr.get("false_negative") is True:
                continue
            if m and v in (True, False) and ((v is True) if f in ql.ERROR_WHEN_TRUE else (v is False)):
                s["errors"] += 1
                s["error_modules"][m] += 1
        for x in hr.get("extraction_errors") or []:
            s["extraction_errors"][x["module"]] += 1
            s["error_modules"][x["module"]] += 1
        if hr.get("interpretation_verdict") in ("overinterpreted", "underinterpreted", "unsupported"):
            s["low_confidence_interpretation"] += 1
            s["error_modules"][hr.get("interpretation_module") or "management_diff"] += 1
            s["errors"] += 1
        s["errors"] += len(hr.get("extraction_errors") or [])
        s["events_with_issues"] += s["errors"] > before
    for c in corrections:
        st[c["ticker"]]["corrections"] += 1
    return {t: {**v, "extraction_errors": dict(v["extraction_errors"]), "error_modules": dict(v["error_modules"])}
            for t, v in st.items()}


def summarize(root: Path = ROOT, month: Optional[str] = None) -> Dict[str, Any]:
    all_events = ql.load_events(root)
    events = [e for e in all_events if _in_month(e["date"], month)]
    ids = {e["quality_event_id"] for e in events}
    corrections = [c for c in ql.load_corrections(root) if c["quality_event_id"] in ids]
    reviewed = [e for e in events if e["review_status"] == "reviewed"]
    pending = [e for e in events if e["review_status"] in ("pending", "in_review")]
    system = [e for e in events if e.get("origin") != "manual_missed"]
    missed = [e for e in events if e.get("origin") == "manual_missed"]

    det_rev = [e for e in system if _bool(e, "event_detected_correctly") in (True, False)
               or _bool(e, "false_positive") in (True, False)]
    fp = [e for e in system if _bool(e, "false_positive") is True]
    det_ok = [e for e in det_rev if _bool(e, "event_detected_correctly") is True and _bool(e, "false_positive") is not True]
    fn = [e for e in events if _bool(e, "false_negative") is True]
    dup = [e for e in events if "duplicate" in str(e["human_review"].get("notes", "")).lower()]

    verdicts = Counter(e["human_review"].get("classification_verdict") for e in events
                       if e["human_review"].get("classification_verdict") not in (ql.UNKNOWN, ql.NA))
    pr_rev = [e for e in system if _bool(e, "priority_correct") in (True, False)
              and e["system_output"].get("priority") in ql.PRIORITIES]
    pr_ok = [e for e in pr_rev if _bool(e, "priority_correct") is True]
    by_reviewed_priority = Counter(e["human_review"].get("reviewed_priority") for e in pr_rev
                                   if e["human_review"].get("reviewed_priority") in ql.PRIORITIES)
    pr_dirs = Counter()
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    for e in pr_rev:
        rp, sp = e["human_review"].get("reviewed_priority"), e["system_output"].get("priority")
        if rp in order and rp != sp:
            pr_dirs["system_too_high" if order[sp] < order[rp] else "system_too_low"] += 1

    g_items_rev = g_items_ok = 0
    for e in events:
        hr = e["human_review"]
        if hr.get("guidance_items_reviewed"):
            g_items_rev += hr["guidance_items_reviewed"]
            g_items_ok += hr.get("guidance_items_correct") or 0
        elif hr.get("guidance_extracted_correctly") in (True, False):
            g_items_rev += 1
            g_items_ok += hr["guidance_extracted_correctly"] is True
        else:
            g_items_rev += sum(x["module"] == "guidance_tracker" for x in hr.get("extraction_errors") or [])
    ext = Counter()
    ext_by_type = Counter()
    for e in events:
        for x in e["human_review"].get("extraction_errors") or []:
            ext[x["module"]] += 1
            ext_by_type[x["error_type"]] += 1
    for e in events:  # boolean "extraction wrong" without a typed error still counts once per module
        hr = e["human_review"]
        typed = {x["module"] for x in hr.get("extraction_errors") or []}
        for f, m in (("guidance_extracted_correctly", "guidance_tracker"), ("kpi_extraction_correct", "kpi_registry"),
                     ("management_change_correct", "management_diff")):
            if hr.get(f) is False and m not in typed:
                ext[m] += 1
    interp = Counter(e["human_review"].get("interpretation_verdict") for e in events
                     if e["human_review"].get("interpretation_verdict") not in (ql.UNKNOWN, ql.NA))
    value = Counter(e["human_review"].get("research_value") for e in events
                    if e["human_review"].get("research_value") in ("HIGH", "MEDIUM", "LOW", "NONE"))
    corr_cat = Counter(f"{c['module']}:{c['field']}" for c in corrections)

    mods = module_stats(events, corrections)
    tick = ticker_stats(events, corrections)
    rated = [(m, s) for m, s in mods.items() if s["agreement"]["value"] != INSUFFICIENT]
    reliable = sorted(rated, key=lambda x: (-x[1]["agreement"]["value"], -x[1]["reviewed"]))[:3]
    weakest = sorted(rated, key=lambda x: (x[1]["agreement"]["value"], -x[1]["reviewed"]))[:3]
    # without a large enough sample, name the module with the most recorded errors (a count, not a rate)
    by_err = sorted(((m, s["errors"] + s["extraction_errors"] + s["corrections"]) for m, s in mods.items()),
                    key=lambda x: -x[1])
    weakest_by_count = [m for m, n in by_err if n > 0][:3]
    problem_tickers = sorted(((t, s["events_with_issues"], s["errors"]) for t, s in tick.items()),
                             key=lambda x: (-x[1], -x[2]))

    req_pending = [e for e in pending if e.get("review_requirement") == "required"]
    actions = []
    if req_pending:
        actions.append(f"完成 {len(req_pending)} 筆 HIGH / required 的待 review 事件（"
                       + ", ".join(e["quality_event_id"] for e in req_pending[:5]) + ("…" if len(req_pending) > 5 else "") + "）")
    if fn:
        actions.append(f"檢查 {len(fn)} 筆漏抓事件的偵測規則缺口（event_detector；只記錄，不自動改規則）")
    if fp:
        actions.append(f"檢查 {len(fp)} 筆 false positive 的事件來源與門檻（event_detector / event_classifier）")
    if pr_dirs:
        actions.append(f"比對 priority 分歧方向 {dict(pr_dirs)}，判斷 research-policy.yaml 門檻是否需人工調整")
    for m in (weakest_by_count if not weakest else [m for m, _ in weakest])[:2]:
        actions.append(f"抽查 {m} 的近期輸出（錯誤 / 修正最多的模組）")
    if not reviewed:
        actions.append("目前尚無人工 review；先從 required 事件開始，累積樣本後 metrics 才有意義")
    if not actions:
        actions.append("維持抽樣 review；本月無明顯品質問題")

    return {
        "month": month, "generated_at": ql.now_iso(), "min_sample": MIN_SAMPLE,
        "coverage": {"events_processed": len(events), "system_events": len(system), "events_reviewed": len(reviewed),
                     "pending_reviews": len(pending), "required_pending": len(req_pending),
                     "by_workflow": dict(Counter(e["workflow"] for e in events)),
                     "by_origin": dict(Counter(e.get("origin", "auto") for e in events))},
        "event_detection": {"correct_detections": len(det_ok), "detections_reviewed": len(det_rev),
                            "false_positives": len(fp), "false_negatives": len(fn), "missed_events": len(missed),
                            "duplicates_noted": len(dup),
                            "precision": ratio(len(det_ok), len(det_rev)),
                            "recall": ratio(len(det_ok), len(det_ok) + len(fn))},
        "classification": {k: verdicts.get(k, 0) for k in ("correct", "too_high", "too_low", "wrong_type")},
        "priority": {"reviewed": len(pr_rev), "agreement": ratio(len(pr_ok), len(pr_rev)),
                     "disagreement": ratio(len(pr_rev) - len(pr_ok), len(pr_rev)),
                     "by_reviewed_priority": {k: by_reviewed_priority.get(k, 0) for k in ql.PRIORITIES},
                     "disagreement_direction": dict(pr_dirs)},
        "extraction": {"guidance_errors": ext.get("guidance_tracker", 0), "kpi_errors": ext.get("kpi_registry", 0),
                       "management_extraction_errors": ext.get("management_diff", 0),
                       "promise_errors": ext.get("promise_tracker", 0),
                       "metric_definition_errors": ext_by_type.get("wrong_metric_definition", 0),
                       "by_error_type": dict(ext_by_type),
                       "guidance_accuracy": ratio(g_items_ok, g_items_rev)},
        "interpretation": {k: interp.get(k, 0) for k in ("correct", "reasonable_but_uncertain", "overinterpreted",
                                                         "underinterpreted", "unsupported")},
        "research_value": {k: value.get(k, 0) for k in ("HIGH", "MEDIUM", "LOW", "NONE")},
        "manual_corrections": {"total": len(corrections), "top_categories": corr_cat.most_common(5)},
        "modules": mods, "tickers": tick,
        "most_problematic_tickers": [(t, n, k) for t, n, k in problem_tickers if n > 0][:3],
        "most_reliable_modules": [(m, s["agreement"]) for m, s in reliable],
        "weakest_modules": [(m, s["agreement"]) for m, s in weakest],
        "weakest_modules_by_error_count": weakest_by_count,
        "actions_next_month": actions,
        "hindsight_rule": "Quality grades process, evidence and reasoning available at the time; later price moves "
                          "and returns are never used (no price data is read).",
    }


def largest_weakness(s: Dict[str, Any]) -> str:
    if s["weakest_modules"]:
        m, r = s["weakest_modules"][0]
        return f"{m}（{fmt_ratio(r)}）"
    if s["weakest_modules_by_error_count"]:
        return f"{s['weakest_modules_by_error_count'][0]}（依錯誤筆數；樣本不足以算比率）"
    return "尚無（無已 review 的錯誤）"


def render(s: Dict[str, Any]) -> str:
    c, d, p, x = s["coverage"], s["event_detection"], s["priority"], s["extraction"]
    L = [f"# Research OS Quality Summary（{s['month'] or '全部期間'}）", "",
         "> 評估的是研究流程品質（偵測、分類、優先順序、抽取、解讀、研究價值），不是報酬預測。"
         f"不讀取股價；比率分母 < {MIN_SAMPLE} 時顯示 {INSUFFICIENT}。auto 建立的事件預設 pending，未經人工確認。", "",
         "## Coverage",
         f"- Events processed：{c['events_processed']}（系統事件 {c['system_events']}；來源 {c['by_origin']}）",
         f"- Events reviewed：{c['events_reviewed']}",
         f"- Pending reviews：{c['pending_reviews']}（其中 required {c['required_pending']}）",
         f"- 依 workflow：{c['by_workflow']}", "",
         "## Event Detection",
         f"- Correct detections：{d['correct_detections']}（已 review {d['detections_reviewed']}）",
         f"- False positives：{d['false_positives']}",
         f"- False negatives：{d['false_negatives']}",
         f"- Missed events（人工補登）：{d['missed_events']}",
         f"- Event precision：{fmt_ratio(d['precision'])}",
         f"- Event recall：{fmt_ratio(d['recall'])}", "",
         "## Classification",
         *[f"- {k}：{v}" for k, v in s["classification"].items()], "",
         "## Priority",
         *[f"- {k} reviewed：{v}" for k, v in p["by_reviewed_priority"].items()],
         f"- Priority agreement：{fmt_ratio(p['agreement'])}",
         f"- Priority disagreement rate：{fmt_ratio(p['disagreement'])}",
         f"- 分歧方向：{p['disagreement_direction'] or '無'}", "",
         "## Extraction",
         f"- Guidance errors：{x['guidance_errors']}",
         f"- KPI errors：{x['kpi_errors']}",
         f"- Management extraction errors：{x['management_extraction_errors']}",
         f"- Promise errors：{x['promise_errors']}",
         f"- Metric-definition errors：{x['metric_definition_errors']}",
         f"- 錯誤類型：{x['by_error_type'] or '無'}",
         f"- Guidance extraction accuracy：{fmt_ratio(x['guidance_accuracy'])}", "",
         "## Interpretation",
         f"- Overinterpretation：{s['interpretation']['overinterpreted']}",
         f"- Underinterpretation：{s['interpretation']['underinterpreted']}",
         f"- Unsupported inference：{s['interpretation']['unsupported']}",
         f"- Correct / reasonable_but_uncertain：{s['interpretation']['correct']} / {s['interpretation']['reasonable_but_uncertain']}", "",
         "## Research Value",
         *[f"- {k}：{v}" for k, v in s["research_value"].items()], "",
         "## Manual Corrections",
         f"- Total：{s['manual_corrections']['total']}（永久保存在 research/quality/corrections.jsonl；不會自動改規則）",
         "- Top correction categories：" + ("；".join(f"{k} ×{n}" for k, n in s["manual_corrections"]["top_categories"]) or "無"),
         "", "## Module Quality", "",
         "| Module | Reviewed | Correct | Errors | Extraction errors | Corrections | Agreement |",
         "|---|---|---|---|---|---|---|"]
    for m, v in s["modules"].items():
        L.append(f"| {m} | {v['reviewed']} | {v['correct']} | {v['errors']} | {v['extraction_errors']} | "
                 f"{v['corrections']} | {fmt_ratio(v['agreement'])} |")
    L += ["", "## Ticker Quality", "",
          "| Ticker | Events | Reviewed | Pending | FP | FN | Events with issues | Extraction errors by module | Corrections |",
          "|---|---|---|---|---|---|---|---|---|"]
    for t, v in sorted(s["tickers"].items()):
        L.append(f"| {t} | {v['events']} | {v['reviewed']} | {v['pending']} | {v['false_positives']} | "
                 f"{v['false_negatives']} | {v['events_with_issues']} | {v['extraction_errors'] or '—'} | {v['corrections']} |")
    L += ["", "## Most Problematic Tickers"]
    L += [f"- {t}：{n} 筆事件有問題（共 {k} 個錯誤判定）" for t, n, k in s["most_problematic_tickers"]] \
        or ["- 尚無（沒有已 review 的錯誤）"]
    L += ["", "## Most Reliable Modules"]
    L += [f"- {m}：{fmt_ratio(r)}" for m, r in s["most_reliable_modules"]] or [f"- {INSUFFICIENT}（沒有模組達到 n ≥ {MIN_SAMPLE}）"]
    L += ["", "## Weakest Modules"]
    if s["weakest_modules"]:
        L += [f"- {m}：{fmt_ratio(r)}" for m, r in s["weakest_modules"]]
    else:
        L += [f"- {INSUFFICIENT}（沒有模組達到 n ≥ {MIN_SAMPLE}）"]
        if s["weakest_modules_by_error_count"]:
            L.append("- 依錯誤筆數（非比率）：" + ", ".join(s["weakest_modules_by_error_count"]))
    L += ["", "## Actions for Next Month"] + [f"{i}. {a}" for i, a in enumerate(s["actions_next_month"], 1)]
    L += ["", "## Hindsight-bias rule",
          "- 不用股價後來的漲跌評斷 thesis、valuation 或 extraction；WATCH 後來上漲不算 failure，BUY 後來下跌不算 extraction failure。",
          "- 只評估當時可得的證據、流程與推理。", ""]
    return "\n".join(L)


def run(month: Optional[str] = None, root: Path = ROOT, write: bool = True) -> Dict[str, Any]:
    month = month or date.today().strftime("%Y-%m")
    s = summarize(root, month)
    text = render(s)
    out = ql.quality_dir(root) / "summaries" / f"{month}-quality-summary.md"
    if write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        out.with_suffix(".json").write_text(json.dumps(s, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return {"path": str(out), "summary": s, "text": text}


def compact(root: Path = ROOT, month: Optional[str] = None) -> Dict[str, Any]:
    """Short status for the dashboard / monthly review (whole log unless a month is given)."""
    s = summarize(root, month)
    return {"reviewed": s["coverage"]["events_reviewed"], "pending": s["coverage"]["pending_reviews"],
            "required_pending": s["coverage"]["required_pending"],
            "false_positives": s["event_detection"]["false_positives"],
            "false_negatives": s["event_detection"]["false_negatives"],
            "priority_agreement": s["priority"]["agreement"], "manual_corrections": s["manual_corrections"]["total"],
            "largest_weakness": largest_weakness(s), "next_action": s["actions_next_month"][0], "summary": s}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--month", help="YYYY-MM (default: current month)")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--print", action="store_true", help="print the summary")
    a = ap.parse_args(argv)
    res = run(a.month, a.root)
    print(res["path"])
    if a.print:
        print(res["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
