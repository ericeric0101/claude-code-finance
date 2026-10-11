# Research Capability

Comprehensive company research providing a complete overview.

### 1. Company Profile
Fetch company overview from Alpha Vantage (see `apis/alphavantage.md`):
- Company description and business summary
- Sector and industry classification
- Market capitalization
- Key executives

### 2. Current Valuation
From the same overview endpoint:
- Current stock price
- P/E ratio (trailing and forward if available)
- Price-to-book, Price-to-sales
- Dividend yield
- 52-week range

### 3. Recent Financial Performance
Fetch latest income statement:
- Revenue and revenue growth
- Gross margin, operating margin, net margin
- EPS and EPS growth

### 4. Financial Health
Fetch latest balance sheet:
- Total assets, total liabilities
- Cash position
- Debt levels and debt/equity ratio
- Current ratio

### 5. Recent News
Fetch news sentiment:
- Top 3-5 recent news items
- Overall sentiment (bullish/bearish/neutral)

### 6. SEC Filings (Optional)
If relevant, check recent 8-K filings for material events (see `apis/sec-edgar.md`).

### 7. Analyst Sentiment
Use yfinance to get (see `apis/yfinance.md`):
- Recent analyst recommendations
- Price target range

## Output Format

Present findings in a structured format:

```
## {Company Name} ({TICKER}) Research Summary

### Company Overview
[Description, sector, industry]

### Valuation Snapshot
| Metric | Value |
|--------|-------|
| Price | $XXX |
| Market Cap | $XXB |
| P/E | XX.X |
| ...

### Financial Performance (TTM)
[Revenue, margins, EPS with YoY comparisons]

### Financial Health
[Balance sheet highlights, debt levels]

### Recent Developments
[News summary, any material 8-K events]

### Analyst Sentiment
[Recommendation summary, price targets]

---
Sources: [List sources with dates]
```

## Rate Limit Awareness

This skill uses ~5-7 Alpha Vantage requests. With 25/day limit:
- Can run ~3-4 full research reports per day
- Consider caching results for repeat queries
