# Codex → Claude migration audit

Audit date: 2026-10-12 (Asia/Taipei). Workspace:
`/Users/cheng-kaihuang/stock-deep-research`. Secret values were not printed.

## Pre-migration baseline

| Item | Finding |
|---|---|
| Branch / HEAD | `main` at `8f38adf Refine valuation and recommendation framework`, 1 commit ahead of `origin/main` |
| Remotes | `origin` = ericeric0101/claude-code-finance (fork); `upstream` = andrasp/claude-code-finance |
| Recent history | `86941f6` skills + AAPL pipeline → `abd77f2` Codex skill entries → `751b4fa` AAPL cashflow normalization → `a7542c2` labels / price ranges / event checks → `8f38adf` valuation and recommendation framework |
| Uncommitted (modified) | `scripts/recommendation.py` (adds `revenue_catch_up`, single-method map fixes), `tests/test_recommendation.py` (+2 tests). Kept as-is and committed with the migration because PL outputs depend on them; all 8 tests passed before any migration change. |
| Untracked | `research/PL/` (2026-10-11 deep dive + inputs/outputs), `research/PLTR/` (2026-10-11 report + inputs/outputs) |
| Generated research | `research/AAPL/` (report, 40+ JSON/markdown inputs and outputs), `research/PL/`, `research/PLTR/`; `research/AAPL/raw/` (16 MB filings) is git-ignored |
| Secrets | `.env` exists (mode 600) with `ALPHA_VANTAGE_API_KEY` and `SEC_EDGAR_USER_AGENT`; ignored by `.gitignore:1` (`.env`) and `.env.*` (except `.env.example`); not tracked by git |
| Other ignored local state | `.tools/` (230 MB local Claude CLI install), `.venv/`, `.cache/`, `uv.lock`, `__pycache__/`, `.claude/settings.local.json` |
| Codex config in repo | No `.codex/` directory. Codex uses `AGENTS.md` + `.agents/skills/` (three relative symlinks into `.claude/skills/`) |
| Codex config outside repo | `~/.codex/config.toml` has no project entry for this repo; its MCP servers (`node_repl`, `computer-use`, `codebase-memory-mcp`) are global, not repo-specific. Not modified. |
| Claude config | `CLAUDE.md` (short project rules), `.claude/skills/{finance-skill,stock-analysis,my-equity-research}`, no commands, hooks or settings files |
| Upstream integrity | `docs/upstream-versions.json` SHA-256 check: all 20 finance-skill and 61 stock-analysis files match upstream (no local modifications) |
| Reproducibility | `scripts/recommendation.py` regenerates `research/{AAPL,PL,PLTR}/recommendation-output.json` byte-identically |

## Component inventory

| Component | Current path | Origin | Purpose | Used by Codex? | Reusable by Claude? | Migration action | Risk |
|---|---|---|---|---|---|---|---|
| finance-skill (canonical) | `.claude/skills/finance-skill/` | andrasp/claude-code-finance @8870afd | SEC EDGAR, Alpha Vantage, yfinance clients | Yes (via symlink) | Yes, native | KEEP | Low |
| finance-skill upstream mirror | `skills/finance-skill/` | same upstream, tracked by the fork | Original upstream location; identical to canonical (excluding caches) | No | Not needed | REVIEW (kept to diff against `upstream` remote; not a second working copy) | Divergence if edited; do not edit |
| stock-analysis | `.claude/skills/stock-analysis/` | alirezarezvani/claude-skills @19392f7 | Framework, references, QA scripts | Yes (symlink) | Yes, native | KEEP | Low |
| valuation.py / ratios.py / score.py / verify_data.py / lint_report.py | `.claude/skills/stock-analysis/scripts/` | upstream, unmodified | Valuation engine and QA gates | Yes | Yes | REUSE | Low |
| my-equity-research | `.claude/skills/my-equity-research/` | project-owned | Decision layer, action labels, events screen | Yes | Yes | ADAPT (one-line pointer to orchestrator) | Low |
| Codex skill entries | `.agents/skills/*` | project | Codex discovery | Yes | n/a | SYMLINK (extended to 7 new skills) | Low |
| AGENTS.md | `AGENTS.md` | project | Codex instructions | Yes | Read-only reference | KEEP (+ new-skill pointer) | Low |
| CLAUDE.md | `CLAUDE.md` | project | Claude instructions | No | Yes | ADAPT (rewritten concise) | Low |
| recommendation.py | `scripts/recommendation.py` | project | Valuation map, reverse-DCF comparison, earnings / revenue catch-up | Yes | Yes | REUSE (uncommitted edits preserved) | Low |
| recommendation policy | `docs/recommendation-policy.md`, `docs/research-report-template.md` | project | Separates model value / expectations / map / action | Yes | Yes | KEEP | Low |
| SEC acquisition | `scripts/acquire_research.py` | project | Dated SEC submissions / facts via finance-skill | Yes | Yes | REUSE | Low |
| AAPL extract / normalize | `scripts/extract_aapl.py`, `scripts/normalize_aapl.py`, `scripts/run_valuation_checks.py` | project | AAPL-specific intake, cash-flow normalization, sensitivity | Yes | Yes | KEEP (company-specific, validated) | Medium if generalized |
| Setup check | `scripts/check_setup.py` | project | Upstream hash + CLI smoke + env check | Yes | Yes | KEEP (reports Codex host; still valid) | Low |
| Legacy Claude launcher | `scripts/claude` → `.tools/claude` | project | Local Claude CLI wrapper | No | Optional | KEEP / DEPRECATE in docs (Claude Code desktop/CLI used directly) | Low |
| Research prompts | `docs/research-prompts.md` | project | Prompt library incl. PL Deep Dive | Yes | Yes | KEEP | Low |
| Setup record | `docs/SETUP.md`, `docs/validation.json` | project | 15-step setup and validation history | Yes | Yes | KEEP (historical) | Low |
| AAPL research | `research/AAPL/` | 2026-10-11 run | Regression case | Yes | Yes | KEEP + add state layout | Low |
| PL research | `research/PL/` | 2026-10-11 run (untracked) | Regression case | Yes | Yes | KEEP + add state layout; commit | Low |
| PLTR research | `research/PLTR/` | 2026-10-11 run (untracked) | Report + recommendation I/O | Yes | Yes | KEEP; commit; state not yet initialized | Low |
| Tests | `tests/test_recommendation.py` | project | Policy and valuation regression | Yes | Yes | KEEP + add `tests/test_research_os.py` | Low |
| Codex MCP config | `~/.codex/config.toml` (global) | user | Global Codex MCP servers | Yes | No | REVIEW (untouched; nothing repo-specific) | None |
| HOOD example PDF | `examples/` | upstream | Upstream example | No | n/a | KEEP | None |

No other copies of finance-skill or stock-analysis exist in the workspace.
