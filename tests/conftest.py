"""Shared test fixtures for wrchart tests."""

import numpy as np
import polars as pl
import pytest


@pytest.fixture
def daily_ohlc():
    """Daily OHLC data with standard column names (252 rows = 1 year)."""
    np.random.seed(42)
    n = 252
    prices = 100 + np.cumsum(np.random.randn(n) * 0.5)

    return pl.DataFrame({
        "time": list(range(n)),
        "open": prices + np.random.randn(n) * 0.1,
        "high": prices + np.abs(np.random.randn(n) * 0.5),
        "low": prices - np.abs(np.random.randn(n) * 0.5),
        "close": prices + np.random.randn(n) * 0.1,
        "volume": np.random.randint(1000, 10000, n).tolist(),
    })


@pytest.fixture
def ohlc_uppercase():
    """OHLC data with uppercase column names."""
    np.random.seed(42)
    n = 100
    prices = 100 + np.cumsum(np.random.randn(n) * 0.5)

    return pl.DataFrame({
        "Date": list(range(n)),
        "Open": prices + np.random.randn(n) * 0.1,
        "High": prices + np.abs(np.random.randn(n) * 0.5),
        "Low": prices - np.abs(np.random.randn(n) * 0.5),
        "Close": prices + np.random.randn(n) * 0.1,
        "Volume": np.random.randint(1000, 10000, n).tolist(),
    })


@pytest.fixture
def ohlc_short_names():
    """OHLC data with short column names (o, h, l, c)."""
    np.random.seed(42)
    n = 100
    prices = 100 + np.cumsum(np.random.randn(n) * 0.5)

    return pl.DataFrame({
        "t": list(range(n)),
        "o": prices + np.random.randn(n) * 0.1,
        "h": prices + np.abs(np.random.randn(n) * 0.5),
        "l": prices - np.abs(np.random.randn(n) * 0.5),
        "c": prices + np.random.randn(n) * 0.1,
        "v": np.random.randint(1000, 10000, n).tolist(),
    })


@pytest.fixture
def line_data():
    """Simple time-value data for line charts."""
    np.random.seed(42)
    n = 500
    return pl.DataFrame({
        "time": list(range(n)),
        "value": 100 + np.cumsum(np.random.randn(n) * 0.5),
    })


@pytest.fixture
def tick_data():
    """High-frequency tick data (500k rows)."""
    np.random.seed(42)
    n = 500_000
    return pl.DataFrame({
        "timestamp": list(range(n)),
        "price": 100 + np.cumsum(np.random.randn(n) * 0.01),
    })


@pytest.fixture
def forecast_paths():
    """Monte Carlo forecast paths (100 paths x 30 steps)."""
    np.random.seed(42)
    n_paths = 100
    n_steps = 30
    start_price = 100

    paths = []
    for _ in range(n_paths):
        path = [start_price]
        for _ in range(n_steps - 1):
            path.append(path[-1] * (1 + np.random.randn() * 0.02))
        paths.append(path)

    return {
        "paths": np.array(paths),
        "start_time": 0,
    }


@pytest.fixture
def multi_panel_data(daily_ohlc, line_data):
    """List of DataFrames for multi-panel charts."""
    return [daily_ohlc, line_data, line_data.clone()]
