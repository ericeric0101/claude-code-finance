# Codex ↔ Claude compatibility map

Goal: one canonical implementation, two hosts. Nothing Codex uses was removed.

## A. Portable (shared by both hosts)

| Asset | Path |
|---|---|
| Python tools | `scripts/*.py`, `.claude/skills/*/scripts/*.py` |
| Upstream skill packages (markdown + scripts) | `.claude/skills/finance-skill/`, `.claude/skills/stock-analysis/` |
| Project skills (plain markdown instructions) | `.claude/skills/<name>/SKILL.md` |
| Schemas and state | `research/<TICKER>/**` (JSON, YAML, CSV, markdown) |
| Policies and templates | `docs/recommendation-policy.md`, `docs/research-report-template.md`, `docs/data-source-policy.md` |
| Upstream manifest | `docs/upstream-versions.json` |
| Tests | `tests/` (stdlib `unittest`) |
| Credentials | `.env` (ignored), `.env.example` |

## B. Codex-specific

| Asset | Notes |
|---|---|
| `AGENTS.md` | Codex instruction entry; maps Claude tool names (Bash, Read, WebFetch, AskUserQuestion) to Codex operations; states `allowed-tools` is upstream metadata |
| `.agents/skills/*` | Relative symlinks to `.claude/skills/*` for Codex skill discovery |
| `scripts/check_setup.py` "Host: Codex desktop" line | Informational; checks resolve through `.agents/skills` |
| Script paths using `.agents/skills/...` (`acquire_research.py`, `run_valuation_checks.py`, `check_setup.py`, tests) | Resolve to the same files via symlink; left unchanged |

There is no `.codex/` folder, no Codex slash-command file and no repo-specific
Codex MCP config. Global `~/.codex/config.toml` was not modified.

## C. Claude-specific

| Asset | Notes |
|---|---|
| `CLAUDE.md` | Concise project rules |
| `.claude/skills/<name>/SKILL.md` | Native skill discovery (`name`, `description` frontmatter) |
| `.claude/commands/{init,update,deep,watch}-stock.md`, `monthly-research.md` | Thin wrappers so `/init-stock PL` etc. work; each delegates to `equity-research-orchestrator` |
| `allowed-tools` in finance-skill frontmatter | Honored by Claude; ignored by Codex |
| `scripts/claude` + `.tools/claude` | Legacy local CLI launcher; optional |

No hooks, subagents or `.claude/settings.json` were added: nothing in the
workflow needs them, and avoiding them keeps behavior identical across hosts.

## Equivalences

| Workflow | Claude Code | Codex |
|---|---|---|
| Initialize | `/init-stock PL` | "Use equity-research-orchestrator to INIT PL" |
| Update | `/update-stock PL` | "... UPDATE PL" |
| Deep dive | `/deep-stock PL` | "... DEEP PL" |
| Watch | `/watch-stock PL` | "... WATCH PL" or `python3 scripts/research_state.py status PL` |
| Monthly | `/monthly-research` | "Run research-review" |

Both hosts read and write the same `research/` state, so a Codex update and a
Claude update land in the same files and the same git history.
