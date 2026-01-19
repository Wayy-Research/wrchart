"""Tests for column auto-detection."""

import polars as pl
import pytest

from wrchart.core.schema import DataSchema


class TestColumnDetection:
    """Test column name detection from DataFrames."""

    def test_detect_standard_names(self, daily_ohlc):
        """Detect standard lowercase column names."""
        schema = DataSchema.detect(daily_ohlc)
        assert schema["time"] == "time"
        assert schema["open"] == "open"
        assert schema["high"] == "high"
        assert schema["low"] == "low"
        assert schema["close"] == "close"
        assert schema["volume"] == "volume"

    def test_detect_uppercase_names(self, ohlc_uppercase):
        """Detect uppercase column names."""
        schema = DataSchema.detect(ohlc_uppercase)
        assert schema["time"] == "Date"
        assert schema["open"] == "Open"
        assert schema["high"] == "High"
        assert schema["low"] == "Low"
        assert schema["close"] == "Close"
        assert schema["volume"] == "Volume"

    def test_detect_short_names(self, ohlc_short_names):
        """Detect short column names (o, h, l, c)."""
        schema = DataSchema.detect(ohlc_short_names)
        assert schema["time"] == "t"
        assert schema["open"] == "o"
        assert schema["high"] == "h"
        assert schema["low"] == "l"
        assert schema["close"] == "c"
        assert schema["volume"] == "v"

    def test_detect_time_value(self, line_data):
        """Detect time-value data."""
        schema = DataSchema.detect(line_data)
        assert schema["time"] == "time"
        assert schema["close"] == "value"  # value is an alias for close
        assert schema["open"] is None
        assert schema["high"] is None
        assert schema["low"] is None

    def test_detect_timestamp_alias(self):
        """Detect timestamp as time alias."""
        df = pl.DataFrame({
            "timestamp": [1, 2, 3],
            "price": [100, 101, 102],
        })
        schema = DataSchema.detect(df)
        assert schema["time"] == "timestamp"
        assert schema["close"] == "price"

    def test_detect_missing_columns(self):
        """Handle missing columns gracefully."""
        df = pl.DataFrame({
            "foo": [1, 2, 3],
            "bar": [100, 101, 102],
        })
        schema = DataSchema.detect(df)
        assert all(v is None for v in schema.values())


class TestChartTypeInference:
    """Test chart type inference from data."""

    def test_has_ohlc(self, daily_ohlc):
        """Detect OHLC data."""
        assert DataSchema.has_ohlc(daily_ohlc) is True

    def test_has_ohlc_missing_column(self, line_data):
        """Line data should not be detected as OHLC."""
        assert DataSchema.has_ohlc(line_data) is False

    def test_has_time_value(self, line_data):
        """Detect time-value data."""
        assert DataSchema.has_time_value(line_data) is True

    def test_infer_candlestick(self, daily_ohlc):
        """Infer candlestick chart type for OHLC data."""
        assert DataSchema.infer_chart_type(daily_ohlc) == "candlestick"

    def test_infer_line(self, line_data):
        """Infer line chart type for time-value data."""
        assert DataSchema.infer_chart_type(line_data) == "line"

    def test_infer_unknown(self):
        """Return unknown for unrecognized data."""
        df = pl.DataFrame({
            "foo": [1, 2, 3],
            "bar": [100, 101, 102],
        })
        assert DataSchema.infer_chart_type(df) == "unknown"


class TestColumnGetters:
    """Test column getter methods."""

    def test_get_time_col_auto(self, daily_ohlc):
        """Auto-detect time column."""
        assert DataSchema.get_time_col(daily_ohlc) == "time"

    def test_get_time_col_explicit(self, daily_ohlc):
        """Explicit time column overrides auto-detect."""
        assert DataSchema.get_time_col(daily_ohlc, explicit="custom") == "custom"

    def test_get_time_col_missing(self):
        """Raise error if time column not found."""
        df = pl.DataFrame({"foo": [1, 2, 3]})
        with pytest.raises(ValueError, match="Could not detect time column"):
            DataSchema.get_time_col(df)

    def test_get_value_col_auto(self, line_data):
        """Auto-detect value column."""
        assert DataSchema.get_value_col(line_data) == "value"

    def test_get_value_col_close(self, daily_ohlc):
        """Detect close column as value."""
        assert DataSchema.get_value_col(daily_ohlc) == "close"

    def test_get_ohlc_cols_auto(self, daily_ohlc):
        """Auto-detect all OHLC columns."""
        cols = DataSchema.get_ohlc_cols(daily_ohlc)
        assert cols["time"] == "time"
        assert cols["open"] == "open"
        assert cols["high"] == "high"
        assert cols["low"] == "low"
        assert cols["close"] == "close"

    def test_get_ohlc_cols_explicit_override(self, daily_ohlc):
        """Explicit columns override auto-detect."""
        cols = DataSchema.get_ohlc_cols(
            daily_ohlc,
            time="custom_time",
            close="custom_close",
        )
        assert cols["time"] == "custom_time"
        assert cols["close"] == "custom_close"
        assert cols["open"] == "open"  # Still auto-detected

    def test_get_ohlc_cols_missing(self, line_data):
        """Raise error if OHLC columns not found."""
        with pytest.raises(ValueError, match="Could not detect columns"):
            DataSchema.get_ohlc_cols(line_data)
