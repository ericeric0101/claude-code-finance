#!/usr/bin/env python3
"""NotebookLM export (Level 4, P2, optional reading layer).

Writes research/<TICKER>/exports/notebooklm-sources.md: a source list to load into
NotebookLM (latest SEC filings and earnings releases by URL, management history and
guidance-vs-actual files, the current thesis summary). It copies no raw filings and
writes nothing back: the git repo stays the canonical research state.

Usage: python3 scripts/notebooklm_export.py PL
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import level4_common as l4  # noqa: E402


def export(ticker: str, root: Path = ROOT, n: int = 8, write: bool = True) -> str:
    t = ticker.upper()
    base = l4.company_dir(t, root)
    th = l4.thesis(t, root)
    sources = l4.read_json(base / "evidence/sources.json", []) or []
    filings = sorted([s for s in sources if str(s.get("type", "")).startswith(("10-K", "10-Q"))],
                     key=lambda s: s.get("filed") or s.get("period_end") or "", reverse=True)[:n]
    releases = sorted([r for r in l4.read_csv(base / "market/events.csv") if "2.02" in r.get("event_type", "")],
                      key=lambda r: r["event_date"], reverse=True)[:n]
    L = [f"# {t} NotebookLM source list（{l4.today()}）", "",
         "> 選用閱讀層。NotebookLM 的回答不會寫回 state；git repo 是唯一的 canonical research state。", "",
         "## Current thesis（thesis/current.yaml）", "", f"Action: {th.get('action')}；as of {th.get('as_of')}", "",
         (th.get("summary") or "").strip(), "", "## Latest SEC filings", ""]
    L += [f"- {s.get('type')} period {s.get('period_end')} filed {s.get('filed', '')}: {s.get('url')}" for s in filings] or ["- 無"]
    L += ["", "## Earnings releases（8-K Item 2.02）", ""]
    L += [f"- {r['event_date']} {r['description']}: {r['source']}" for r in releases] or ["- 無"]
    L += ["", "## Management history（repo files to upload as text）", ""]
    for rel in ("management/semantic-diff.md", "management/guidance-vs-actual.md", "management/changes.md"):
        if (base / rel).exists():
            L.append(f"- research/{t}/{rel}")
    text = "\n".join(L) + "\n"
    if write:
        out = base / "exports/notebooklm-sources.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    return text


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="+")
    args = ap.parse_args(argv)
    for t in args.tickers:
        export(t)
        print(f"research/{t.upper()}/exports/notebooklm-sources.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
