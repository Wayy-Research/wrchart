#!/usr/bin/env python
"""Debug script to test chart generation and find blank graph issue."""

import sys
sys.path.insert(0, '.')

import wrchart as wrc
import polars as pl
import numpy as np
import json

print(f'wrchart version: {wrc.__version__}')

# Generate sample OHLCV data
np.random.seed(42)
n = 100

returns = np.random.randn(n) * 0.02
prices = 100 * np.exp(np.cumsum(returns))

opens = np.roll(prices, 1)
opens[0] = prices[0]
highs = np.maximum(prices, opens) * (1 + np.abs(np.random.randn(n)) * 0.01)
lows = np.minimum(prices, opens) * (1 - np.abs(np.random.randn(n)) * 0.01)
volumes = np.random.randint(100000, 1000000, n)

df = pl.DataFrame({
    'time': list(range(n)),
    'open': opens,
    'high': highs,
    'low': lows,
    'close': prices,
    'volume': volumes,
})

print("\nDataFrame head:")
print(df.head())

print("\nDataFrame dtypes:")
print(df.dtypes)

# Create chart
chart = wrc.Chart(width=900, height=500, title='Test Chart')
chart.add_candlestick(df)
chart.add_volume(df)

# Get the JSON config and check for issues
config_json = chart.to_json()
config = json.loads(config_json)

print("\n--- Chart Config Debug ---")
print(f"Number of series: {len(config['series'])}")

for i, series in enumerate(config['series']):
    print(f"\nSeries {i} ({series['type']}):")
    print(f"  Data length: {len(series['data'])}")
    if series['data']:
        print(f"  First item: {series['data'][0]}")
        print(f"  Last item: {series['data'][-1]}")

        # Check for any None/NaN values
        for j, item in enumerate(series['data'][:5]):
            for k, v in item.items():
                if v is None:
                    print(f"    WARNING: None value at index {j}, key '{k}'")
                elif isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                    print(f"    WARNING: NaN/Inf value at index {j}, key '{k}': {v}")

# Try to serialize to JSON again to catch numpy type issues
print("\n--- JSON Serialization Test ---")
try:
    json_str = json.dumps(config)
    print(f"JSON serialization successful! Length: {len(json_str)} chars")
except TypeError as e:
    print(f"JSON serialization FAILED: {e}")

    # Find the problematic values
    for i, series in enumerate(config['series']):
        for j, item in enumerate(series['data'][:5]):
            for k, v in item.items():
                try:
                    json.dumps(v)
                except TypeError:
                    print(f"  Problematic value at series {i}, index {j}, key '{k}': {v} (type: {type(v)})")

# Save HTML for inspection
html = chart._generate_html()
with open('test_chart.html', 'w') as f:
    f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Chart Debug</title>
</head>
<body style="background: #131722; padding: 20px;">
    {html}
</body>
</html>
""")
print("\nSaved test_chart.html for browser inspection")

# Also print the raw data that goes into the chart
print("\n--- Raw JS Data Sample (first 3 items) ---")
for i, series in enumerate(config['series']):
    print(f"\nSeries {i} ({series['type']}) first 3 items:")
    for item in series['data'][:3]:
        print(f"  {item}")
