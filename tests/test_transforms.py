"""Tests for data transforms."""

import polars as pl
import numpy as np
import pytest

from wrchart.transforms import (
    lttb_downsample,
    to_heikin_ashi,
    to_renko,
    to_kagi,
    to_point_and_figure,
    to_line_break,
    to_range_bars,
)


@pytest.fixture
def sample_ohlc():
    """Create sample OHLC data."""
    np.random.seed(42)
    n = 100
    prices = 100 + np.cumsum(np.random.randn(n) * 0.5)

    return pl.DataFrame({
        "time": list(range(n)),
        "open": prices + np.random.randn(n) * 0.1,
        "high": prices + np.abs(np.random.randn(n) * 0.5),
        "low": prices - np.abs(np.random.randn(n) * 0.5),
        "close": prices + np.random.randn(n) * 0.1,
    })


@pytest.fixture
def sample_line_data():
    """Create sample time series data."""
    np.random.seed(42)
    n = 1000
    return pl.DataFrame({
        "time": list(range(n)),
        "value": 100 + np.cumsum(np.random.randn(n) * 0.5),
    })


class TestLTTB:
    """Tests for LTTB downsampling."""

    def test_lttb_reduces_points(self, sample_line_data):
        """LTTB should reduce point count."""
        result = lttb_downsample(sample_line_data, target_points=100)
        assert len(result) == 100

    def test_lttb_preserves_small_data(self, sample_line_data):
        """LTTB should not reduce data smaller than target."""
        small_data = sample_line_data.head(50)
        result = lttb_downsample(small_data, target_points=100)
        assert len(result) == 50

    def test_lttb_preserves_endpoints(self, sample_line_data):
        """LTTB should always keep first and last points."""
        result = lttb_downsample(sample_line_data, target_points=10)
        assert result["time"][0] == sample_line_data["time"][0]
        assert result["time"][-1] == sample_line_data["time"][-1]


class TestHeikinAshi:
    """Tests for Heikin-Ashi transform."""

    def test_heikin_ashi_shape(self, sample_ohlc):
        """Output should have same length as input."""
        result = to_heikin_ashi(sample_ohlc)
        assert len(result) == len(sample_ohlc)

    def test_heikin_ashi_columns(self, sample_ohlc):
        """Output should have standard OHLC columns."""
        result = to_heikin_ashi(sample_ohlc)
        assert "open" in result.columns
        assert "high" in result.columns
        assert "low" in result.columns
        assert "close" in result.columns

    def test_heikin_ashi_high_low_valid(self, sample_ohlc):
        """High should be >= low for all rows."""
        result = to_heikin_ashi(sample_ohlc)
        assert (result["high"] >= result["low"]).all()


class TestRenko:
    """Tests for Renko transform."""

    def test_renko_creates_bricks(self, sample_ohlc):
        """Renko should create at least one brick."""
        result = to_renko(sample_ohlc, brick_size=0.5)
        assert len(result) > 0

    def test_renko_brick_size(self, sample_ohlc):
        """Each brick should have size equal to brick_size."""
        brick_size = 0.5
        result = to_renko(sample_ohlc, brick_size=brick_size)
        for i in range(len(result)):
            brick_range = abs(result["close"][i] - result["open"][i])
            assert abs(brick_range - brick_size) < 0.01


class TestKagi:
    """Tests for Kagi transform."""

    def test_kagi_creates_lines(self, sample_ohlc):
        """Kagi should create at least one line."""
        result = to_kagi(sample_ohlc, reversal_amount=0.5, close_col="close")
        assert len(result) > 0

    def test_kagi_has_line_type(self, sample_ohlc):
        """Kagi should include line type (yang/yin)."""
        result = to_kagi(sample_ohlc, reversal_amount=0.5, close_col="close")
        assert "line_type" in result.columns


class TestPointAndFigure:
    """Tests for Point & Figure transform."""

    def test_pnf_creates_columns(self, sample_ohlc):
        """P&F should create at least one column."""
        result = to_point_and_figure(sample_ohlc, box_size=0.5)
        assert len(result) > 0

    def test_pnf_has_column_type(self, sample_ohlc):
        """P&F should indicate X or O columns."""
        result = to_point_and_figure(sample_ohlc, box_size=0.5)
        assert "column_type" in result.columns
        assert all(t in ["X", "O"] for t in result["column_type"].to_list())


class TestLineBreak:
    """Tests for Line Break transform."""

    def test_line_break_creates_lines(self, sample_ohlc):
        """Line Break should create at least one line."""
        result = to_line_break(sample_ohlc, num_lines=3, close_col="close")
        assert len(result) > 0

    def test_line_break_direction(self, sample_ohlc):
        """Line Break should have direction indicator."""
        result = to_line_break(sample_ohlc, num_lines=3, close_col="close")
        assert "direction" in result.columns


class TestRangeBars:
    """Tests for Range Bars transform."""

    def test_range_bars_creates_bars(self, sample_ohlc):
        """Range Bars should create at least one bar."""
        result = to_range_bars(sample_ohlc, range_size=1.0)
        assert len(result) > 0

    def test_range_bars_consistent_range(self, sample_ohlc):
        """All complete bars should have similar range."""
        range_size = 1.0
        result = to_range_bars(sample_ohlc, range_size=range_size)
        # Check all but last bar (which may be incomplete)
        if len(result) > 1:
            for i in range(len(result) - 1):
                bar_range = result["high"][i] - result["low"][i]
                assert bar_range <= range_size + 0.1
