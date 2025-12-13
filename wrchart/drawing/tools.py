"""
Drawing tools for chart annotations.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class HorizontalLine:
    """
    Horizontal line at a specific price level.

    Useful for support/resistance levels, targets, stops.
    """

    price: float
    color: Optional[str] = None
    width: int = 1
    style: str = "solid"  # solid, dashed, dotted
    label: Optional[str] = None
    label_visible: bool = True

    def to_js_config(self) -> Dict[str, Any]:
        """Convert to Lightweight Charts price line config."""
        return {
            "price": self.price,
            "color": self.color or "#888888",
            "lineWidth": self.width,
            "lineStyle": {"solid": 0, "dashed": 1, "dotted": 2}.get(self.style, 0),
            "axisLabelVisible": self.label_visible,
            "title": self.label or "",
        }


@dataclass
class TrendLine:
    """
    Trend line connecting two points.
    """

    start_time: Any
    start_price: float
    end_time: Any
    end_price: float
    color: Optional[str] = None
    width: int = 1
    style: str = "solid"
    extend_right: bool = False
    extend_left: bool = False

    def to_js_config(self) -> Dict[str, Any]:
        """Convert to configuration dict."""
        return {
            "type": "trendline",
            "start": {"time": self.start_time, "price": self.start_price},
            "end": {"time": self.end_time, "price": self.end_price},
            "color": self.color or "#888888",
            "lineWidth": self.width,
            "lineStyle": {"solid": 0, "dashed": 1, "dotted": 2}.get(self.style, 0),
            "extendRight": self.extend_right,
            "extendLeft": self.extend_left,
        }


@dataclass
class Rectangle:
    """
    Rectangle highlighting a price/time zone.
    """

    start_time: Any
    start_price: float
    end_time: Any
    end_price: float
    fill_color: Optional[str] = None
    border_color: Optional[str] = None
    border_width: int = 1
    fill_opacity: float = 0.2

    def to_js_config(self) -> Dict[str, Any]:
        """Convert to configuration dict."""
        return {
            "type": "rectangle",
            "start": {"time": self.start_time, "price": self.start_price},
            "end": {"time": self.end_time, "price": self.end_price},
            "fillColor": self.fill_color or "#888888",
            "borderColor": self.border_color or "#888888",
            "borderWidth": self.border_width,
            "fillOpacity": self.fill_opacity,
        }


@dataclass
class FibonacciRetracement:
    """
    Fibonacci retracement levels between two price points.

    Standard levels: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%
    """

    start_time: Any
    start_price: float
    end_time: Any
    end_price: float
    color: Optional[str] = None
    levels: Optional[List[float]] = None
    show_labels: bool = True
    show_prices: bool = True

    def __post_init__(self):
        if self.levels is None:
            self.levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]

    def get_level_prices(self) -> List[Dict[str, Any]]:
        """Calculate price at each Fibonacci level."""
        diff = self.end_price - self.start_price
        return [
            {
                "level": level,
                "price": self.start_price + (diff * level),
                "label": f"{level * 100:.1f}%",
            }
            for level in self.levels
        ]

    def to_js_config(self) -> Dict[str, Any]:
        """Convert to configuration dict."""
        return {
            "type": "fibonacci",
            "start": {"time": self.start_time, "price": self.start_price},
            "end": {"time": self.end_time, "price": self.end_price},
            "color": self.color or "#888888",
            "levels": self.get_level_prices(),
            "showLabels": self.show_labels,
            "showPrices": self.show_prices,
        }
