#!/usr/bin/env python3
"""Backfill state snapshots so a company has multi-period state, without hindsight.

Two honest kinds of past state:

  --retrospective DATE
      Rebuilt today from data that was public on DATE: SEC facts filed <= DATE,
      the close on/before DATE, management statements / guidance issued <= DATE and
      promise outcomes resolved <= DATE. No thesis, action or valuation is invented:
      the snapshot carries `retrospective: true` and no recommendation.

  --from-git COMMIT --as-of DATE
      A review that really happened: thesis, valuation, monitoring and financial
      state files are taken from the given git commit (the research as recorded
      then); SEC history is rebuilt with the same DATE cutoff, and management data
      issued <= DATE is used. retrospective = false, with the commit in `note`.

Snapshots are written to research/<TICKER>/snapshots/<DATE>.json. Existing real
snapshots are never replaced by retrospective ones.
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_fundamental_history as bfh  # noqa: E402
import price_reaction  # noqa: E402
import research_state as rs  # noqa: E402
import state_diff  # noqa: E402


def _history_as_of(base: Path, as_of: str):
    facts = json.loads((base / "raw/companyfacts.json").read_text())
    ov = rs._read_json(base / "financials/tag-overrides.json", {}) or {}
    return bfh.build_history(facts, as_of=as_of, overrides=ov)


def retrospective(ticker: str, as_of: str, root: Path = ROOT) -> Path:
    base = rs.company_dir(ticker, root)
    prices = price_reaction.load_prices(base / "market/prices.csv")
    p = [x for x in prices if x["date"] <= as_of]
    snap = state_diff.build_snapshot(ticker, root, as_of, retrospective=True, history=_history_as_of(base, as_of),
                                     price=(p[-1]["date"], p[-1]["close"]) if p else None,
                                     note="retrospective = true: rebuilt from data public at this date")
    return state_diff.save_snapshot(ticker, snap, root)


def from_git(ticker: str, commit: str, as_of: str, root: Path = ROOT) -> Path:
    t = ticker.upper()
    base = rs.company_dir(t, root)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        data = subprocess.run(["git", "archive", commit, f"research/{t}"], cwd=root, capture_output=True,
                              check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp_root, filter="data")
        tb = tmp_root / "research" / t
        # public-at-date data that the old commit did not yet store
        for rel in ("management/statements.json", "management/guidance.json", "management/promises.json"):
            if (base / rel).exists():
                (tb / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(base / rel, tb / rel)
        hist = _history_as_of(base, as_of)
        (tb / "financials").mkdir(parents=True, exist_ok=True)
        (tb / "financials/history.json").write_text(json.dumps(hist))
        snap = state_diff.build_snapshot(t, tmp_root, as_of, history=hist,
                                         note=f"reconstructed from git {commit} (state recorded {as_of}); "
                                              f"SEC history and management data filtered to <= {as_of}")
    snap["retrospective"] = False
    return state_diff.save_snapshot(t, snap, root, overwrite=True)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--retrospective", action="append", default=[], metavar="DATE")
    ap.add_argument("--from-git", nargs=2, action="append", default=[], metavar=("COMMIT", "DATE"))
    ap.add_argument("--root", type=Path, default=ROOT)
    a = ap.parse_args(argv)
    for d in a.retrospective:
        print(retrospective(a.ticker, d, a.root))
    for commit, d in a.from_git:
        print(from_git(a.ticker, commit, d, a.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
