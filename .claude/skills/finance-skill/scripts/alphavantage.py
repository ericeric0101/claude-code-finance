#!/usr/bin/env python3
"""
Alpha Vantage client with caching.

Usage:
    from alphavantage import get_quote, get_overview, get_income_statement

    quote = get_quote("AAPL")
    overview = get_overview("AAPL")
    income = get_income_statement("AAPL")
"""

import venv  # Auto-setup venv before other imports
import env  # Load .env before other imports

import os
import hashlib
from cache import cached_request

BASE_URL = "https://www.alphavantage.co/query"


def _get_api_key() -> str:
    """Get API key from environment."""
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise Exception("ALPHA_VANTAGE_API_KEY environment variable not set")
    return api_key


def _validate_symbol(symbol: str) -> str:
    """Validate and normalize stock symbol."""
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string")
    return symbol.strip().upper()


def request(function: str, symbol: str = None, extra_params: dict = None) -> dict:
    """
    Make a cached request to Alpha Vantage API.

    Args:
        function: API function name (e.g., "OVERVIEW", "GLOBAL_QUOTE")
        symbol: Stock symbol (optional for some functions)
        extra_params: Additional query parameters

    Returns:
        Parsed JSON response
    """
    params = {"function": function, "apikey": _get_api_key()}
    if symbol:
        params["symbol"] = _validate_symbol(symbol)
    if extra_params:
        params.update(extra_params)

    # Build URL
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE_URL}?{query}"

    # Build cache key
    cache_key = f"alphavantage/{function}"
    if symbol:
        cache_key += f"_{symbol}"
    if extra_params:
        param_hash = hashlib.md5(str(sorted(extra_params.items())).encode()).hexdigest()[:8]
        cache_key += f"_{param_hash}"

    data = cached_request(url, cache_key)

    # Check for API errors
    if "Error Message" in data:
        raise Exception(f"Alpha Vantage error: {data['Error Message']}")
    if "Note" in data:
        raise Exception(f"Alpha Vantage rate limit: {data['Note']}")

    return data


# =============================================================================
# Stock Quotes
# =============================================================================

def get_quote(symbol: str) -> dict:
    """
    Get current stock quote.

    Returns:
        dict with price, change, volume, etc.
    """
    data = request("GLOBAL_QUOTE", symbol)
    quote = data.get("Global Quote", {})
    return {
        "symbol": quote.get("01. symbol"),
        "price": float(quote.get("05. price", 0)),
        "change": float(quote.get("09. change", 0)),
        "change_percent": quote.get("10. change percent", "").rstrip("%"),
        "volume": int(quote.get("06. volume", 0)),
        "latest_day": quote.get("07. latest trading day"),
        "previous_close": float(quote.get("08. previous close", 0)),
        "open": float(quote.get("02. open", 0)),
        "high": float(quote.get("03. high", 0)),
        "low": float(quote.get("04. low", 0)),
    }


def get_daily_prices(symbol: str, outputsize: str = "compact") -> dict:
    """
    Get daily OHLCV data.

    Args:
        symbol: Stock symbol
        outputsize: "compact" (100 days) or "full" (20+ years)

    Returns:
        dict with metadata and time series
    """
    return request("TIME_SERIES_DAILY", symbol, {"outputsize": outputsize})


# =============================================================================
# Company Fundamentals
# =============================================================================

