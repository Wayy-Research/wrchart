"""
Series types for wrchart.

Each series type handles its own data format and rendering configuration.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import polars as pl


@dataclass
class SeriesOptions:
    """Base options for all series types."""

    title: str = ""
    visible: bool = True
    price_scale_id: str = "right"
    price_line_visible: bool = True
    last_value_visible: bool = True


class BaseSeries(ABC):
    """Abstract base class for all series types."""

    def __init__(
        self,
        data: Optional[pl.DataFrame] = None,
        options: Optional[SeriesOptions] = None,
    ):
        self.data = data
        self.options = options or SeriesOptions()
        self._id: Optional[str] = None

    @abstractmethod
    def series_type(self) -> str:
        """Return the Lightweight Charts series type name."""
        pass

    @abstractmethod
    def to_js_data(self) -> List[Dict[str, Any]]:
        """Convert Polars data to JS-compatible format."""
        pass

    @abstractmethod
    def to_js_options(self, theme: Optional[Any] = None) -> Dict[str, Any]:
        """Get series options for Lightweight Charts."""
        pass

    def set_data(self, data: pl.DataFrame) -> "BaseSeries":
        """Set the data for this series."""
        self.data = data
        return self

    def _time_to_js(self, time_col: pl.Series) -> List[Any]:
        """Convert time column to JS-compatible format."""
        # Handle different time types
        if time_col.dtype == pl.Datetime:
            # Convert to Unix timestamp (seconds)
            return (time_col.cast(pl.Int64) // 1_000_000_000).to_list()
        elif time_col.dtype == pl.Date:
            # Convert date to string format YYYY-MM-DD
            return time_col.cast(pl.Utf8).to_list()
        elif time_col.dtype in [pl.Int64, pl.Int32, pl.Float64]:
            # Already numeric, assume Unix timestamp
            return time_col.to_list()
        else:
            # Try to convert to string
            return time_col.cast(pl.Utf8).to_list()


@dataclass
class CandlestickOptions(SeriesOptions):
    """Options specific to candlestick series."""

    up_color: Optional[str] = None
    down_color: Optional[str] = None
    border_up_color: Optional[str] = None
    border_down_color: Optional[str] = None
    wick_up_color: Optional[str] = None
    wick_down_color: Optional[str] = None
    border_visible: bool = True
    wick_visible: bool = True


class CandlestickSeries(BaseSeries):
    """OHLC candlestick chart series."""

    def __init__(
        self,
        data: Optional[pl.DataFrame] = None,
        time_col: str = "time",
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        options: Optional[CandlestickOptions] = None,
    ):
        super().__init__(data, options or CandlestickOptions())
        self.time_col = time_col
        self.open_col = open_col
        self.high_col = high_col
        self.low_col = low_col
        self.close_col = close_col

    def series_type(self) -> str:
        return "Candlestick"

    def to_js_data(self) -> List[Dict[str, Any]]:
        if self.data is None:
            return []

        times = self._time_to_js(self.data[self.time_col])
        opens = self.data[self.open_col].to_list()
        highs = self.data[self.high_col].to_list()
        lows = self.data[self.low_col].to_list()
        closes = self.data[self.close_col].to_list()

        return [
            {"time": t, "open": o, "high": h, "low": l, "close": c}
            for t, o, h, l, c in zip(times, opens, highs, lows, closes)
        ]

    def to_js_options(self, theme: Optional[Any] = None) -> Dict[str, Any]:
        opts = self.options
        result = {
            "title": opts.title,
            "visible": opts.visible,
            "priceScaleId": opts.price_scale_id,
            "priceLineVisible": opts.price_line_visible,
            "lastValueVisible": opts.last_value_visible,
        }

        # Apply theme defaults, then override with explicit options
        if theme:
            theme_opts = theme.to_candlestick_options()
            result.update(theme_opts)

        if isinstance(opts, CandlestickOptions):
            if opts.up_color:
                result["upColor"] = opts.up_color
            if opts.down_color:
                result["downColor"] = opts.down_color
            if opts.border_up_color:
                result["borderUpColor"] = opts.border_up_color
            if opts.border_down_color:
                result["borderDownColor"] = opts.border_down_color
            if opts.wick_up_color:
                result["wickUpColor"] = opts.wick_up_color
            if opts.wick_down_color:
                result["wickDownColor"] = opts.wick_down_color
            result["borderVisible"] = opts.border_visible
            result["wickVisible"] = opts.wick_visible

        return result


@dataclass
class LineOptions(SeriesOptions):
    """Options specific to line series."""

    color: Optional[str] = None
    line_width: int = 2
    line_style: int = 0  # 0=solid, 1=dotted, 2=dashed, 3=large dashed
    line_type: int = 0  # 0=simple, 1=with steps, 2=curved
    crosshair_marker_visible: bool = True
    crosshair_marker_radius: int = 4


class LineSeries(BaseSeries):
    """Line chart series."""

    def __init__(
        self,
        data: Optional[pl.DataFrame] = None,
        time_col: str = "time",
        value_col: str = "value",
        options: Optional[LineOptions] = None,
    ):
        super().__init__(data, options or LineOptions())
        self.time_col = time_col
        self.value_col = value_col

    def series_type(self) -> str:
        return "Line"

    def to_js_data(self) -> List[Dict[str, Any]]:
        if self.data is None:
            return []

        times = self._time_to_js(self.data[self.time_col])
        values = self.data[self.value_col].to_list()

        return [{"time": t, "value": v} for t, v in zip(times, values)]

    def to_js_options(self, theme: Optional[Any] = None) -> Dict[str, Any]:
        opts = self.options
        result = {
            "title": opts.title,
            "visible": opts.visible,
            "priceScaleId": opts.price_scale_id,
            "priceLineVisible": opts.price_line_visible,
            "lastValueVisible": opts.last_value_visible,
        }

        if isinstance(opts, LineOptions):
            result["color"] = opts.color or (
                theme.colors.line_primary if theme else "#000000"
            )
            result["lineWidth"] = opts.line_width
            result["lineStyle"] = opts.line_style
            result["lineType"] = opts.line_type
            result["crosshairMarkerVisible"] = opts.crosshair_marker_visible
            result["crosshairMarkerRadius"] = opts.crosshair_marker_radius

        return result


@dataclass
class AreaOptions(SeriesOptions):
    """Options specific to area series."""

    line_color: Optional[str] = None
    top_color: Optional[str] = None
    bottom_color: Optional[str] = None
    line_width: int = 2
    line_style: int = 0
    crosshair_marker_visible: bool = True


class AreaSeries(BaseSeries):
    """Area chart series (line with filled area below)."""

    def __init__(
        self,
        data: Optional[pl.DataFrame] = None,
        time_col: str = "time",
        value_col: str = "value",
        options: Optional[AreaOptions] = None,
    ):
        super().__init__(data, options or AreaOptions())
        self.time_col = time_col
        self.value_col = value_col

    def series_type(self) -> str:
        return "Area"

    def to_js_data(self) -> List[Dict[str, Any]]:
        if self.data is None:
            return []

        times = self._time_to_js(self.data[self.time_col])
        values = self.data[self.value_col].to_list()

        return [{"time": t, "value": v} for t, v in zip(times, values)]

    def to_js_options(self, theme: Optional[Any] = None) -> Dict[str, Any]:
        opts = self.options
        base_color = theme.colors.line_primary if theme else "#000000"

        result = {
            "title": opts.title,
            "visible": opts.visible,
            "priceScaleId": opts.price_scale_id,
            "priceLineVisible": opts.price_line_visible,
            "lastValueVisible": opts.last_value_visible,
        }

        if isinstance(opts, AreaOptions):
            result["lineColor"] = opts.line_color or base_color
            result["topColor"] = opts.top_color or f"{base_color}40"  # 25% opacity
            result["bottomColor"] = opts.bottom_color or f"{base_color}00"  # 0% opacity
            result["lineWidth"] = opts.line_width
            result["lineStyle"] = opts.line_style
            result["crosshairMarkerVisible"] = opts.crosshair_marker_visible

        return result


@dataclass
class HistogramOptions(SeriesOptions):
    """Options specific to histogram series."""

    color: Optional[str] = None
    base: float = 0


class HistogramSeries(BaseSeries):
    """Histogram/bar chart series (used for volume, etc.)."""

    def __init__(
        self,
        data: Optional[pl.DataFrame] = None,
        time_col: str = "time",
        value_col: str = "value",
        color_col: Optional[str] = None,
        options: Optional[HistogramOptions] = None,
    ):
        super().__init__(data, options or HistogramOptions())
        self.time_col = time_col
        self.value_col = value_col
        self.color_col = color_col

    def series_type(self) -> str:
        return "Histogram"

    def to_js_data(self) -> List[Dict[str, Any]]:
        if self.data is None:
            return []

        times = self._time_to_js(self.data[self.time_col])
        values = self.data[self.value_col].to_list()

        if self.color_col and self.color_col in self.data.columns:
            colors = self.data[self.color_col].to_list()
            return [
                {"time": t, "value": v, "color": c}
                for t, v, c in zip(times, values, colors)
            ]
        else:
            return [{"time": t, "value": v} for t, v in zip(times, values)]

    def to_js_options(self, theme: Optional[Any] = None) -> Dict[str, Any]:
        opts = self.options
        result = {
            "title": opts.title,
            "visible": opts.visible,
            "priceScaleId": opts.price_scale_id,
            "priceLineVisible": opts.price_line_visible,
            "lastValueVisible": opts.last_value_visible,
        }

        if isinstance(opts, HistogramOptions):
            result["color"] = opts.color or (
                theme.colors.volume_up if theme else "#e0e0e0"
            )
            result["base"] = opts.base

        return result


@dataclass
class ScatterOptions(SeriesOptions):
    """Options specific to scatter/marker series."""

    color: Optional[str] = None
    size: int = 4


class ScatterSeries(BaseSeries):
    """
    Scatter plot series for tick data visualization.

    Uses line series with markers and no connecting lines.
    """

    def __init__(
        self,
        data: Optional[pl.DataFrame] = None,
        time_col: str = "time",
        value_col: str = "value",
        options: Optional[ScatterOptions] = None,
    ):
        super().__init__(data, options or ScatterOptions())
        self.time_col = time_col
        self.value_col = value_col

    def series_type(self) -> str:
        # Scatter is implemented as a line with no line, just markers
        return "Line"

    def to_js_data(self) -> List[Dict[str, Any]]:
        if self.data is None:
            return []

        times = self._time_to_js(self.data[self.time_col])
        values = self.data[self.value_col].to_list()

        return [{"time": t, "value": v} for t, v in zip(times, values)]

    def to_js_options(self, theme: Optional[Any] = None) -> Dict[str, Any]:
        opts = self.options
        result = {
            "title": opts.title,
            "visible": opts.visible,
            "priceScaleId": opts.price_scale_id,
            "priceLineVisible": opts.price_line_visible,
            "lastValueVisible": opts.last_value_visible,
            # Scatter-specific: no line, just markers
            "lineWidth": 0,
            "lineVisible": False,
            "crosshairMarkerVisible": True,
        }

        if isinstance(opts, ScatterOptions):
            result["color"] = opts.color or (
                theme.colors.line_primary if theme else "#000000"
            )
            result["crosshairMarkerRadius"] = opts.size

        return result
