# Filing Analysis Workflow

A structured approach to analyzing SEC filings for investment insights.

## When to Use

- Deep dive into annual reports (10-K)
- Quarterly update analysis (10-Q)
- Material event assessment (8-K)
- Tracking insider activity (Form 4)
- Institutional ownership research (13-F)

## Workflow Steps

### Phase 1: Filing Identification

**Objective:** Locate and access the relevant filing.

1. Determine CIK for the company (see `apis/sec-edgar.md`)
2. Fetch recent submissions
3. Identify the specific filing needed
4. Access the filing documents

### Phase 2: 10-K Annual Report Analysis

**Objective:** Extract key insights from annual report.

**Business Section (Item 1):**
- Business description and history
- Products and services
- Customers and markets
- Competition
- Seasonality
- Intellectual property

**Risk Factors (Item 1A):**
- Categorize risks: operational, financial, regulatory, market
- Identify new risks vs prior year
- Assess severity and likelihood
- Note company-specific vs industry-wide risks

**Properties (Item 2):**
- Key facilities and locations
- Owned vs leased
- Capacity and utilization

**Legal Proceedings (Item 3):**
- Ongoing litigation
- Regulatory actions
- Material settlements

**MD&A (Item 7):**
- Management's view of results
- Key performance drivers
- Known trends and uncertainties
- Liquidity and capital resources
- Critical accounting policies

**Financial Statements (Item 8):**
- Auditor's opinion (clean, qualified, adverse)
- Significant accounting policies
- Footnote disclosures
- Off-balance sheet arrangements

**Controls (Item 9A):**
- Internal control assessment
- Material weaknesses
- Changes in controls

### Phase 3: 10-Q Quarterly Report Analysis

**Objective:** Track changes since last report.

Focus on:
- Financial performance vs prior quarter and year-ago
- MD&A updates and new developments
- Changes in risk factors
- Legal proceedings updates
- Any material changes in controls

### Phase 4: 8-K Material Event Analysis

**Objective:** Assess significance of reported events.

**Common 8-K Items:**

| Item | Type | Significance |
|------|------|--------------|
| 1.01 | Material Agreement | Contract wins, partnerships |
| 1.02 | Agreement Termination | Loss of key customer/supplier |
| 2.01 | Asset Changes | Acquisitions, divestitures |
| 2.02 | Results of Operations | Earnings announcement |
| 2.05 | Exit Activities | Restructuring, layoffs |
| 2.06 | Impairments | Asset writedowns |
| 4.01 | Auditor Changes | Red flag if unexpected |
| 5.02 | Director/Officer Changes | Management transitions |
| 7.01 | Reg FD Disclosure | Investor presentations |
| 8.01 | Other Events | Various material items |

**For each 8-K, assess:**
- Materiality to business
- Financial impact
- Strategic implications
- Market reaction appropriateness

### Phase 5: Form 4 Insider Transaction Analysis

**Objective:** Gauge insider sentiment.

Track:
- Who is trading (CEO, CFO, Directors, etc.)
- Transaction type (buy, sell, exercise)
- Transaction size (absolute and % of holdings)
- Timing (regular schedule vs discretionary)
- Pattern over time

**Interpretation:**
- Insider buying = generally positive signal
- Insider selling = context matters (planned sales, diversification)
- Cluster buying = strong positive signal
- Large discretionary sales = potential concern

### Phase 6: 13-F Institutional Holdings

**Objective:** Track smart money positioning.

Analyze:
- Top holders and position sizes
- New positions initiated
- Positions closed
- Position changes (increase/decrease)
- Quality of holders (hedge funds, mutual funds, index funds)

## Output Template

### 10-K Analysis
```
## {Company} FY{Year} 10-K Analysis

### Filing Details
- Filed: {date}
- Fiscal Year End: {date}
- Accession: {number}

### Business Summary
[Key points from Item 1]

### Risk Factor Highlights
**New Risks:**
1. [Risk]
2. [Risk]

**Elevated Risks:**
1. [Risk]
2. [Risk]

### MD&A Key Points
- Revenue drivers: [summary]
- Margin factors: [summary]
- Outlook commentary: [summary]

### Financial Statement Notes
- Auditor: {firm}, {opinion type}
- Notable accounting policies: [list]
- Key footnote items: [list]

### Red Flags
[Any concerning items identified]

### Investment Implications
[What this means for the thesis]

---
Source: SEC EDGAR {accession}
Link: {url}
```

### 8-K Analysis
```
## {Company} 8-K Analysis: {Event Type}

### Filing Details
- Filed: {date}
- Items: {list}

### Event Summary
[What happened]

### Financial Impact
[Quantified impact if available]

### Strategic Implications
[What this means for the company]

### Market Reaction
[How stock responded]

### Assessment
[Bullish/Bearish/Neutral for investment thesis]

---
Source: SEC EDGAR {accession}
```

### Insider Activity
```
## {Company} Insider Transaction Analysis

### Recent Transactions
| Date | Insider | Role | Type | Shares | Price | Value |
|------|---------|------|------|--------|-------|-------|
| ... | ... | ... | ... | ... | ... | ... |

### 90-Day Summary
- Net Insider Position: {Buying/Selling}
- Total Bought: ${X}
- Total Sold: ${X}
- Net: ${X}

### Notable Patterns
[Observations about insider behavior]

### Signal Assessment
[What insider activity suggests]

---
Source: SEC EDGAR Form 4 Filings
```
