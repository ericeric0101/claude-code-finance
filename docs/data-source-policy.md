# Data source policy — US equities

| Tier | Sources | Use |
|---|---|---|
| 1 | SEC EDGAR (10-K, 10-Q, 8-K, proxy, XBRL company facts), company Investor Relations, earnings releases, official guidance | Financial facts, guidance, management statements, events |
| 2 | US Treasury, Federal Reserve / FRED, BLS / BEA and other official statistics | Rates, macro inputs for discount rates and event screens |
| 3 | Alpha Vantage or another reliable market-data provider; exchange data where available | Prices, volumes, corporate-action-aware series |
| 4 | yfinance and secondary aggregators (Yahoo, StockAnalysis, FT tearsheets) | Convenience, prototyping and cross-checks only |

Rules:

1. A lower tier never silently overrides a higher tier. If an aggregator
   disagrees with a filing, the filing wins and the discrepancy is recorded.
2. Every stored datapoint records **source**, **retrieval date**, **reporting
   period** and **classification** (Fact / Calculation / Assumption /
   Interpretation). Prices also record trading date and exchange.
3. Consensus estimates are never fabricated. If consensus is not available from a
   cited source, say so; analyst assumptions are labelled as assumptions.
4. An unavailable source is a disclosed gap, not permission to use remembered numbers.
5. Prefer local evidence: do not call an API when `research/<TICKER>/` already
   holds the dated data needed. Network acquisition goes through `finance-skill`
   (`uv run --project .claude/skills/finance-skill/scripts ...`) so caching and
   the SEC User-Agent are applied.
6. Unknown tickers require a verified numeric CIK before SEC calls.
7. API keys live in `.env` only; never in reports, state files, commands or git.
8. Headlines are discovery leads; verify material facts with the issuer,
   regulator, central bank or official statistics before they enter state.
