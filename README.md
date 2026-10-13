> **使用手冊（從這裡開始）：[docs/USER-GUIDE.md](docs/USER-GUIDE.md)**
>
> This fork is a dual **Codex / Claude Code** US equity continuous research system ([architecture](docs/us-equity-research-os.md), [dual usage](docs/dual-codex-claude-usage.md)).
> Codex entry points: `AGENTS.md` and `.agents/skills/`. The original upstream README follows below.
> See [local setup and 15-step status](docs/SETUP.md), [research prompts](docs/research-prompts.md), and [the AAPL test report](research/AAPL/AAPL-analysis-2026-10-11.md).

# Claude Code Finance

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Claude Code isn't just a software development agent. It's a general-purpose agent that can be extended with domain specializations. This repo adds financial analysis capabilities to Claude Code.

Instead of building a standalone financial agent that duplicates what Claude Code already does, this extends Claude Code itself. Markdown for progressive disclosure, Python scripts for the hard parts (auth, caching, parsing), and guidance that teaches the agent when to call utilities vs generate new code. No infrastructure to deploy. The agent becomes genuinely skilled at finance while remaining composable with everything else Claude Code can do.

## What It Does

Once installed, ask financial questions naturally:

- "What's Apple trading at?"
- "Show me Microsoft's key financial metrics"
- "Compare profitability across major automakers"
- "What are the risk factors in Tesla's latest 10-K?"
- "Is NVIDIA overbought based on technicals?"

The skill auto-activates when it detects financial queries and provides structured analysis using free-tier data sources.

## How It Works

The skill balances three layers:

### Markdown for progressive disclosure

SKILL.md loads only when triggered. Capability docs (research.md, filings.md, etc.) provide structured guidance for each analysis type. The agent reads these on-demand, keeping context lightweight.

### Python scripts for data access

Pre-built utilities handle the messy parts: API authentication, caching, rate limits, and response parsing. The agent calls these directly rather than generating HTTP code from scratch each time.

### Markdown instructions for code generation

API docs explain how to use the scripts (`from sec_edgar import get_latest_filing`) and when to generate new code. The agent reads the docs, then writes code that calls the utilities.

The agent doesn't need to figure out SEC EDGAR's User-Agent requirements or Alpha Vantage's response format. It just imports the module and calls functions. It can still generate custom analysis code when needed.

## Example: Full Company Analysis

Here's a real analysis generated through natural conversation:

> "Do a full financial analysis of HOOD and create a PDF report"

**[View the full PDF report](examples/HOOD_Financial_Analysis_Report.pdf)**

The 13-page report includes:
- Executive summary with key metrics
- Business overview and revenue breakdown
- Financial performance (revenue trajectory, profitability turnaround)
- Platform metrics and KPIs
- Valuation analysis with peer comparison (SCHW, IBKR)
- Balance sheet health
- Growth drivers and strategic initiatives
- Risk factors (regulatory, business, financial)
- Technical analysis (support/resistance, moving averages)
- Analyst sentiment and institutional holders
- Investment thesis (bull/bear cases)

All data was pulled live from SEC EDGAR, Alpha Vantage, and Yahoo Finance, then synthesized into a structured report—entirely through natural conversation.

## Structure

```
claude-code-finance/
├── README.md
├── examples/
│   └── HOOD_Financial_Analysis_Report.pdf  # Sample output
└── skills/finance-skill/
    ├── SKILL.md              # Skill definition (auto-activation triggers)
    ├── guidelines.md         # Analysis principles, entity recognition, citations
    ├── apis/                 # API reference docs
    │   ├── alphavantage.md
    │   ├── sec-edgar.md
    │   └── yfinance.md
    ├── capabilities/         # Analysis capabilities
    │   ├── research.md       # Company research
    │   ├── fundamentals.md   # Financial statement analysis
    │   ├── filings.md        # SEC filing analysis
    │   ├── compare.md        # Peer comparison
    │   └── technicals.md     # Technical analysis
    ├── scripts/              # Python utilities
    │   ├── pyproject.toml    # Dependencies (managed by uv)
    │   ├── venv.py           # Auto-bootstrap module
    │   ├── env.py            # Environment variable loading
    │   ├── cache.py          # Caching infrastructure
    │   ├── alphavantage.py   # Alpha Vantage client
    │   └── sec_edgar.py      # SEC EDGAR client
    └── workflows/            # Structured analysis guides
        ├── fundamental-analysis.md
        ├── comparative-analysis.md
        ├── earnings-analysis.md
        └── filing-analysis.md
```

