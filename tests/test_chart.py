"""Tests for the unified Chart class."""

import json
import numpy as np
import polars as pl
import pytest

import wrchart as wrc
from wrchart.core.chart import Chart, candlestick, line, area, forecast, dashboard
from wrchart.core.backends.base import BackendType


class TestChartCreation:
    """Test chart creation with different data types."""

    def test_create_empty_chart(self):
        """Create chart without data."""
        chart = Chart()
        assert chart is not None
        assert chart._backend is not None

    def test_create_with_ohlc_data(self, daily_ohlc):
        """Create chart with OHLC data auto-detects candlestick."""
        chart = Chart(daily_ohlc)
        assert chart._backend_type == BackendType.LIGHTWEIGHT

    def test_create_with_line_data(self, line_data):
        """Create chart with time-value data auto-detects line."""
        chart = Chart(line_data)
        assert chart._backend_type == BackendType.LIGHTWEIGHT

    def test_create_with_large_data_selects_webgl(self, tick_data):
        """Large datasets auto-select WebGL backend."""
        chart = Chart(tick_data)
        assert chart._backend_type == BackendType.WEBGL

    def test_create_with_forecast_data_selects_canvas(self, forecast_paths):
        """Forecast data auto-selects canvas backend."""
        forecast_paths["historical"] = np.array([100, 101, 102, 103, 104])
        chart = Chart(forecast_paths)
        assert chart._backend_type == BackendType.CANVAS

    def test_create_with_multiple_dataframes_selects_multipanel(self, multi_panel_data):
        """Multiple DataFrames auto-select multipanel backend."""
        chart = Chart(multi_panel_data)
        assert chart._backend_type == BackendType.MULTIPANEL

    def test_explicit_backend_override(self, daily_ohlc):
        """Explicit backend parameter overrides auto-selection."""
        chart = Chart(daily_ohlc, backend="webgl")
        assert chart._backend_type == BackendType.WEBGL


class TestThemes:
    """Test theme configuration."""

    def test_string_theme(self, daily_ohlc):
        """Theme can be specified as string."""
        chart = Chart(daily_ohlc, theme="dark")
        assert chart.theme.name == "dark"

    def test_theme_instance(self, daily_ohlc):
        """Theme can be specified as Theme instance."""
        chart = Chart(daily_ohlc, theme=wrc.DARK)
        assert chart.theme.name == "dark"

    def test_default_theme(self, daily_ohlc):
        """Default theme is wayy."""
        chart = Chart(daily_ohlc)
        assert chart.theme.name == "wayy"

    def test_invalid_theme_raises(self, daily_ohlc):
        """Invalid theme name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown theme"):
            Chart(daily_ohlc, theme="invalid")


class TestSeriesMethods:
    """Test series addition methods."""

    def test_add_candlestick_auto_detect(self, daily_ohlc):
        """add_candlestick auto-detects column names."""
        chart = Chart()
        chart.add_candlestick(daily_ohlc)
        assert len(chart._backend._series) == 1

    def test_add_candlestick_explicit_cols(self, ohlc_uppercase):
        """add_candlestick works with explicit column names."""
        chart = Chart()
        chart.add_candlestick(
            ohlc_uppercase,
            time_col="Date",
            open_col="Open",
            high_col="High",
            low_col="Low",
            close_col="Close",
        )
        assert len(chart._backend._series) == 1

    def test_add_line_auto_detect(self, line_data):
        """add_line auto-detects column names."""
        chart = Chart()
        chart.add_line(line_data)
        assert len(chart._backend._series) == 1

    def test_add_area(self, line_data):
        """add_area creates area series."""
        chart = Chart()
        chart.add_area(line_data)
        assert len(chart._backend._series) == 1

    def test_add_volume(self, daily_ohlc):
        """add_volume creates volume histogram."""
        chart = Chart()
        chart.add_candlestick(daily_ohlc)
        chart.add_volume(daily_ohlc)
        assert len(chart._backend._series) == 2

    def test_method_chaining(self, daily_ohlc):
        """Methods support chaining."""
        chart = (
            Chart()
            .add_candlestick(daily_ohlc)
            .add_volume(daily_ohlc)
            .add_horizontal_line(100)
        )
        assert len(chart._backend._series) == 2
        assert len(chart._backend._price_lines) == 1


class TestOutput:
    """Test output methods."""

    def test_to_html(self, daily_ohlc):
        """to_html returns HTML string."""
        chart = Chart(daily_ohlc)
        html = chart.to_html()
        assert "<script>" in html
        assert "LightweightCharts" in html

    def test_to_json(self, daily_ohlc):
        """to_json returns valid JSON."""
        chart = Chart(daily_ohlc)
        json_str = chart.to_json()
        data = json.loads(json_str)
        assert "series" in data

    def test_repr_html(self, daily_ohlc):
        """_repr_html_ works for Jupyter."""
        chart = Chart(daily_ohlc)
        html = chart._repr_html_()
        assert "<script>" in html


class TestQuickPlotFunctions:
    """Test quick-plot convenience functions."""

    def test_candlestick_function(self, daily_ohlc):
        """candlestick() creates chart with candlestick series."""
        chart = candlestick(daily_ohlc)
        assert len(chart._backend._series) == 1
        assert chart._backend._series[0].series_type() == "Candlestick"

    def test_line_function(self, line_data):
        """line() creates chart with line series."""
        chart = line(line_data)
        assert len(chart._backend._series) == 1
        assert chart._backend._series[0].series_type() == "Line"

    def test_area_function(self, line_data):
        """area() creates chart with area series."""
        chart = area(line_data)
        assert len(chart._backend._series) == 1
        assert chart._backend._series[0].series_type() == "Area"

    def test_forecast_function(self, forecast_paths):
        """forecast() creates canvas-based forecast chart."""
        paths = forecast_paths["paths"]
        historical = np.array([100, 101, 102, 103, 104])
        chart = forecast(paths, historical)
        assert chart._backend_type == BackendType.CANVAS

    def test_dashboard_function(self, multi_panel_data):
        """dashboard() creates multi-panel chart."""
        chart = dashboard(multi_panel_data)
        assert chart._backend_type == BackendType.MULTIPANEL


class TestDeprecationWarning:
    """Test deprecation warnings for old API."""

    def test_webgl_chart_warning(self, line_data):
        """WebGLChart raises DeprecationWarning."""
        with pytest.warns(DeprecationWarning, match="WebGLChart is deprecated"):
            chart = wrc.WebGLChart()
            chart.add_line(line_data)
