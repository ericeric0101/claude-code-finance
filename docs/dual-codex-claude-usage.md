# Using Codex and Claude Code on the same repo

## Shared by both

- `research/` — all company state and dated reports (single source of truth).
- `scripts/` — `research_state.py`, `price_reaction.py`, `recommendation.py`,
  acquisition and AAPL-specific normalization tools.
- `.claude/skills/` — every skill package, canonical location.
- `docs/` — policies, templates, schemas, this guide.
- `tests/`, `.env` (local, ignored), `docs/upstream-versions.json`.

## Only Codex

- `AGENTS.md` (instructions and tool-name mapping).
- `.agents/skills/` symlinks (discovery). Global `~/.codex/config.toml`.

## Only Claude Code

- `CLAUDE.md`, `.claude/commands/` (slash wrappers), native skill discovery,
  `allowed-tools` frontmatter, optional `scripts/claude` launcher.

## Canonical locations

| What | Where |
|---|---|
| Skills | `.claude/skills/<name>/` (Codex reaches them through `.agents/skills/<name>` symlinks) |
| Valuation engine | `.claude/skills/stock-analysis/scripts/valuation.py` (upstream, unmodified) |
| Decision helpers | `scripts/recommendation.py` |
| State tool | `scripts/research_state.py` |
| Data clients | `.claude/skills/finance-skill/scripts/` |
| Upstream mirror (do not edit) | `skills/finance-skill/` |

## Avoiding divergence

1. Never copy a skill folder; add a symlink in `.agents/skills/` for each new
   `.claude/skills/<name>` (a test enforces this).
2. Never edit upstream packages; `python3 scripts/check_setup.py` verifies hashes.
   Put custom behavior in project-owned skills (`my-equity-research`,
   `equity-research-orchestrator`, ...) or `docs/`.
3. Keep host-specific text in `AGENTS.md` / `CLAUDE.md` short; long procedures
   belong in skills both hosts read.
4. Write research through `research_state.py` so either host upserts the same
   history files; commit after each material update so git records who changed what.
5. Run `python3 -m unittest discover -s tests` before committing from either host.
