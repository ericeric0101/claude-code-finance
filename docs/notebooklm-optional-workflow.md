# NotebookLM — optional human-reading layer

NotebookLM is **not** a dependency. No skill, script or test requires it.

| NotebookLM (optional) | Git repository (canonical) |
|---|---|
| Exploring long documents (10-K, proxy, transcripts) | Structured research state in `research/<TICKER>/` |
| Source-grounded Q&A while reading | Version history of every judgment (git) |
| Reading earnings-call transcripts | Machine-readable data (JSON / YAML / CSV) |
| | Valuation logic and scripts |
| | Tests and reproducibility |

Suggested use:

1. Upload primary documents (the filings listed in `evidence/sources.json`) to a
   notebook per company for reading and Q&A.
2. When a reading session produces a finding, record it in the repo with the
   primary-source citation (filing URL and section), not the NotebookLM answer
   as the source.
3. Do not copy state files into NotebookLM as a second source of truth; if you
   want the current view there, export `research_state.py status TICKER` as a
   dated, read-only note.
