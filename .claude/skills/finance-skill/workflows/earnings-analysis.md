# Earnings Analysis Workflow

A structured approach to analyzing quarterly earnings releases and their implications.

## When to Use

- Before an earnings announcement (preview)
- After an earnings release (analysis)
- Tracking a company through reporting season
- Understanding earnings surprises

## Workflow Steps

### Phase 1: Pre-Earnings Context

**Objective:** Understand expectations going into earnings.

1. Review analyst estimates (if available via yfinance)
2. Note key metrics to watch:
   - Revenue consensus
   - EPS consensus
   - Guidance ranges

3. Identify key themes:
   - What did management guide for last quarter?
   - What are the market's concerns?
   - What macro factors might impact results?

### Phase 2: Historical Pattern

**Objective:** Understand the company's earnings track record.

1. Fetch earnings history from Alpha Vantage
2. Analyze:
   - Beat/miss pattern (last 4-8 quarters)
   - Average surprise magnitude
   - Stock reaction to prior reports
   - Seasonal patterns

### Phase 3: Results Analysis (Post-Earnings)

**Objective:** Dissect the actual earnings release.

**Revenue Analysis:**
- Actual vs consensus
- Year-over-year growth
- Sequential growth
- By segment (if available)

**Earnings Analysis:**
- EPS actual vs consensus
- GAAP vs non-GAAP reconciliation
- One-time items
- Tax rate impact

**Margin Analysis:**
- Gross margin change
- Operating margin change
- Drivers of margin change

### Phase 4: Guidance Assessment

**Objective:** Understand forward outlook.

If guidance provided:
- Next quarter guidance vs consensus
- Full year guidance vs consensus
- Change from prior guidance (raised/lowered/maintained)
- Commentary on key drivers

### Phase 5: Management Commentary

**Objective:** Extract qualitative insights.

Key topics to note:
- Demand environment
- Competitive dynamics
- Cost pressures
- Capital allocation priorities
- Macro outlook

**Look for:**
- Changes in tone from prior quarters
- New initiatives or concerns
- Specific metrics management highlights

### Phase 6: Market Reaction

**Objective:** Understand how the market interpreted results.

Monitor:
- After-hours price movement
- Next-day trading
- Volume vs average
- Analyst rating changes

**Consider:**
- Does reaction match the quality of results?
- What's driving the reaction (beat, guidance, commentary)?
- Is this an overreaction?

### Phase 7: Investment Implications

**Objective:** Determine what this means for the investment thesis.

Assess:
- Does this change the fundamental story?
- Are estimates likely to rise or fall?
- Has risk profile changed?
- Valuation implications

## Output Template

### Pre-Earnings Preview
```
## {Company} Q{X} {Year} Earnings Preview

### Expectations
| Metric | Consensus | Company Guidance | YoY Change |
|--------|-----------|------------------|------------|
| Revenue | | | |
| EPS | | | |

### Key Themes to Watch
1. [Theme 1]
2. [Theme 2]
3. [Theme 3]

### Historical Track Record
| Quarter | EPS Est | EPS Actual | Surprise |
|---------|---------|------------|----------|
| ... | ... | ... | ... |

### What Would Be Bullish/Bearish
**Bullish:** [Scenarios]
**Bearish:** [Scenarios]
```

### Post-Earnings Analysis
```
## {Company} Q{X} {Year} Earnings Analysis

### Results Summary
| Metric | Consensus | Actual | Surprise |
|--------|-----------|--------|----------|
| Revenue | | | +/-X% |
| EPS | | | +/-X% |

### Revenue Breakdown
[Segment analysis if available]

### Margin Performance
| Metric | This Q | Last Q | YoY |
|--------|--------|--------|-----|
| Gross Margin | | | |
| Operating Margin | | | |

### Guidance
| Metric | New Guidance | Prior Guidance | Consensus |
|--------|--------------|----------------|-----------|
| Q{X+1} Revenue | | | |
| Q{X+1} EPS | | | |
| FY Revenue | | | |
| FY EPS | | | |

### Key Takeaways from Call
1. [Takeaway 1]
2. [Takeaway 2]
3. [Takeaway 3]

### Market Reaction
- After-hours: {+/-X%}
- Commentary: [Why market reacted this way]

### Investment Implications
[What this means for the stock]

### Updated View
[Bullish/Bearish/Neutral and reasoning]

---
Sources: [List with dates]
```
