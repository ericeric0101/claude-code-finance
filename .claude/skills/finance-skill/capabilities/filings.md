# Filings Capability

Analyze SEC filings for a company.

## Recent Filings Overview

1. Fetch company submissions from SEC EDGAR (see `apis/sec-edgar.md`)
2. List recent filings (last 10-20):
   - Form type
   - Filing date
   - Brief description

### 10-K Analysis (Annual Report)

When `10-K` is specified:

1. Locate most recent 10-K filing
2. Analyze key sections:

**Business (Item 1):**
- Business description
- Key products/services
- Competitive landscape

**Risk Factors (Item 1A):**
- Top 5-10 risk factors
- New risks vs prior year
- Industry-specific risks

**MD&A (Item 7):**
- Management's view of performance
- Key drivers and challenges
- Forward-looking statements

**Financial Statements (Item 8):**
- Auditor opinion
- Any qualifications or concerns

### 10-Q Analysis (Quarterly Report)

When `10-Q` is specified:

1. Locate most recent 10-Q filing
2. Focus on:
   - Quarterly financial performance
   - MD&A updates
   - New risk factors
   - Legal proceedings updates

### 8-K Analysis (Material Events)

When `8-K` is specified:

1. Fetch recent 8-K filings (last 5-10)
2. Categorize by item type:
   - Earnings announcements (Item 2.02)
   - Material agreements (Item 1.01)
   - Executive changes (Item 5.02)
   - Other material events
3. Summarize key events

### Form 4 Analysis (Insider Transactions)

When `4` is specified:

1. Fetch recent Form 4 filings
2. Analyze insider trading patterns:
   - Who is buying/selling
   - Transaction sizes
   - Relationship to company (CEO, CFO, Director, etc.)
   - Net insider sentiment (buying vs selling)

## Output Format

### For Recent Filings Overview:
```
## {Company Name} ({TICKER}) Recent SEC Filings

| Date | Form | Description |
|------|------|-------------|
| ... | ... | ... |

### Notable Recent Filings
[Highlight any significant filings]
```

### For 10-K/10-Q:
```
## {Company Name} ({TICKER}) {Form Type} Analysis
### Filed: {date}

### Business Overview
[Summary from Item 1]

### Key Risk Factors
1. [Risk 1]
2. [Risk 2]
...

### Management Discussion Highlights
[Key points from MD&A]

### Financial Statement Notes
[Notable items from financials]

---
Source: SEC EDGAR Filing {accession_number}
Link: {url_to_filing}
```

### For 8-K:
```
## {Company Name} ({TICKER}) Recent Material Events

### {Date} - {Item Type}
[Event summary]

### {Date} - {Item Type}
[Event summary]

---
Source: SEC EDGAR
```

### For Form 4:
```
## {Company Name} ({TICKER}) Insider Transactions

### Recent Transactions
| Date | Insider | Title | Type | Shares | Price |
|------|---------|-------|------|--------|-------|
| ... | ... | ... | ... | ... | ... |

### Net Insider Sentiment
[Summary: Net buying/selling over period]

---
Source: SEC EDGAR Form 4 Filings
```

## Rate Limit Awareness

SEC EDGAR has no daily limit (10 req/sec). This skill can be used freely.
Include User-Agent header with requests.
