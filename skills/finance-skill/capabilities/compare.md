# Compare Capability

Side-by-side comparison of multiple companies (2-5 tickers).

### 1. Company Profiles
Fetch overview for each company from Alpha Vantage (see `apis/alphavantage.md`):
- Verify all companies are in comparable industries
- Note any sector/industry differences

### 2. Valuation Comparison

| Metric | {Ticker1} | {Ticker2} | {Ticker3} | Median |
|--------|-----------|-----------|-----------|--------|
| Market Cap | | | | |
| Enterprise Value | | | | |
| P/E (TTM) | | | | |
| P/E (Forward) | | | | |
| P/S | | | | |
| P/B | | | | |
| EV/EBITDA | | | | |
| PEG Ratio | | | | |

Highlight: Cheapest/most expensive on each metric.

### 3. Growth Comparison

| Metric | {Ticker1} | {Ticker2} | {Ticker3} | Median |
|--------|-----------|-----------|-----------|--------|
| Revenue Growth (YoY) | | | | |
| EPS Growth (YoY) | | | | |
| Revenue Growth (3Y CAGR) | | | | |
| EPS Growth (3Y CAGR) | | | | |

### 4. Profitability Comparison

| Metric | {Ticker1} | {Ticker2} | {Ticker3} | Median |
|--------|-----------|-----------|-----------|--------|
| Gross Margin | | | | |
| Operating Margin | | | | |
| Net Margin | | | | |
| ROE | | | | |
| ROA | | | | |
| ROIC | | | | |

### 5. Financial Health Comparison

| Metric | {Ticker1} | {Ticker2} | {Ticker3} | Median |
|--------|-----------|-----------|-----------|--------|
| Current Ratio | | | | |
| Debt/Equity | | | | |
| Interest Coverage | | | | |
| Cash/Share | | | | |

### 6. Size & Scale

| Metric | {Ticker1} | {Ticker2} | {Ticker3} |
|--------|-----------|-----------|-----------|
| Revenue (TTM) | | | |
| Net Income (TTM) | | | |
| Employees | | | |
| Market Cap | | | |

### 7. Dividend Comparison (if applicable)

| Metric | {Ticker1} | {Ticker2} | {Ticker3} |
|--------|-----------|-----------|-----------|
| Dividend Yield | | | |
| Payout Ratio | | | |
| Dividend Growth (5Y) | | | |

### 8. Analyst Sentiment
Use yfinance (see `apis/yfinance.md`) for each:
- Consensus rating
- Price target upside/downside

## Output Format

```
## Comparative Analysis: {Ticker1} vs {Ticker2} vs {Ticker3}

### Company Overview
| Company | Sector | Industry | Description |
|---------|--------|----------|-------------|
| ... | ... | ... | ... |

### Valuation Comparison
[Table with highlighting for best/worst]

### Growth Comparison
[Table with highlighting]

### Profitability Comparison
[Table with highlighting]

### Financial Health
[Table with highlighting]

### Summary

**Most Attractive Valuation:** {Ticker} - [reason]
**Best Growth Profile:** {Ticker} - [reason]
**Strongest Financials:** {Ticker} - [reason]
**Highest Risk:** {Ticker} - [reason]

### Key Differentiators
- {Ticker1}: [unique strength/weakness]
- {Ticker2}: [unique strength/weakness]
- {Ticker3}: [unique strength/weakness]

---
Sources: Alpha Vantage, yfinance, as of {date}
```

## Rate Limit Awareness

This skill uses 1-2 Alpha Vantage requests per company.
- 2 companies: ~4 requests
- 3 companies: ~6 requests
- 5 companies: ~10 requests

With 25/day limit, use sparingly. Consider caching.
