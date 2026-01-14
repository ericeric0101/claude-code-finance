---
name: finance-skill
description: Financial analysis capabilities including stock quotes, fundamentals, SEC filings, comparisons, and technicals. Auto-activates on financial queries.
allowed-tools: Bash, Read, Write, Glob, Grep, Task, WebFetch, WebSearch, AskUserQuestion
---

# Finance Skill

Financial analysis for investment research. Provides stock data, fundamental analysis, SEC filing analysis, peer comparisons, and technical analysis.

## Auto-Activation

Activate this skill when user:
- Asks about stock prices or quotes
- Mentions ticker symbols (AAPL, MSFT, GOOGL, etc.)
- Asks about company financials, earnings, or metrics
- Mentions SEC filings (10-K, 10-Q, 8-K, Form 4)
- Asks to compare companies
- Asks about technical indicators or chart patterns
- Uses financial terminology (P/E, ROE, EBITDA, etc.)

## Capabilities

| Capability | Purpose | See |
|------------|---------|-----|
| Research | Comprehensive company overview | capabilities/research.md |
| Fundamentals | Deep financial statement analysis | capabilities/fundamentals.md |
| Filings | SEC filing analysis | capabilities/filings.md |
| Compare | Side-by-side peer comparison | capabilities/compare.md |
| Technicals | Technical price analysis | capabilities/technicals.md |

## Guidelines

See `guidelines.md` for analysis principles, entity recognition, data validation, and citation requirements.

## Data Sources

Reference these API docs for implementation:
- `apis/alphavantage.md` - Market data, financials, technicals (25 req/day free tier)
- `apis/sec-edgar.md` - SEC filings (10 req/sec, no daily limit)
- `apis/yfinance.md` - Analyst data, holdings (Python library)

## Scripts

Python modules for data fetching and parsing (in `scripts/`):
- `alphavantage.py` - Alpha Vantage client with parsing
- `sec_edgar.py` - SEC EDGAR client with parsing
- `cache.py` - Caching infrastructure for API responses

Scripts auto-bootstrap dependencies via [uv](https://docs.astral.sh/uv/). Running a script directly (e.g., `python3 alphavantage.py AAPL quote`) will automatically set up a venv and install dependencies on first run.

For inline Python code, use `uv run`:
```bash
cd scripts/
uv run python -c "import yfinance as yf; print(yf.Ticker('AAPL').info)"
```

## Dependencies

Required:
- `uv` - Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Environment Variables

Required:
- `ALPHA_VANTAGE_API_KEY` - Get free key at alphavantage.co
- `SEC_EDGAR_USER_AGENT` - Your name and email for SEC API

## Natural Language Handling

When users ask financial questions:

1. **Stock quotes**: "What's Apple trading at?" → Fetch quote via Alpha Vantage
2. **Company research**: "Tell me about Microsoft" → Use research capability
3. **Comparisons**: "How does AMD compare to NVIDIA?" → Use compare capability
4. **Filings**: "What are Tesla's risk factors?" → Fetch 10-K, analyze Item 1A
5. **Technicals**: "Is GOOGL overbought?" → Use technicals capability

Always cite data sources and dates. Flag stale data (>1 day for quotes, >1 quarter for financials).

## Rate Limit Awareness

Alpha Vantage free tier: 25 requests/day. A full research analysis uses 5-7 requests.
- Cache aggressively
- Prefer SEC EDGAR for filing data (unlimited)
- Use yfinance for analyst/holder data (no API key needed)

## Context Management

Financial data fetches can be large (SEC filings, multi-company comparisons, historical data). To preserve main session context:

**Delegate to sub-agents:**
- API calls and data fetching
- Data exploration and extraction (e.g., parsing 10-K sections)
- Multi-company comparisons and cross-dataset analysis
- Any operation that returns verbose raw data

**Main session acts as orchestrator:**
- Interpret user intent
- Dispatch sub-agents for data gathering
- Synthesize summarized results from agents
- Present final analysis to user

**For complex analyses, use hierarchical delegation:**
```
Main Session (orchestrator)
├── Agent A: Fetch and summarize Company 1 data
├── Agent B: Fetch and summarize Company 2 data
├── Agent C: Fetch and summarize Company 3 data
└── (optional) Agent D: Compare summaries from A, B, C
```

Sub-agents should return concise summaries with key metrics, not raw API responses or full document text.
