# Fundamentals Capability

Deep dive into a company's financial statements with trend analysis.

### 1. Income Statement Analysis
Fetch income statement from Alpha Vantage (see `apis/alphavantage.md`):

**Revenue Analysis:**
- Revenue trend (3-5 years)
- Year-over-year growth rates
- Revenue concentration concerns (if known)

**Profitability Analysis:**
- Gross margin trend
- Operating margin trend
- Net margin trend
- Identify margin expansion/compression

**Earnings Quality:**
- EPS growth vs revenue growth
- Operating income vs net income consistency
- One-time items or adjustments

### 2. Balance Sheet Analysis
Fetch balance sheet:

**Asset Quality:**
- Total assets trend
- Cash and equivalents
- Accounts receivable growth vs revenue growth
- Inventory trends (for applicable companies)

**Liability Structure:**
- Short-term vs long-term debt
- Debt maturity schedule (if available)
- Accounts payable trends

**Equity Position:**
- Shareholders' equity trend
- Retained earnings growth
- Book value per share

### 3. Cash Flow Analysis
Fetch cash flow statement:

**Operating Cash Flow:**
- OCF trend
- OCF vs Net Income (quality indicator)
- Working capital changes

**Investing Activities:**
- Capital expenditures
- CapEx as % of revenue
- Acquisitions or divestitures

**Financing Activities:**
- Debt issuance/repayment
- Share buybacks
- Dividend payments

### 4. Key Ratios & Metrics

**Profitability:**
| Metric | Current | Prior Year | Trend |
|--------|---------|------------|-------|
| Gross Margin | | | |
| Operating Margin | | | |
| Net Margin | | | |
| ROE | | | |
| ROA | | | |
| ROIC | | | |

**Liquidity:**
| Metric | Current | Prior Year | Trend |
|--------|---------|------------|-------|
| Current Ratio | | | |
| Quick Ratio | | | |
| Cash Ratio | | | |

**Leverage:**
| Metric | Current | Prior Year | Trend |
|--------|---------|------------|-------|
| Debt/Equity | | | |
| Debt/EBITDA | | | |
| Interest Coverage | | | |

**Efficiency:**
| Metric | Current | Prior Year | Trend |
|--------|---------|------------|-------|
| Asset Turnover | | | |
| Inventory Turnover | | | |
| Days Sales Outstanding | | | |

### 5. Red Flags Check

Look for warning signs:
- Revenue growing faster than cash flow
- Increasing receivables as % of revenue
- Declining margins
- Rising debt levels
- Negative operating cash flow
- Large discrepancies between GAAP and non-GAAP earnings

## Output Format

```
## {Company Name} ({TICKER}) Fundamental Analysis

### Executive Summary
[2-3 sentence overview of financial health]

### Income Statement Trends
[Revenue and profitability analysis with tables]

### Balance Sheet Health
[Asset, liability, equity analysis]

### Cash Flow Quality
[OCF analysis, free cash flow calculation]

### Key Ratios
[Ratio tables with trend indicators]

### Concerns & Red Flags
[Any warning signs identified]

### Strengths
[Positive financial attributes]

---
Sources: Alpha Vantage, as of {date}
```

## Rate Limit Awareness

This skill uses 3-4 Alpha Vantage requests (overview, income, balance, cash flow).
