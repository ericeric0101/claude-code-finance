# Comparative Analysis Workflow

A structured approach to comparing multiple companies to identify relative value.

## When to Use

- Choosing between similar investment opportunities
- Understanding competitive positioning
- Sector/industry analysis
- Identifying best-in-class operators

## Workflow Steps

### Phase 1: Define the Comparison Set

**Objective:** Select appropriate peer companies.

1. Start with the primary company of interest
2. Identify peers based on:
   - Same industry/sector
   - Similar business model
   - Comparable market cap (within 2-3x)
   - Geographic overlap

**Guidelines:**
- 3-5 companies is ideal
- Too many dilutes the analysis
- Ensure comparability (don't compare AAPL to a small-cap tech)

### Phase 2: Normalize the Data

**Objective:** Ensure apples-to-apples comparison.

Consider adjustments for:
- Fiscal year-end differences
- Currency (if international)
- Accounting policy differences
- One-time items

**Key Normalizations:**
- Use TTM (trailing twelve months) for income metrics
- Use most recent quarter for balance sheet
- Convert all to same currency if needed

### Phase 3: Valuation Comparison

**Objective:** Identify relative cheapness/expensiveness.

Compare metrics:

| Metric | Use Case |
|--------|----------|
| P/E | Profitable companies |
| P/S | High-growth, unprofitable |
| P/B | Asset-heavy industries |
| EV/EBITDA | Leverage-neutral comparison |
| EV/Revenue | Pre-profit companies |
| PEG | Growth-adjusted value |

**Analysis:**
- Rank companies on each metric
- Identify outliers (why is X so cheap/expensive?)
- Consider premium/discount justification

### Phase 4: Growth Comparison

**Objective:** Assess growth trajectories.

Compare:
- Revenue growth (1Y, 3Y CAGR, 5Y CAGR)
- EPS growth (1Y, 3Y CAGR)
- Guidance/estimates for next year

**Analysis:**
- Who's growing fastest?
- Is growth sustainable?
- What's driving the growth differences?

### Phase 5: Profitability Comparison

**Objective:** Identify operational excellence.

Compare margins:
- Gross margin (pricing power, cost structure)
- Operating margin (operational efficiency)
- Net margin (overall profitability)
- Return metrics (ROE, ROA, ROIC)

**Analysis:**
- Who operates most efficiently?
- Are margins expanding or contracting?
- What explains margin differences?

### Phase 6: Financial Health Comparison

**Objective:** Assess relative risk.

Compare:
- Debt levels (Debt/Equity, Debt/EBITDA)
- Liquidity (Current ratio, cash position)
- Interest coverage
- Cash flow generation

**Analysis:**
- Who has the strongest balance sheet?
- Who is most/least leveraged?
- Who generates the most free cash flow?

### Phase 7: Quality Assessment

**Objective:** Identify qualitative differentiators.

Consider:
- Management quality and tenure
- Competitive moat strength
- Market position (leader vs challenger)
- Innovation pipeline
- ESG/governance factors

### Phase 8: Synthesis & Ranking

**Objective:** Form comparative conclusions.

Create a scorecard:

| Factor | Weight | Co. A | Co. B | Co. C |
|--------|--------|-------|-------|-------|
| Valuation | 25% | | | |
| Growth | 25% | | | |
| Profitability | 20% | | | |
| Financial Health | 15% | | | |
| Quality | 15% | | | |
| **Total** | 100% | | | |

## Output Template

```
## Comparative Analysis: {Companies}

### Comparison Set
| Company | Ticker | Market Cap | Sector |
|---------|--------|------------|--------|
| ... | ... | ... | ... |

### Valuation Summary
[Table with all valuation metrics, highlighting cheapest/most expensive]

### Growth Comparison
[Table with growth rates, highlighting fastest growers]

### Profitability Comparison
[Table with margins, highlighting most profitable]

### Financial Strength
[Table with leverage/liquidity, highlighting strongest]

### Competitive Positioning
[Qualitative comparison of market positions]

### Scorecard
[Weighted ranking table]

### Conclusions

**Best Value:** {Company} - [reasoning]
**Best Growth:** {Company} - [reasoning]
**Best Quality:** {Company} - [reasoning]
**Highest Risk:** {Company} - [reasoning]

### Recommendation
[Which company(ies) stand out and why]

---
Sources: [List with dates]
```
