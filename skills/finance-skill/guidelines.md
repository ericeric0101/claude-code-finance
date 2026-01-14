# Financial Analysis Guidelines

## Entity Recognition

When processing financial queries, extract and validate:

**Ticker Symbols:**
- US stocks: 1-5 uppercase letters (AAPL, MSFT, GOOGL)
- Validate against known exchanges before API calls
- Handle common variations (BRK.B vs BRK-B)

**Dates & Periods:**
- Fiscal years: FY2024, FY24
- Quarters: Q1 2024, 1Q24, Q1'24
- Relative: TTM (trailing twelve months), YTD, MRQ (most recent quarter)

**Financial Metrics:**
- Valuation: P/E, P/B, P/S, EV/EBITDA, PEG
- Profitability: ROE, ROA, ROIC, gross margin, operating margin, net margin
- Liquidity: Current ratio, quick ratio, cash ratio
- Leverage: Debt/Equity, interest coverage, debt/EBITDA

## Analysis Principles

**Fundamental Analysis:**
- Always consider trends over multiple periods (3-5 years)
- Compare metrics to industry benchmarks
- Look for consistency between income statement, balance sheet, and cash flow
- Identify red flags: revenue/earnings divergence, working capital issues, debt levels

**Comparative Analysis:**
- Use peer companies from same sector/industry
- Normalize by market cap or revenue where appropriate
- Account for fiscal year-end differences
- Consider growth rates, not just absolute values

**Technical Analysis:**
- Combine multiple indicators for confirmation
- Consider volume alongside price movements
- Identify support/resistance from historical price action
- Note trend direction before interpreting oscillators

## Web Research

Web research can supplement official data sources but requires careful handling.

**Appropriate uses:**
- Discovering recent news to verify via official sources
- Understanding market narrative and sentiment
- Finding leads to investigate with official data
- Context on industry trends or competitive dynamics

**Never use web sources for:**
- Financial figures (use SEC filings or Alpha Vantage)
- Material facts about a company (verify via SEC filings)
- Investment conclusions

**Source hierarchy (most to least trustworthy):**
1. SEC EDGAR filings (official, legally required disclosures)
2. Company investor relations / press releases
3. Alpha Vantage / market data APIs
4. Major financial news (Reuters, Bloomberg, WSJ)
5. Analyst reports from reputable firms
6. General news and commentary
7. Blogs, forums, social media (treat as sentiment only)

**When using web information:**
- Always label as "per [source]" or "reportedly"
- Distinguish between confirmed facts and claims/speculation
- Cross-reference material claims against official sources
- Note the date - web info goes stale quickly
- Be skeptical of numbers not from official filings

**Red flags to watch for:**
- Precise financial figures without SEC filing citation
- "Insider" information or rumors
- Highly bullish/bearish commentary without substantiation
- AI-generated content rehashing other sources
- Outdated information presented as current

## Data Validation

Before presenting financial data:
- Verify data freshness (check report dates)
- Cross-reference key figures when possible
- Flag stale data (>1 quarter old for financials)
- Handle missing data gracefully - state what's unavailable

## Citation Requirements

Always cite data sources:
- "Source: Alpha Vantage, as of {date}"
- "Source: SEC EDGAR Filing {form_type}, {filing_date}"
- Include links to original SEC filings when referencing them

## Date & Time

For date-sensitive operations (data freshness, filing dates, earnings dates), obtain the current local date/time using system tools:

```bash
date "+%Y-%m-%d %H:%M:%S"
```

or via Python:

```python
from datetime import datetime
print(datetime.now().strftime("%Y-%m-%d"))
```

Use this to:
- Validate data freshness
- Calculate time since last filing
- Determine relevant fiscal periods
- Set appropriate date ranges for API calls

## Environment Variables

Required for financial data access:
```
ALPHA_VANTAGE_API_KEY=your_key_here
SEC_EDGAR_USER_AGENT=YourName your_email@example.com
```

The SEC EDGAR API requires a User-Agent header identifying the requester. Use your name and email.
