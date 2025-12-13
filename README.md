# wrchart

Interactive financial charting for Python with Polars support and TradingView-style aesthetics.

**[View Live Demo](./examples/demo.html)** - See all chart types, indicators, GPU-accelerated million-point rendering, and high-frequency data visualization in action.

## Features

- **Polars-native** - Works directly with Polars DataFrames
- **Interactive** - TradingView-style pan, zoom, and crosshair
- **Jupyter-ready** - Renders inline in notebooks
- **Non-standard charts** - Renko, Kagi, Point & Figure, Heikin-Ashi, Line Break, Range Bars
- **GPU-accelerated** - WebGL rendering for millions of points at 60fps
- **Dynamic LOD** - Level of Detail automatically adjusts based on zoom
- **High-frequency data** - LTTB decimation for tick data visualization
- **Styled by default** - Clean Wayy Research aesthetic

## Install

```bash
pip install wrchart
```

For Jupyter support:
```bash
pip install wrchart[jupyter]
```

## Quick Start

```python
import wrchart as wrc
import polars as pl

# Create OHLCV data
df = pl.DataFrame({
    "time": [...],
    "open": [...],
    "high": [...],
    "low": [...],
    "close": [...],
    "volume": [...],
})

# Create chart
chart = wrc.Chart(width=800, height=600)
chart.add_candlestick(df)
chart.add_volume(df)
chart.show()
```

## Chart Types

### Standard Charts

```python
# Candlestick
chart = wrc.Chart()
chart.add_candlestick(df)

# Line
chart.add_line(df, value_col="close")

# Area
chart.add_area(df, value_col="close")
```

### Non-Standard Charts

```python
# Heikin-Ashi (smoothed candles)
ha_data = wrc.to_heikin_ashi(df)
chart.add_candlestick(ha_data)

# Renko (price-based bricks)
renko_data = wrc.to_renko(df, brick_size=5.0)
chart.add_candlestick(renko_data)

# Kagi (reversal lines)
kagi_data = wrc.to_kagi(df, reversal_amount=2.0)

# Point & Figure (X's and O's)
pnf_data = wrc.to_point_and_figure(df, box_size=1.0)

# Three Line Break
lb_data = wrc.to_line_break(df, num_lines=3)

# Range Bars
rb_data = wrc.to_range_bars(df, range_size=2.0)
```

### High-Frequency Data

```python
# Downsample 1M ticks to 2000 points
display_data = wrc.lttb_downsample(tick_data, target_points=2000)
chart.add_line(display_data, value_col="price")
```

### GPU-Accelerated Million Point Rendering

For tick-by-tick data with millions of points, use `WebGLChart` for GPU-accelerated rendering:

```python
import wrchart as wrc
import polars as pl

# Create 1 million tick data points
df = pl.DataFrame({
    "time": range(1_000_000),
    "price": [...],  # Your tick prices
})

# WebGL chart with automatic LOD
chart = wrc.WebGLChart(width=800, height=400, title="Tick Data")
chart.add_line(df, time_col="time", value_col="price")
chart.show()

# Or save to HTML file
chart.to_html("tick_chart.html")
```

Features:
- **60fps rendering** of millions of points via WebGL
- **Dynamic LOD**: Automatically switches between 7 detail levels (2K to 1M points)
- **Virtual viewport**: Only renders visible data for maximum performance
- **Smooth interaction**: Pan with drag, zoom with scroll wheel

## Themes

```python
# Wayy theme (default) - black/white/red
chart = wrc.Chart(theme=wrc.WayyTheme)

# Dark theme
chart = wrc.Chart(theme=wrc.DarkTheme)

# Light theme
chart = wrc.Chart(theme=wrc.LightTheme)
```

## API Reference

### Chart

```python
wrc.Chart(
    width=800,          # Chart width in pixels
    height=600,         # Chart height in pixels
    theme=WayyTheme,    # Color theme
    title=None,         # Optional chart title
)

# Methods
chart.add_candlestick(df, time_col="time", open_col="open", ...)
chart.add_line(df, time_col="time", value_col="value", ...)
chart.add_area(df, time_col="time", value_col="value", ...)
chart.add_histogram(df, time_col="time", value_col="value", ...)
chart.add_volume(df, time_col="time", volume_col="volume", ...)
chart.add_marker(time, position="aboveBar", shape="circle", ...)
chart.show()
```

### WebGLChart (GPU-Accelerated)

```python
wrc.WebGLChart(
    width=800,          # Chart width in pixels
    height=400,         # Chart height in pixels
    theme=WayyTheme,    # Color theme
    title=None,         # Optional chart title
)

# Methods
chart.add_line(df, time_col="time", value_col="value")  # Add line data
chart.show()                                             # Display in notebook/browser
chart.to_html("chart.html")                             # Save to HTML file
```

### Transforms

```python
# Heikin-Ashi
wrc.to_heikin_ashi(df, time_col="time", open_col="open", ...)

# Renko
wrc.to_renko(df, brick_size=5.0, use_atr=False, ...)

# Kagi
wrc.to_kagi(df, reversal_amount=2.0, use_percentage=False, ...)

# Point & Figure
wrc.to_point_and_figure(df, box_size=1.0, reversal_boxes=3, ...)

# Line Break
wrc.to_line_break(df, num_lines=3, ...)

# Range Bars
wrc.to_range_bars(df, range_size=2.0, ...)

# LTTB Decimation
wrc.lttb_downsample(df, time_col="time", value_col="value", target_points=1000)
```

## Integration with wrtrade

```python
import wrtrade as wrt
import wrchart as wrc

# Backtest
portfolio = wrt.Portfolio(prices, signals)
results = portfolio.calculate_performance()

# Visualize
chart = wrc.Chart(title="Portfolio Performance")
chart.add_line(
    results['cumulative_returns'].to_frame(),
    value_col="cumulative_returns"
)
chart.show()
```

## License

MIT License - see LICENSE file for details.

## Links

- [GitHub](https://github.com/wayy-research/wrchart)
- [Documentation](https://wrchart.readthedocs.io/)
- [Wayy Research](https://wayyresearch.com)