def get_overview(symbol: str) -> dict:
    """
    Get company overview with key metrics.

    Returns:
        dict with company info, valuation metrics, financials
    """
    data = request("OVERVIEW", symbol)
    return {
        "symbol": data.get("Symbol"),
        "name": data.get("Name"),
        "description": data.get("Description"),
        "sector": data.get("Sector"),
        "industry": data.get("Industry"),
        "market_cap": _safe_int(data.get("MarketCapitalization")),
        "pe_ratio": _safe_float(data.get("PERatio")),
        "pe_forward": _safe_float(data.get("ForwardPE")),
        "peg_ratio": _safe_float(data.get("PEGRatio")),
        "price_to_book": _safe_float(data.get("PriceToBookRatio")),
        "price_to_sales": _safe_float(data.get("PriceToSalesRatioTTM")),
        "ev_to_ebitda": _safe_float(data.get("EVToEBITDA")),
        "eps": _safe_float(data.get("EPS")),
        "revenue_ttm": _safe_int(data.get("RevenueTTM")),
        "gross_profit_ttm": _safe_int(data.get("GrossProfitTTM")),
        "ebitda": _safe_int(data.get("EBITDA")),
        "profit_margin": _safe_float(data.get("ProfitMargin")),
        "operating_margin": _safe_float(data.get("OperatingMarginTTM")),
        "roe": _safe_float(data.get("ReturnOnEquityTTM")),
        "roa": _safe_float(data.get("ReturnOnAssetsTTM")),
        "dividend_yield": _safe_float(data.get("DividendYield")),
        "dividend_per_share": _safe_float(data.get("DividendPerShare")),
        "beta": _safe_float(data.get("Beta")),
        "52_week_high": _safe_float(data.get("52WeekHigh")),
        "52_week_low": _safe_float(data.get("52WeekLow")),
        "50_day_ma": _safe_float(data.get("50DayMovingAverage")),
        "200_day_ma": _safe_float(data.get("200DayMovingAverage")),
        "shares_outstanding": _safe_int(data.get("SharesOutstanding")),
        "book_value": _safe_float(data.get("BookValue")),
    }


def get_income_statement(symbol: str, quarterly: bool = False) -> list[dict]:
    """
    Get income statement data.

    Args:
        symbol: Stock symbol
        quarterly: If True, return quarterly data; else annual

    Returns:
        List of income statement records
    """
    data = request("INCOME_STATEMENT", symbol)
    key = "quarterlyReports" if quarterly else "annualReports"
    reports = data.get(key, [])
    return [_parse_income_statement(r) for r in reports]


def get_balance_sheet(symbol: str, quarterly: bool = False) -> list[dict]:
    """
    Get balance sheet data.

    Args:
        symbol: Stock symbol
        quarterly: If True, return quarterly data; else annual

    Returns:
        List of balance sheet records
    """
    data = request("BALANCE_SHEET", symbol)
    key = "quarterlyReports" if quarterly else "annualReports"
    reports = data.get(key, [])
    return [_parse_balance_sheet(r) for r in reports]


def get_cash_flow(symbol: str, quarterly: bool = False) -> list[dict]:
    """
    Get cash flow statement data.

    Args:
        symbol: Stock symbol
        quarterly: If True, return quarterly data; else annual

    Returns:
        List of cash flow records
    """
    data = request("CASH_FLOW", symbol)
    key = "quarterlyReports" if quarterly else "annualReports"
    reports = data.get(key, [])
    return [_parse_cash_flow(r) for r in reports]


def get_earnings(symbol: str) -> dict:
    """
    Get earnings data with surprises.

    Returns:
        dict with annual and quarterly earnings
    """
    data = request("EARNINGS", symbol)
    return {
        "annual": data.get("annualEarnings", []),
        "quarterly": data.get("quarterlyEarnings", []),
    }


# =============================================================================
# Technical Indicators
# =============================================================================

def get_sma(symbol: str, period: int = 20, interval: str = "daily") -> dict:
    """Get Simple Moving Average."""
    return request("SMA", symbol, {
        "interval": interval,
        "time_period": str(period),
        "series_type": "close"
    })


def get_rsi(symbol: str, period: int = 14, interval: str = "daily") -> dict:
    """Get Relative Strength Index."""
    return request("RSI", symbol, {
        "interval": interval,
        "time_period": str(period),
        "series_type": "close"
    })


def get_macd(symbol: str, interval: str = "daily") -> dict:
    """Get MACD indicator."""
    return request("MACD", symbol, {
        "interval": interval,
        "series_type": "close"
    })


