import numpy as np
import pandas as pd
import io
import time


# ─────────────────────────────────────────────────────────────────────────────
# HARDCODED FALLBACK DATA for tickers that consistently fail
# (Update these values periodically to keep them fresh)
# ─────────────────────────────────────────────────────────────────────────────
_HARDCODED = {
    "TATAMOTORS.NS": {
        "current_price": 685.0,   # Approximate price in ₹ (update as needed)
        "mu": 0.18,               # Annualized drift (~18% historical return)
        "sigma": 0.42,            # Annualized volatility (~42%)
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE 1: yfinance (primary)
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_yfinance(ticker, period="3y"):
    """Primary source: yfinance library."""
    import yfinance as yf
    data = yf.download(ticker, period=period, interval="1d")
    if data.empty:
        raise ValueError("yfinance returned empty data")
    if isinstance(data.columns, pd.MultiIndex):
        close = data['Close'].iloc[:, 0].dropna().values
    else:
        close = data['Close'].dropna().values
    return close.flatten()


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE 2: Direct Yahoo Finance CSV download (no library needed)
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_yahoo_direct(ticker, years=3):
    """
    Fallback: scrape Yahoo Finance CSV endpoint directly.
    No API key required.
    """
    import requests

    period2 = int(time.time())
    period1 = int(period2 - years * 365.25 * 86400)

    url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}"
        f"?period1={period1}&period2={period2}&interval=1d&events=history"
        f"&includeAdjustedClose=true"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        )
    }

    session = requests.Session()
    session.headers.update(headers)
    session.get("https://finance.yahoo.com", timeout=10)

    crumb_resp = session.get(
        "https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=10
    )
    crumb = crumb_resp.text.strip()
    if not crumb:
        raise ValueError("Could not obtain Yahoo crumb")

    csv_url = url + f"&crumb={crumb}"
    resp = session.get(csv_url, timeout=15)
    resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text), parse_dates=["Date"])
    close = df["Close"].dropna().values.flatten()

    if len(close) < 20:
        raise ValueError("Yahoo direct CSV returned insufficient data")

    return close


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE 3: Alpha Vantage (free key)
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_alpha_vantage(ticker):
    """Fallback: Alpha Vantage TIME_SERIES_DAILY."""
    import requests

    API_KEY = "demo"
    av_ticker = ticker.replace(".NS", ".BSE").replace(".BO", ".BSE")

    url = (
        f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY"
        f"&symbol={av_ticker}&outputsize=full&apikey={API_KEY}"
    )

    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    ts = data.get("Time Series (Daily)")
    if not ts:
        raise ValueError(
            f"Alpha Vantage error: "
            f"{data.get('Note', data.get('Error Message', 'Unknown'))}"
        )

    df = pd.DataFrame.from_dict(ts, orient="index").sort_index()
    close = df["4. close"].astype(float).dropna().values.flatten()

    if len(close) < 20:
        raise ValueError("Alpha Vantage returned insufficient data")

    return close


# ─────────────────────────────────────────────────────────────────────────────
# MASTER FUNCTION: tries each source in order, then hardcoded fallback
# ─────────────────────────────────────────────────────────────────────────────
_SOURCES = [
    ("yfinance", _fetch_yfinance),
    ("Yahoo Direct CSV", _fetch_yahoo_direct),
    ("Alpha Vantage", _fetch_alpha_vantage),
]


def get_stock_data(ticker, period="3y"):
    """
    Fetches historical close prices from multiple backends with automatic
    failover. Falls back to hardcoded values if all APIs fail.
    Returns (current_price, mu, sigma, source_name).
    """
    errors = []

    for name, fetch_fn in _SOURCES:
        try:
            if name == "yfinance":
                close_prices = fetch_fn(ticker, period)
            elif name == "Yahoo Direct CSV":
                years = int(period.replace("y", "")) if "y" in period else 3
                close_prices = fetch_fn(ticker, years)
            else:
                close_prices = fetch_fn(ticker)

            if close_prices is None or len(close_prices) < 20:
                raise ValueError(f"{name}: not enough data points")

            log_returns = np.log(close_prices[1:] / close_prices[:-1])
            mu = float(np.mean(log_returns) * 252)
            sigma = float(np.std(log_returns) * np.sqrt(252))
            current_price = float(close_prices[-1])

            return current_price, mu, sigma, name

        except Exception as e:
            errors.append(f"  • {name}: {e}")
            continue

    # ── All API sources failed — try hardcoded fallback ─────────────────────
    if ticker in _HARDCODED:
        hc = _HARDCODED[ticker]
        return hc["current_price"], hc["mu"], hc["sigma"], "Hardcoded Fallback"

    error_report = "\n".join(errors)
    raise ValueError(f"All data sources failed for {ticker}:\n{error_report}")