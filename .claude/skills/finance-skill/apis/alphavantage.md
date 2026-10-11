# Alpha Vantage API

Market data, financials, and technical indicators.

**Rate Limit:** 25 requests/day (free tier). Cache aggressively.

## Python Module

Use `scripts/alphavantage.py` for all Alpha Vantage access:

```python
from alphavantage import get_quote, get_overview, get_income_statement

# Current quote
quote = get_quote("AAPL")
# → {"symbol": "AAPL", "price": 260.10, "change": 2.50, ...}

# Company overview with valuation metrics
overview = get_overview("AAPL")
# → {"name": "Apple Inc", "pe_ratio": 34.84, "market_cap": 3845545787000, ...}

# Financial statements
income = get_income_statement("AAPL")           # Annual
income_q = get_income_statement("AAPL", quarterly=True)
balance = get_balance_sheet("AAPL")
cashflow = get_cash_flow("AAPL")

# Technical indicators
from alphavantage import get_rsi, get_macd, get_sma, get_bbands
rsi = get_rsi("AAPL", period=14)
macd = get_macd("AAPL")
sma = get_sma("AAPL", period=50)
bbands = get_bbands("AAPL", period=20)
```

### CLI Usage

Scripts auto-bootstrap via uv on first run:

```bash
python3 scripts/alphavantage.py AAPL quote
python3 scripts/alphavantage.py AAPL overview
python3 scripts/alphavantage.py AAPL income
```

## Environment Variable

```
ALPHA_VANTAGE_API_KEY=your_key_here
```

Get a free key at [alphavantage.co](https://www.alphavantage.co/support/#api-key).

## Available Functions

### Quotes & Prices
| Function | Description |
|----------|-------------|
| `get_quote(symbol)` | Current price, change, volume |
| `get_daily_prices(symbol)` | Daily OHLCV data |

### Fundamentals
| Function | Description |
|----------|-------------|
| `get_overview(symbol)` | Company info, valuation metrics |
| `get_income_statement(symbol)` | Revenue, margins, net income |
| `get_balance_sheet(symbol)` | Assets, liabilities, equity |
| `get_cash_flow(symbol)` | Operating, investing, financing |
| `get_earnings(symbol)` | EPS with surprise data |

### Technicals
| Function | Description |
|----------|-------------|
| `get_sma(symbol, period)` | Simple Moving Average |
| `get_rsi(symbol, period)` | Relative Strength Index |
| `get_macd(symbol)` | MACD indicator |
| `get_bbands(symbol, period)` | Bollinger Bands |

### News
| Function | Description |
|----------|-------------|
| `get_news(symbol)` | Recent articles with sentiment |

## Cache TTLs

Data is cached automatically:

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Company Overview | 7 days | Changes rarely |
| Financial Statements | 24 hours | Updated quarterly |
| Stock Quotes | 24 hours | Free tier is end-of-day |
| Technical Indicators | 1 hour | Acceptable for analysis |
| News | 30 minutes | Balance freshness vs quota |

## Rate Limit Planning

With 25 requests/day:
- Full research (overview + financials): ~5 requests
- Technical analysis: ~5 requests
- Plan for ~3-4 deep analyses per day

Prefer SEC EDGAR for filing data (unlimited).
