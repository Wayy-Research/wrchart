"""Tests for backend selection logic."""

import numpy as np
import polars as pl
import pytest

from wrchart.core.backends.base import Backend, BackendType


class TestBackendAutoSelection:
    """Test automatic backend selection based on data."""

    def test_none_data_selects_lightweight(self):
        """None data defaults to lightweight backend."""
        backend_type = Backend.select_backend(None, "auto")
        assert backend_type == BackendType.LIGHTWEIGHT

    def test_small_dataframe_selects_lightweight(self, daily_ohlc):
        """Small DataFrames select lightweight backend."""
        backend_type = Backend.select_backend(daily_ohlc, "auto")
        assert backend_type == BackendType.LIGHTWEIGHT

    def test_large_dataframe_selects_webgl(self, tick_data):
        """Large DataFrames (>100k rows) select WebGL backend."""
        backend_type = Backend.select_backend(tick_data, "auto")
        assert backend_type == BackendType.WEBGL

    def test_threshold_boundary(self):
        """Test 100k row threshold."""
        # Just under threshold - lightweight
        small = pl.DataFrame({
            "time": list(range(99_999)),
            "value": [1.0] * 99_999,
        })
        assert Backend.select_backend(small, "auto") == BackendType.LIGHTWEIGHT

        # Just over threshold - WebGL
        large = pl.DataFrame({
            "time": list(range(100_001)),
            "value": [1.0] * 100_001,
        })
        assert Backend.select_backend(large, "auto") == BackendType.WEBGL

    def test_list_of_dataframes_selects_multipanel(self, multi_panel_data):
        """List of DataFrames selects multipanel backend."""
        backend_type = Backend.select_backend(multi_panel_data, "auto")
        assert backend_type == BackendType.MULTIPANEL

    def test_dict_with_paths_selects_canvas(self, forecast_paths):
        """Dict with 'paths' key selects canvas backend."""
        backend_type = Backend.select_backend(forecast_paths, "auto")
        assert backend_type == BackendType.CANVAS


class TestExplicitBackendSelection:
    """Test explicit backend selection."""

    def test_explicit_lightweight(self, daily_ohlc):
        """Explicit 'lightweight' selection."""
        backend_type = Backend.select_backend(daily_ohlc, "lightweight")
        assert backend_type == BackendType.LIGHTWEIGHT

    def test_explicit_webgl(self, daily_ohlc):
        """Explicit 'webgl' selection overrides auto."""
        backend_type = Backend.select_backend(daily_ohlc, "webgl")
        assert backend_type == BackendType.WEBGL

    def test_explicit_canvas(self, daily_ohlc):
        """Explicit 'canvas' selection."""
        backend_type = Backend.select_backend(daily_ohlc, "canvas")
        assert backend_type == BackendType.CANVAS

    def test_explicit_multipanel(self, daily_ohlc):
        """Explicit 'multipanel' selection."""
        backend_type = Backend.select_backend(daily_ohlc, "multipanel")
        assert backend_type == BackendType.MULTIPANEL

    def test_unknown_backend_defaults_to_lightweight(self, daily_ohlc):
        """Unknown backend defaults to lightweight."""
        backend_type = Backend.select_backend(daily_ohlc, "unknown")
        assert backend_type == BackendType.LIGHTWEIGHT
