# yfinance Reference (Python)

Unofficial Yahoo Finance wrapper. No API key required but may break without notice.

**Usage:** yfinance is included in scripts' dependencies. Run from `scripts/` directory:

```bash
cd scripts/
uv run python -c "import yfinance as yf; print(yf.Ticker('AAPL').info['currentPrice'])"
```

## Basic Usage

```python
import yfinance as yf

# Single ticker
ticker = yf.Ticker("AAPL")

# Multiple tickers
tickers = yf.Tickers("AAPL MSFT GOOGL")
```

## Available Data

### Company Info
```python
ticker.info  # Dict with company details, market cap, P/E, etc.
```

### Historical Prices
```python
ticker.history(period="1y")  # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
ticker.history(start="2020-01-01", end="2024-01-01")
ticker.history(period="1d", interval="1m")  # Intraday: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h
```

### Analyst Data
```python
ticker.recommendations           # Analyst recommendations (buy/hold/sell)
ticker.recommendations_summary   # Summary of recommendations
ticker.upgrades_downgrades       # Recent rating changes
ticker.analyst_price_targets     # Price target stats (low, mean, median, high)
```

### Holdings & Ownership
```python
ticker.institutional_holders    # Top institutional holders
ticker.mutualfund_holders       # Top mutual fund holders
ticker.insider_transactions     # Recent insider buys/sells
ticker.insider_holders          # Current insider positions
ticker.major_holders            # Ownership breakdown %
```

### Financials (May Be Unreliable)
```python
ticker.income_stmt              # Income statement
ticker.quarterly_income_stmt    # Quarterly income statement
ticker.balance_sheet            # Balance sheet
ticker.quarterly_balance_sheet  # Quarterly balance sheet
ticker.cashflow                 # Cash flow statement
ticker.quarterly_cashflow       # Quarterly cash flow
```
**Note:** Financial statements may return empty. Use Alpha Vantage as primary source.

### Dividends & Splits
```python
ticker.dividends    # Dividend history
ticker.splits       # Stock split history
ticker.actions      # Both dividends and splits
```

### Options
```python
ticker.options              # Available expiration dates
ticker.option_chain("2024-01-19")  # Options chain for specific date
```

## Best Uses

yfinance is most reliable for:
- Historical price data
- Analyst recommendations and price targets
- Institutional/insider holdings
- Options chains

Avoid relying on yfinance for:
- Financial statements (use Alpha Vantage)
- Real-time quotes (delayed)
- Any data requiring consistency

## Example: Get Analyst Sentiment

```python
import yfinance as yf

ticker = yf.Ticker("AAPL")

# Recent recommendations
recs = ticker.recommendations
if recs is not None:
    recent = recs.tail(10)
    print(recent[['Firm', 'To Grade', 'Action']])

# Price targets
targets = ticker.analyst_price_targets
if targets is not None:
    print(f"Low: ${targets['low']}, Mean: ${targets['mean']}, High: ${targets['high']}")
```
