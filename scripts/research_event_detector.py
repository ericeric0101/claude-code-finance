#!/usr/bin/env python3
"""Research event detector (Level 4): what happened since the last check that may need research.

Sources (incremental; only items newer than research/<T>/monitoring/scan-state.json):
  SEC      10-Q, 10-K, 8-K (by item), DEF 14A, Form 4, Form 144, S-3 / 424B (capital raise),
           S-4 / 425 (merger) from the submissions list (raw/submissions.json; refreshed with
           --refresh, one small request per ticker). A 10-Q / 10-K newer than the filing the
           state was built from is always reported, whatever the scan window.
  Company  issuer announcements recorded in market/events.csv; guidance updates in
           management/guidance.json (raised / lowered vs the previous range for the same period).
  Market   major daily price move, abnormal volume, major drawdown, new 52-week high / low,
           large move since the last research review (market/prices.csv; refreshed separately).
  State    newly triggered monitoring rules / thesis invalidation, promises newly missed or
           delayed, management semantic findings, expectation-gap and valuation-percentile moves.
  Macro    only items in research/queue/macro-inbox.json whose topic is in the ticker's
           `macro_links` (config/watchlist.yaml); other macro news is ignored.

Routine insider filings (Form 4 / 144) are aggregated into one event per ticker per scan.
Output is a list of raw events; classification is research_event_classifier.py.

Usage: python3 scripts/research_event_detector.py PL [--as-of YYYY-MM-DD] [--refresh]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import level4_common as l4  # noqa: E402

ITEM_EVENTS = {  # 8-K item → event type
    "2.02": "earnings_release", "1.01": "major_contract", "2.01": "acquisition", "5.02": "management_change",
    "3.02": "capital_raise", "7.01": "investor_presentation", "2.05": "restructuring", "2.06": "impairment",
    "4.02": "non_reliance", "1.03": "bankruptcy", "5.07": "shareholder_vote", "8.01": "other_event",
}
CAPITAL_FORMS = ("S-3", "S-3ASR", "S-1", "424B5", "424B3", "424B2")
ANNOUNCE_WORDS = [("guidance_update", ("guidance", "outlook", "reaffirm")),
                  ("acquisition", ("acquire", "acquisition", "merger", "to buy")),
                  ("capital_raise", ("offering", "convertible", "at-the-market", "atm program", "private placement")),
                  ("major_contract", ("contract", "award", "selected", "agreement", "tender", "order")),
                  ("product_launch", ("launch", "unveil", "introduce", "available", "release of")),
                  ("management_change", ("appoint", "ceo", "cfo", "resign", "steps down", "chief")),
                  ("investor_presentation", ("investor day", "presentation", "conference"))]


def event_id(ticker: str, etype: str, ts: str, key: str) -> str:
    return f"{ticker}-{ts}-{etype}-" + hashlib.sha1(f"{ticker}|{etype}|{ts}|{key}".encode()).hexdigest()[:8]


def _ev(ticker: str, etype: str, ts: str, source: str, source_type: str, key: str, **details: Any) -> Dict[str, Any]:
    return {"event_id": event_id(ticker, etype, ts, key), "ticker": ticker, "event_type": etype, "timestamp": ts,
            "source": source, "source_type": source_type,
            "evidence_quality": l4.evidence_quality(source_type, source), "details": details}


# --------------------------------------------------------------------------- SEC

def sec_events(ticker: str, sub: Dict[str, Any], since: str, as_of: str, state_filed: Optional[str],
               forms: List[str], seen: set) -> List[Dict[str, Any]]:
    r = (sub.get("filings") or {}).get("recent") or {}
    cik = str(sub.get("cik") or "")
    out, insiders = [], []
    for i, form in enumerate(r.get("form") or []):
        filed = r["filingDate"][i]
        acc = r["accessionNumber"][i]
        if filed > as_of:
            continue
        base_form = form.split("/")[0]
        if base_form not in forms and form not in forms:
            continue
        primary_periodic = base_form in ("10-Q", "10-K")
        newer_than_state = primary_periodic and state_filed and filed > state_filed
        if acc in seen or (not newer_than_state and filed <= since):
            continue  # already queued by an earlier scan, or older than the scan window
        if primary_periodic and state_filed and filed <= state_filed:
            continue  # already incorporated in financials/history.json
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik) if cik else 0}/{acc.replace('-', '')}/{r['primaryDocument'][i]}"
        items = r.get("items", [""] * len(r["form"]))[i] or ""
        st = f"SEC {form}"
        if base_form in ("4", "144"):
            insiders.append({"form": form, "filed": filed, "accession": acc})
            continue
        if primary_periodic:
            out.append(_ev(ticker, "sec_10q" if base_form == "10-Q" else "sec_10k", filed, url, st, acc, form=form,
                           report_date=r["reportDate"][i], accession=acc, amendment=form.endswith("/A"),
                           newer_than_state=bool(newer_than_state), state_latest_filed=state_filed))
        elif base_form == "8-K":
            its = [x.strip() for x in items.split(",") if x.strip()]
            types = [ITEM_EVENTS[x] for x in its if x in ITEM_EVENTS] or ["other_event"]
            main = next((t for t in ("earnings_release", "acquisition", "major_contract", "capital_raise",
                                     "management_change", "non_reliance", "impairment", "restructuring",
                                     "investor_presentation", "shareholder_vote") if t in types), types[0])
            out.append(_ev(ticker, main, filed, url, f"SEC 8-K items {items}", acc, form=form, items=its,
                           accession=acc, amendment=form.endswith("/A")))
        elif base_form in CAPITAL_FORMS:
            out.append(_ev(ticker, "capital_raise", filed, url, st, acc, form=form, accession=acc))
        elif base_form in ("S-4", "425"):
            out.append(_ev(ticker, "acquisition", filed, url, st, acc, form=form, accession=acc,
                           note="merger registration / communication"))
        elif base_form == "DEF 14A":
            out.append(_ev(ticker, "proxy_statement", filed, url, st, acc, form=form, accession=acc))
        elif base_form in ("SC 13D", "SCHEDULE 13D"):
            out.append(_ev(ticker, "activist_stake", filed, url, st, acc, form=form, accession=acc))
    if insiders:
        last = max(x["filed"] for x in insiders)
        out.append(_ev(ticker, "insider_filings", last, "SEC Form 4 / 144 (submissions list)", "SEC Form 4",
                       ",".join(sorted(x["accession"] for x in insiders)),
                       form4=sum(x["form"].startswith("4") for x in insiders),
                       form144=sum(x["form"].startswith("144") for x in insiders),
                       first=min(x["filed"] for x in insiders), last=last,
                       accessions=[x["accession"] for x in insiders][:50]))
    return out


# --------------------------------------------------------------------------- company / market

def announcement_events(ticker: str, base: Path, since: str, as_of: str) -> List[Dict[str, Any]]:
    out = []
    for r in l4.read_csv(base / "market/events.csv"):
        d = r.get("event_date", "")
        if not (since < d <= as_of) or "8-K" in r.get("event_type", ""):
            continue
        text = f"{r.get('description', '')}".lower()
        etype = next((t for t, words in ANNOUNCE_WORDS if any(w in text for w in words)), "company_announcement")
        out.append(_ev(ticker, etype, d, r.get("source", ""), "issuer press release", r.get("description", ""),
                       description=r.get("description"), recorded_type=r.get("event_type")))
    return out


def guidance_events(ticker: str, base: Path, since: str, as_of: str) -> List[Dict[str, Any]]:
    out = []
    g = sorted(l4.read_json(base / "management/guidance.json", []) or [], key=lambda x: x["issued"])
    for x in g:
        if not (since < x["issued"] <= as_of):
            continue
        prev = [y for y in g if y["metric"] == x["metric"] and y["period"] == x["period"] and y["issued"] < x["issued"]]
        if not prev:
            continue
        p = prev[-1]
        mid0, mid1 = (p["low"] + p["high"]) / 2, (x["low"] + x["high"]) / 2
        if abs(mid1 - mid0) < 1e-9:
            continue
        direction = "raised" if mid1 > mid0 else "lowered"
        spending = x["metric"] in ("capex", "gaap_operating_expenses", "non_gaap_operating_expenses", "sbc")
        out.append(_ev(ticker, "guidance_update", x["issued"], x.get("source", ""), "official quantified guidance range",
                       f"{x['metric']}|{x['period']}|{x['issued']}", metric=x["metric"], period=x["period"],
                       direction=direction, spending_plan=spending,
                       previous=[p["low"], p["high"]], current=[x["low"], x["high"]], unit=x.get("unit"),
                       change_pct=round((mid1 / mid0 - 1) * 100, 2) if mid0 else None))
    return out


def market_events(ticker: str, base: Path, since: str, as_of: str, policy: Dict[str, Any],
                  first_scan: bool) -> List[Dict[str, Any]]:
    mp = policy["market"]
    px = [p for p in l4.prices(ticker, base.parent.parent) if p["date"] <= as_of]
    if len(px) < 60:
        return []
    out = []
    idx = [i for i, p in enumerate(px) if p["date"] > since][-int(mp["max_backfill_sessions"]):]
    look = int(mp["lookback_sessions"])
    src = "market/prices.csv (dated market source)"
    for i in idx:
        if i < 1:
            continue
        p, q = px[i], px[i - 1]
        chg = (p["close"] / q["close"] - 1) * 100
        if abs(chg) >= mp["daily_move_pct"]:
            out.append(_ev(ticker, "major_price_move", p["date"], src, "market data", "d", move_pct=round(chg, 2),
                           close=p["close"]))
        vols = [x["volume"] for x in px[max(0, i - 50):i] if x.get("volume")]
        if p.get("volume") and len(vols) >= 20:
            ratio = p["volume"] / (sum(vols) / len(vols))
            if ratio >= mp["volume_ratio"]:
                out.append(_ev(ticker, "abnormal_volume", p["date"], src, "market data", "v",
                               volume_ratio=round(ratio, 2), move_pct=round(chg, 2)))
        window = px[max(0, i - look):i]
        if len(window) >= 200:
            hi, lo = max(x["close"] for x in window), min(x["close"] for x in window)
            if p["close"] > hi:
                out.append(_ev(ticker, "new_52w_high", p["date"], src, "market data", "h", close=p["close"], prior_high=hi))
            if p["close"] < lo:
                out.append(_ev(ticker, "new_52w_low", p["date"], src, "market data", "l", close=p["close"], prior_low=lo))
            dd = (p["close"] / hi - 1) * 100
            dd_prev = (q["close"] / max(x["close"] for x in px[max(0, i - 1 - look):i - 1] or [q]) - 1) * 100
            if dd <= -mp["drawdown_pct"] < dd_prev or (dd <= -mp["drawdown_pct"] and i == idx[0]):
                out.append(_ev(ticker, "major_drawdown", p["date"], src, "market data", "dd",
                               drawdown_pct=round(dd, 2), high_252=hi))
    # move since the price the research state is built on
    latest = l4.read_json(base / "valuation/latest.json", {}) or {}
    ref, ref_date = latest.get("price"), latest.get("price_date")
    if ref and px:
        move = (px[-1]["close"] / float(ref) - 1) * 100
        if abs(move) >= mp["large_move_pct"]:
            out.append(_ev(ticker, "large_move_since_review", px[-1]["date"], src, "market data",
                           f"{ref_date}|{round(move)}", move_pct=round(move, 2), reference_price=ref,
                           reference_date=ref_date, close=px[-1]["close"]))
    return out


# --------------------------------------------------------------------------- state events

CONDITION_TOKENS = ("dilution", "capex", "rpo", "backlog", "receivable", "inventory", "margin", "revenue", "fcf", "cash",
                    "services", "debt")


def condition_family(rule: Dict[str, Any]) -> str:
    """Underlying condition of a rule, so a monitoring rule and an invalidation rule on the same metric count once."""
    text = " ".join(str(x) for x in (rule.get("rule"), rule.get("metric"), json.dumps(rule.get("values") or {}))).lower()
    for tok in CONDITION_TOKENS:
        if tok in text:
            return "backlog/rpo" if tok in ("rpo", "backlog") else tok
    return str(rule.get("rule"))


def state_events(ticker: str, base: Path, root: Path, scan: Dict[str, Any], as_of: str,
                 policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    import research_state as rs
    out = []
    rules = rs.check_rules(ticker, root)
    trig = sorted(r["rule"] for r in rules if r["state"] == "triggered")
    standing_since = None
    if scan.get("triggered_rules") is None:  # first scan: rules already triggered in the last snapshot
        snaps = [l4.read_json(p, {}) for p in sorted((base / "snapshots").glob("*.json"))]
        snaps = [x for x in snaps if x and not x.get("retrospective")]
        if snaps:
            standing_since = snaps[-1]["as_of"]
            before = {k for k, v in (snaps[-1].get("rules") or {}).items() if v.get("state") == "triggered"}
        else:
            before = set()
    else:
        before = set(scan.get("triggered_rules") or [])
    for r in rules:
        if r["state"] != "triggered" or (r["rule"] in before and standing_since is None):
            continue
        value = r.get("value") if r["type"] != "invalidation" else r.get("values")
        common = dict(rule=r["rule"], rule_type=r["type"], value=value, warning=r.get("warning"),
                      thesis_component=r.get("thesis_component"), condition=condition_family(r), meaning=l4.REASSESS)
        src = f"monitoring/rules.yaml / thesis/invalidation-rules.yaml ({r['rule']})"
        if r["rule"] in before:  # already reported in the last change report; reassessment still open
            out.append(_ev(ticker, "standing_trigger", as_of, src, "research state (rule evaluation on SEC data)", r["rule"],
                           triggered_since=standing_since, **common))
            continue
        et = "thesis_invalidation" if r["type"] == "invalidation" else "monitoring_trigger"
        out.append(_ev(ticker, et, as_of, src, "research state (rule evaluation on SEC data)", r["rule"], **common))
    scan["triggered_rules"] = trig
    prom = l4.read_json(base / "management/promises.json", []) or []
    seen_status = scan.get("promise_status")
    if seen_status is None:  # first scan: compare with what the latest live snapshot knew
        snaps = [l4.read_json(p, {}) for p in sorted((base / "snapshots").glob("*.json"))]
        snaps = [x for x in snaps if x and not x.get("retrospective")]
        known = ((snaps[-1].get("management") or {}).get("promises") or {}) if snaps else {}
        seen_status = {k: v.get("status") for k, v in known.items()}
    for p in prom:
        st = p.get("status")
        if st in ("missed", "delayed") and seen_status.get(p["promise_id"]) != st:
            out.append(_ev(ticker, "promise_missed" if st == "missed" else "promise_delayed", as_of,
                           p.get("source", ""), "issuer earnings release (promise tracker)", p["promise_id"],
                           promise_id=p["promise_id"], rule=p.get("resolution_rule"),
                           comparison_basis=p.get("comparison_basis"),
                           spending_plan="spending-plan" in (p.get("resolution_rule") or "")))
    scan["promise_status"] = {p["promise_id"]: p.get("status") for p in prom}
    sd = l4.read_json(base / "management/semantic-diff.json", {}) or {}
    since = scan.get("_since", "")
    for f in sd.get("findings") or []:
        # quantitative guidance changes are already guidance_update events; only timing claims are added here
        if f.get("as_of", "") > since and f["dimension"] == "timing":
            out.append(_ev(ticker, "management_wording_change", f.get("as_of") or as_of,
                           (f.get("sources") or [""])[-1], "semantic inference" if f["CONFIDENCE"] != "high"
                           else "official quantified guidance range", f["CHANGE"],
                           dimension=f["dimension"], change=f["CHANGE"], confidence=f["CONFIDENCE"]))
    stmts = l4.read_json(base / "management/statements.json", []) or []
    if stmts:
        scan["last_management_update"] = max(str(s.get("date", "")) for s in stmts)
    gh = l4.read_csv(base / "valuation/expectation-gap-history.csv")
    if gh:
        dates = sorted({r["date"] for r in gh})
        if len(dates) >= 2 and dates[-1] > (scan.get("last_gap_date") or ""):
            cur = {r["metric"]: r for r in gh if r["date"] == dates[-1]}
            prev = {r["metric"]: r for r in gh if r["date"] == dates[-2]}
            for k, r in cur.items():
                if k in prev and r.get("gap_vs_base") and prev[k].get("gap_vs_base"):
                    d = abs(float(r["gap_vs_base"])) - abs(float(prev[k]["gap_vs_base"]))
                    if abs(d) >= policy["priority"]["expectation_gap_change"]:
                        out.append(_ev(ticker, "expectation_gap_change", dates[-1],
                                       "valuation/expectation-gap-history.csv", "research state (calculation on SEC data and prices)", k,
                                       metric=k, change=round(d, 4), direction="widened" if d > 0 else "narrowed"))
        scan["last_gap_date"] = dates[-1]
    snaps = sorted((base / "snapshots").glob("*.json"))
    live = [l4.read_json(p, {}) for p in snaps]
    live = [s for s in live if s and not s.get("retrospective")]
    if len(live) >= 2 and live[-1]["as_of"] > (scan.get("last_percentile_date") or ""):
        a = (live[-2].get("valuation") or {}).get("percentiles") or {}
        b = (live[-1].get("valuation") or {}).get("percentiles") or {}
        for mult, v in b.items():
            for w in ("3y", "since_listing"):
                x, y = (a.get(mult) or {}).get(w), v.get(w)
                if isinstance(x, (int, float)) and isinstance(y, (int, float)) and \
                        abs(y - x) >= policy["priority"]["valuation_percentile_change"]:
                    out.append(_ev(ticker, "valuation_rerating", live[-1]["as_of"], "valuation/historical-percentiles.json",
                                   "research state (calculation on SEC data and prices)", f"{mult}|{w}", multiple=mult, window=w,
                                   previous=x, current=y))
        scan["last_percentile_date"] = live[-1]["as_of"]
    return out


def macro_events(ticker: str, root: Path, since: str, as_of: str, links: List[str]) -> List[Dict[str, Any]]:
    out = []
    for m in l4.read_json(root / "research/queue/macro-inbox.json", []) or []:
        if m.get("topic") not in (links or []) or not (since < m.get("date", "") <= as_of):
            continue
        if m.get("tickers") and ticker not in m["tickers"]:
            continue
        out.append(_ev(ticker, "macro_thesis_link", m["date"], m.get("source", ""), m.get("source_type", "secondary"),
                       m.get("headline", ""), topic=m["topic"], headline=m.get("headline")))
    return out


# --------------------------------------------------------------------------- entry

def detect(ticker: str, root: Path = ROOT, as_of: Optional[str] = None, refresh: bool = False,
           save_state: bool = True, since_override: Optional[str] = None) -> Dict[str, Any]:
    t = ticker.upper()
    as_of = l4.today(as_of)
    base = l4.company_dir(t, root)
    policy = l4.load_policy(root)
    entry = l4.watch_entry(t, root)
    scan = l4.load_scan_state(t, root)
    first = not scan.get("last_checked")
    if not first:
        since = scan["last_checked"]
    else:  # first scan: what happened since the last research review (bounded look-back)
        floor = (date.fromisoformat(as_of) - timedelta(days=int(policy["scan"]["first_scan_lookback_days"]))).isoformat()
        since = max(floor, l4.latest_review_date(t, root) or floor)
    if since_override:  # replay a window (dry runs / backfills); never combine with save_state
        since, first, save_state = since_override, False, False
        scan = dict(scan, seen_accessions=[], triggered_rules=None, promise_status=None)
    sub = {}
    if refresh and entry.get("cik"):
        import sec_data
        sub = sec_data.submissions(str(entry["cik"]), t, root, refresh=True)
    else:
        sub = l4.read_json(base / "raw/submissions.json", {}) or {}
    snaps = sorted((base / "snapshots").glob("*.json"))
    state_filed = None
    for p in reversed(snaps):
        s = l4.read_json(p, {}) or {}
        if not s.get("retrospective"):
            state_filed = (s.get("financials") or {}).get("latest_filed")
            break
    seen = set(scan.get("seen_accessions") or [])
    events = sec_events(t, sub, since, as_of, state_filed, policy["scan"]["sec_forms"], seen) if sub else []
    events += announcement_events(t, base, since, as_of)
    events += guidance_events(t, base, since, as_of)
    events += market_events(t, base, since, as_of, policy, first)
    scan["_since"] = since
    events += state_events(t, base, root, scan, as_of, policy)
    scan.pop("_since", None)
    events += macro_events(t, root, since, as_of, entry.get("macro_links") or [])
    uniq = {e["event_id"]: e for e in events}
    events = sorted(uniq.values(), key=lambda e: (e["timestamp"], e["event_type"]))
    for e in events:
        e["detected_at"] = l4.now_iso()
        e["scan_window"] = {"since": since, "as_of": as_of, "first_scan": first}
    r = (sub.get("filings") or {}).get("recent") or {}
    accs = [a for a, d in zip(r.get("accessionNumber") or [], r.get("filingDate") or []) if d <= as_of]
    scan["seen_accessions"] = sorted(set(list(seen) + accs[:300]))[-400:]
    periodic = [d for f, d in zip(r.get("form") or [], r.get("filingDate") or [])
                if f.split("/")[0] in ("10-Q", "10-K") and d <= as_of]
    scan["last_filing"] = max(periodic) if periodic else scan.get("last_filing")
    px = l4.prices(t, root)
    scan["last_price_update"] = px[-1]["date"] if px else scan.get("last_price_update")
    scan["last_checked"] = as_of
    scan["state_latest_filed"] = state_filed
    if save_state:
        l4.save_scan_state(t, scan, root)
    return {"ticker": t, "since": since, "as_of": as_of, "first_scan": first, "events": events, "scan_state": scan}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--as-of")
    ap.add_argument("--refresh", action="store_true", help="refresh SEC submissions list (network)")
    ap.add_argument("--dry-run", action="store_true", help="do not update scan-state.json")
    ap.add_argument("--since", help="replay events after this date (implies --dry-run)")
    args = ap.parse_args(argv)
    res = detect(args.ticker, as_of=args.as_of, refresh=args.refresh, save_state=not args.dry_run,
                 since_override=args.since)
    for e in res["events"]:
        print(f"{e['timestamp']} {e['event_type']:24s} {json.dumps(e['details'], ensure_ascii=False)[:110]}")
    print(f"{res['ticker']}: {len(res['events'])} events since {res['since']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
