#!/usr/bin/env python3
"""Small SEC EDGAR access layer for the research OS (network).

Reuses the unmodified finance-skill client for JSON endpoints (it loads .env
for SEC_EDGAR_USER_AGENT) and adds cached document fetches. Raw payloads go to
research/<TICKER>/raw/, which is git-ignored. Credentials are never printed.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
_FS = ROOT / ".claude/skills/finance-skill/scripts"
_LAST_CALL = [0.0]


def _client():
    if str(_FS) not in sys.path:
        sys.path.insert(0, str(_FS))
    import env  # noqa: F401  (loads .env; values are never printed)
    import sec_edgar
    return sec_edgar


def _throttle() -> None:
    wait = 0.15 - (time.time() - _LAST_CALL[0])
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL[0] = time.time()


def raw_dir(ticker: str, root: Path = ROOT) -> Path:
    d = root / "research" / ticker.upper() / "raw"
    d.mkdir(parents=True, exist_ok=True)
    return d


def company_facts(cik: str, ticker: str, root: Path = ROOT, refresh: bool = True) -> Dict[str, Any]:
    path = raw_dir(ticker, root) / "companyfacts.json"
    if refresh or not path.exists():
        _throttle()
        facts = _client().get_company_facts(cik)
        path.write_text(json.dumps(facts), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def submissions(cik: str, ticker: str, root: Path = ROOT, refresh: bool = True) -> Dict[str, Any]:
    path = raw_dir(ticker, root) / "submissions.json"
    if refresh or not path.exists():
        _throttle()
        sub = _client().get_submissions(cik)
        path.write_text(json.dumps(sub), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def _user_agent() -> str:
    _client()
    ua = os.environ.get("SEC_EDGAR_USER_AGENT")
    if not ua:
        raise RuntimeError("SEC_EDGAR_USER_AGENT is not set (see .env.example)")
    return ua


def fetch_url(url: str, cache: Path) -> str:
    """Fetch a SEC document once; later calls read the git-ignored cache."""
    if cache.exists():
        return cache.read_text(encoding="utf-8", errors="ignore")
    _throttle()
    req = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8", errors="ignore")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8")
    return text


def html_to_text(doc: str) -> str:
    doc = re.sub(r"(?is)<(script|style).*?</\1>", " ", doc)
    doc = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|li|h\d)>", "\n", doc)
    doc = re.sub(r"<[^>]+>", " ", doc)
    doc = html.unescape(doc).replace("\xa0", " ")
    doc = re.sub(r"[ \t]+", " ", doc)
    return re.sub(r"\n\s*\n+", "\n", doc).strip()


def recent_filings(sub: Dict[str, Any], forms: tuple = ("10-K", "10-Q", "8-K")) -> List[Dict[str, Any]]:
    r = sub["filings"]["recent"]
    out = []
    for i, form in enumerate(r["form"]):
        if form.split("/")[0] in forms:
            out.append({"form": form, "filed": r["filingDate"][i], "report_date": r["reportDate"][i],
                        "accession": r["accessionNumber"][i], "primary": r["primaryDocument"][i],
                        "items": r.get("items", [""] * len(r["form"]))[i],
                        "acceptance": r.get("acceptanceDateTime", [""] * len(r["form"]))[i]})
    return out


def filing_base_url(cik: str, accession: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"


def earnings_exhibit(cik: str, ticker: str, accession: str, root: Path = ROOT) -> Optional[Dict[str, str]]:
    """Locate the EX-99.1 earnings release of an 8-K (Item 2.02) and return its text."""
    base = filing_base_url(cik, accession)
    cache = raw_dir(ticker, root) / "filings" / accession
    try:
        index = json.loads(fetch_url(base + "index.json", cache / "index.json"))
    except Exception:
        return None
    names = [i["name"] for i in index.get("directory", {}).get("item", [])]
    cands = [n for n in names if re.search(r"ex-?99[._-]?0?1|ex991|exhibit991", n, re.I)
             and n.lower().endswith((".htm", ".html", ".txt"))]
    if not cands:
        cands = [n for n in names if re.search(r"ex-?99", n, re.I) and n.lower().endswith((".htm", ".html"))]
    if not cands:
        return None
    name = sorted(cands)[0]
    text = html_to_text(fetch_url(base + name, cache / name))
    return {"url": base + name, "text": text}
