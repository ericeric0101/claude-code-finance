# Technicals Capability

Technical analysis of price trends and indicators.

### 1. Price Overview
Fetch current quote and recent price data from Alpha Vantage (see `apis/alphavantage.md`):

- Current price
- Day's range (high/low)
- 52-week range
- Distance from 52-week high/low
- Recent price change (1D, 1W, 1M, 3M, YTD)

### 2. Trend Analysis

**Moving Averages:**
Fetch SMA indicators:
- 20-day SMA (short-term)
- 50-day SMA (medium-term)
- 200-day SMA (long-term)

Determine:
- Price vs each MA (above/below)
- MA alignment (bullish: 20 > 50 > 200, bearish: reverse)
- Golden cross / Death cross status

**Trend Direction:**
- Short-term trend (20-day)
- Medium-term trend (50-day)
- Long-term trend (200-day)

### 3. Momentum Indicators

**RSI (Relative Strength Index):**
```
?function=RSI&symbol={TICKER}&interval=daily&time_period=14&series_type=close
```
- Current RSI value
- Overbought (>70) / Oversold (<30) status
- Divergence from price (if notable)

**MACD:**
```
?function=MACD&symbol={TICKER}&interval=daily&series_type=close
```
- MACD line vs Signal line
- Histogram trend
- Recent crossovers

### 4. Volatility

**Bollinger Bands:**
```
?function=BBANDS&symbol={TICKER}&interval=daily&time_period=20&series_type=close
```
- Current price position within bands
- Band width (expanding/contracting)
- Recent band touches

### 5. Support & Resistance

Based on recent price action:
- Identify key support levels (recent lows, round numbers)
- Identify key resistance levels (recent highs, round numbers)
- Distance to nearest support/resistance

### 6. Volume Analysis

From daily price data:
- Current volume vs average
- Volume trend (increasing/decreasing)
- Notable volume spikes

## Output Format

```
## {Company Name} ({TICKER}) Technical Analysis

### Price Summary
| Metric | Value |
|--------|-------|
| Current Price | ${price} |
| Day Range | ${low} - ${high} |
| 52-Week Range | ${52w_low} - ${52w_high} |
| From 52W High | -{X}% |
| From 52W Low | +{X}% |

### Performance
| Period | Change |
|--------|--------|
| 1 Day | {+/-X%} |
| 1 Week | {+/-X%} |
| 1 Month | {+/-X%} |
| 3 Months | {+/-X%} |
| YTD | {+/-X%} |

### Trend Analysis
| Moving Average | Value | Price Position |
|----------------|-------|----------------|
| 20-day SMA | ${X} | {Above/Below} |
| 50-day SMA | ${X} | {Above/Below} |
| 200-day SMA | ${X} | {Above/Below} |

**Trend Summary:** {Bullish/Bearish/Neutral} - [explanation]

### Momentum Indicators
| Indicator | Value | Signal |
|-----------|-------|--------|
| RSI (14) | {X} | {Overbought/Neutral/Oversold} |
| MACD | {X} | {Bullish/Bearish} |
| MACD Signal | {X} | |
| MACD Histogram | {X} | {Expanding/Contracting} |

### Volatility (Bollinger Bands)
- Upper Band: ${X}
- Middle Band: ${X}
- Lower Band: ${X}
- Price Position: {Near upper/middle/lower}

### Support & Resistance
| Level | Price | Type |
|-------|-------|------|
| R2 | ${X} | Resistance |
| R1 | ${X} | Resistance |
| Current | ${X} | - |
| S1 | ${X} | Support |
| S2 | ${X} | Support |

### Technical Outlook

**Short-term (1-2 weeks):** {Outlook with reasoning}
**Medium-term (1-3 months):** {Outlook with reasoning}

**Key Levels to Watch:**
- Bullish above: ${X}
- Bearish below: ${X}

---
Source: Alpha Vantage, as of {date}
Note: Technical analysis reflects historical patterns and does not guarantee future performance.
```

## Rate Limit Awareness

This skill uses 4-6 Alpha Vantage requests:
- Quote (1)
- Daily prices (1)
- SMA (1-2)
- RSI (1)
- MACD (1)
- Bollinger Bands (1)

Consider which indicators are most relevant and fetch selectively.