## Data Sources

| Source | Data | Rate Limit | Key Required |
|--------|------|------------|--------------|
| [Alpha Vantage](https://www.alphavantage.co/) | Quotes, financials, technicals | 25/day | Yes |
| [SEC EDGAR](https://www.sec.gov/edgar) | Filings, insider trades | 10/sec | No |
| [yfinance](https://github.com/ranaroussi/yfinance) | Analyst data, holders | Unlimited* | No |

*yfinance is unofficial and may break.

## Scripts

The skill calls these Python scripts automatically, but you can also run them directly. Scripts auto-bootstrap dependencies via uv on first run:

```bash
cd skills/finance-skill/scripts

# SEC EDGAR - unlimited, parses 10-K financials
python3 sec_edgar.py AAPL 10-K

# Alpha Vantage - 25/day, company metrics
python3 alphavantage.py AAPL overview

# yfinance - via uv run for inline code
uv run python -c "import yfinance as yf; print(yf.Ticker('AAPL').info['currentPrice'])"

# Cache management
python3 cache.py stats
python3 cache.py clear
```

## Caching

Alpha Vantage free tier: 25 requests/day. The cache preserves them:

| Data Type | TTL |
|-----------|-----|
| Company Overview | 7 days |
| Financial Statements | 24 hours |
| Stock Quotes | 24 hours |
| Technical Indicators | 1 hour |
| News | 30 minutes |

SEC EDGAR has no daily limit (10 req/sec).

## Hierarchical Delegation

Financial data can be large. A 10-K filing is hundreds of pages. A multi-company comparison pulls data from dozens of API calls. Loading this raw data into the main conversation burns context and degrades response quality.

The skill is designed for hierarchical delegation:

```
Main Session (orchestrator)
├── Agent: Fetch Tesla financials → returns summary
├── Agent: Fetch Ford financials → returns summary
├── Agent: Fetch GM financials → returns summary
└── Main Session: Synthesize into comparison table
```

**The main session orchestrates.** It interprets user intent, dispatches sub-agents, and synthesizes their summaries into a final response.

**Sub-agents handle data.** They fetch from APIs, parse large documents, extract relevant sections, and return concise summaries—not raw data.

**For complex analyses, chain agents.** A first layer gathers data, a second layer compares or analyzes, and the main session presents results.

This pattern keeps the main conversation focused on the user while heavy data processing happens in isolated agent contexts that don't pollute the primary thread.

## Limitations

- **End-of-day quotes.** Alpha Vantage free tier, not real-time
- **Rate limited.** Heavy analysis may exhaust daily quota
- **US-focused.** International coverage limited on free tiers
- **No analyst estimates.** Consensus estimates require paid sources

## Installation

### 1. Install uv

Scripts use [uv](https://docs.astral.sh/uv/) for dependency management. Install it first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or via Homebrew on macOS:

```bash
brew install uv
```

### 2. Clone and symlink

```bash
git clone https://github.com/andrasp/claude-code-finance.git
```

**User-level install** (available in all projects):

```bash
ln -s /path/to/claude-code-finance/skills/finance-skill ~/.claude/skills/finance-skill
```

**— OR —**

**Project-level install** (available only in this project):

```bash
ln -s /path/to/claude-code-finance/skills/finance-skill .claude/skills/finance-skill
```

### 3. Set environment variables

Create a `.env` file in your project root:

```
ALPHA_VANTAGE_API_KEY=your_key_here
SEC_EDGAR_USER_AGENT=YourName your_email@example.com
```

The scripts automatically load `.env` from the current working directory, or fall back to `~/.env`.

- Get Alpha Vantage key: https://www.alphavantage.co/support/#api-key
- SEC EDGAR just needs your identity (no registration)

## License

MIT License - use however you want.