def get_bbands(symbol: str, period: int = 20, interval: str = "daily") -> dict:
    """Get Bollinger Bands."""
    return request("BBANDS", symbol, {
        "interval": interval,
        "time_period": str(period),
        "series_type": "close"
    })


# =============================================================================
# News & Sentiment
# =============================================================================

def get_news(symbol: str) -> list[dict]:
    """
    Get news articles with sentiment.

    Returns:
        List of news articles
    """
    data = request("NEWS_SENTIMENT", extra_params={"tickers": symbol})
    return data.get("feed", [])


# =============================================================================
# Helpers
# =============================================================================

def _safe_float(value) -> float | None:
    """Convert to float, returning None for invalid values."""
    if value is None or value == "None" or value == "-":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value) -> int | None:
    """Convert to int, returning None for invalid values."""
    if value is None or value == "None" or value == "-":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_income_statement(report: dict) -> dict:
    """Parse income statement report."""
    return {
        "fiscal_date": report.get("fiscalDateEnding"),
        "currency": report.get("reportedCurrency"),
        "revenue": _safe_int(report.get("totalRevenue")),
        "cost_of_revenue": _safe_int(report.get("costOfRevenue")),
        "gross_profit": _safe_int(report.get("grossProfit")),
        "operating_expenses": _safe_int(report.get("operatingExpenses")),
        "operating_income": _safe_int(report.get("operatingIncome")),
        "net_income": _safe_int(report.get("netIncome")),
        "ebitda": _safe_int(report.get("ebitda")),
        "eps": _safe_float(report.get("reportedEPS")),
    }


def _parse_balance_sheet(report: dict) -> dict:
    """Parse balance sheet report."""
    return {
        "fiscal_date": report.get("fiscalDateEnding"),
        "currency": report.get("reportedCurrency"),
        "total_assets": _safe_int(report.get("totalAssets")),
        "total_liabilities": _safe_int(report.get("totalLiabilities")),
        "total_equity": _safe_int(report.get("totalShareholderEquity")),
        "cash": _safe_int(report.get("cashAndCashEquivalentsAtCarryingValue")),
        "short_term_debt": _safe_int(report.get("shortTermDebt")),
        "long_term_debt": _safe_int(report.get("longTermDebt")),
        "current_assets": _safe_int(report.get("totalCurrentAssets")),
        "current_liabilities": _safe_int(report.get("totalCurrentLiabilities")),
    }


def _parse_cash_flow(report: dict) -> dict:
    """Parse cash flow report."""
    return {
        "fiscal_date": report.get("fiscalDateEnding"),
        "currency": report.get("reportedCurrency"),
        "operating_cashflow": _safe_int(report.get("operatingCashflow")),
        "investing_cashflow": _safe_int(report.get("cashflowFromInvestment")),
        "financing_cashflow": _safe_int(report.get("cashflowFromFinancing")),
        "capex": _safe_int(report.get("capitalExpenditures")),
        "dividends_paid": _safe_int(report.get("dividendPayout")),
        "net_change": _safe_int(report.get("changeInCashAndCashEquivalents")),
    }


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: alphavantage.py <symbol> [function]")
        print("Functions: quote, overview, income, balance, cashflow, earnings")
        sys.exit(1)

    symbol = sys.argv[1]
    func = sys.argv[2] if len(sys.argv) > 2 else "overview"

    print(f"Fetching {func} for {symbol}...")

    if func == "quote":
        data = get_quote(symbol)
    elif func == "overview":
        data = get_overview(symbol)
    elif func == "income":
        data = get_income_statement(symbol)
    elif func == "balance":
        data = get_balance_sheet(symbol)
    elif func == "cashflow":
        data = get_cash_flow(symbol)
    elif func == "earnings":
        data = get_earnings(symbol)
    else:
        print(f"Unknown function: {func}")
        sys.exit(1)

    print(json.dumps(data, indent=2, default=str))
