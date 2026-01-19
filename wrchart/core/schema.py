"""
Column auto-detection for DataFrames.

Automatically detects OHLCV columns from common naming conventions.
"""

from typing import Dict, List, Optional, Set
import polars as pl


class DataSchema:
    """Auto-detect OHLCV columns from DataFrame column names."""

    # Common aliases for each column type (case-insensitive matching)
    TIME_ALIASES: Set[str] = {
        "time", "timestamp", "date", "datetime", "t", "index", "dt", "ts"
    }
    OPEN_ALIASES: Set[str] = {"open", "o"}
    HIGH_ALIASES: Set[str] = {"high", "h", "hi"}
    LOW_ALIASES: Set[str] = {"low", "l", "lo"}
    CLOSE_ALIASES: Set[str] = {"close", "c", "price", "value", "adj_close", "adjclose"}
    VOLUME_ALIASES: Set[str] = {"volume", "vol", "v"}

    @classmethod
    def detect(cls, df: pl.DataFrame) -> Dict[str, Optional[str]]:
        """
        Detect column mapping from DataFrame.

        Returns dict with keys: time, open, high, low, close, volume
        Values are the detected column names, or None if not found.
        """
        columns = {col.lower(): col for col in df.columns}

        return {
            "time": cls._find_column(columns, cls.TIME_ALIASES),
            "open": cls._find_column(columns, cls.OPEN_ALIASES),
            "high": cls._find_column(columns, cls.HIGH_ALIASES),
            "low": cls._find_column(columns, cls.LOW_ALIASES),
            "close": cls._find_column(columns, cls.CLOSE_ALIASES),
            "volume": cls._find_column(columns, cls.VOLUME_ALIASES),
        }

    @classmethod
    def _find_column(
        cls, columns: Dict[str, str], aliases: Set[str]
    ) -> Optional[str]:
        """Find a column matching any of the aliases."""
        for alias in aliases:
            if alias in columns:
                return columns[alias]
        return None

    @classmethod
    def has_ohlc(cls, df: pl.DataFrame) -> bool:
        """Check if DataFrame has OHLC columns."""
        schema = cls.detect(df)
        return all(
            schema[col] is not None
            for col in ["time", "open", "high", "low", "close"]
        )

    @classmethod
    def has_time_value(cls, df: pl.DataFrame) -> bool:
        """Check if DataFrame has time and value/close columns."""
        schema = cls.detect(df)
        return schema["time"] is not None and schema["close"] is not None

    @classmethod
    def infer_chart_type(cls, df: pl.DataFrame) -> str:
        """
        Infer the best chart type for this DataFrame.

        Returns: "candlestick", "line", or "unknown"
        """
        if cls.has_ohlc(df):
            return "candlestick"
        elif cls.has_time_value(df):
            return "line"
        else:
            return "unknown"

    @classmethod
    def get_time_col(cls, df: pl.DataFrame, explicit: Optional[str] = None) -> str:
        """Get time column name, with optional explicit override."""
        if explicit:
            return explicit
        schema = cls.detect(df)
        if schema["time"]:
            return schema["time"]
        raise ValueError(
            f"Could not detect time column. Columns: {df.columns}. "
            "Specify time column explicitly."
        )

    @classmethod
    def get_value_col(cls, df: pl.DataFrame, explicit: Optional[str] = None) -> str:
        """Get value column name (close/price/value), with optional explicit override."""
        if explicit:
            return explicit
        schema = cls.detect(df)
        if schema["close"]:
            return schema["close"]
        raise ValueError(
            f"Could not detect value column. Columns: {df.columns}. "
            "Specify value column explicitly."
        )

    @classmethod
    def get_ohlc_cols(
        cls,
        df: pl.DataFrame,
        time: Optional[str] = None,
        open_: Optional[str] = None,
        high: Optional[str] = None,
        low: Optional[str] = None,
        close: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Get OHLC column names, with optional explicit overrides.

        Returns dict with keys: time, open, high, low, close
        """
        schema = cls.detect(df)

        result = {
            "time": time or schema["time"],
            "open": open_ or schema["open"],
            "high": high or schema["high"],
            "low": low or schema["low"],
            "close": close or schema["close"],
        }

        missing = [k for k, v in result.items() if v is None]
        if missing:
            raise ValueError(
                f"Could not detect columns: {missing}. Columns: {df.columns}. "
                "Specify these columns explicitly."
            )

        return result
