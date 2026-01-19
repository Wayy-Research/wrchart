"""
Drawing tools for chart annotations.

Provides TradingView-style drawing tools for programmatic and
interactive chart annotations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import uuid


@dataclass
class BaseDrawing(ABC):
    """
    Base class for all drawing tools.

    Provides common properties and serialization methods.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    visible: bool = True
    locked: bool = False
    z_index: int = 0
    color: Optional[str] = None
    line_width: int = 1
    line_style: str = "solid"  # solid, dashed, dotted

    @property
    @abstractmethod
    def drawing_type(self) -> str:
        """Return the drawing type name."""
        pass

    @abstractmethod
    def to_js_config(self) -> Dict[str, Any]:
        """Convert to JavaScript configuration."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON export."""
        config = self.to_js_config()
        config["id"] = self.id
        config["visible"] = self.visible
        config["locked"] = self.locked
        config["zIndex"] = self.z_index
        return config

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseDrawing":
        """Deserialize from dictionary."""
        raise NotImplementedError("Subclasses must implement from_dict")

    def _line_style_value(self) -> int:
        """Convert line style string to numeric value."""
        return {"solid": 0, "dashed": 1, "dotted": 2}.get(self.line_style, 0)


@dataclass
class HorizontalLine(BaseDrawing):
    """
    Horizontal line at a specific price level.

    Useful for support/resistance levels, targets, stops.
    """

    price: float = 0.0
    label: Optional[str] = None
    label_visible: bool = True

    @property
    def drawing_type(self) -> str:
        return "horizontal_line"

    def to_js_config(self) -> Dict[str, Any]:
        """Convert to Lightweight Charts price line config."""
        return {
            "type": self.drawing_type,
            "price": self.price,
            "color": self.color or "#888888",
            "lineWidth": self.line_width,
            "lineStyle": self._line_style_value(),
            "axisLabelVisible": self.label_visible,
            "title": self.label or "",
        }


@dataclass
class VerticalLine(BaseDrawing):
    """
    Vertical line at a specific time point.

    Useful for marking events, dates, or time boundaries.
    """

    time: Any = None
    label: Optional[str] = None
    label_visible: bool = True

    @property
    def drawing_type(self) -> str:
        return "vertical_line"

    def to_js_config(self) -> Dict[str, Any]:
        return {
            "type": self.drawing_type,
            "time": self.time,
            "color": self.color or "#888888",
            "lineWidth": self.line_width,
            "lineStyle": self._line_style_value(),
            "labelVisible": self.label_visible,
            "label": self.label or "",
        }


@dataclass
class TrendLine(BaseDrawing):
    """
    Trend line connecting two points.
    """

    start_time: Any = None
    start_price: float = 0.0
    end_time: Any = None
    end_price: float = 0.0
    extend_right: bool = False
    extend_left: bool = False

    @property
    def drawing_type(self) -> str:
        return "trend_line"

    def to_js_config(self) -> Dict[str, Any]:
        return {
            "type": self.drawing_type,
            "start": {"time": self.start_time, "price": self.start_price},
            "end": {"time": self.end_time, "price": self.end_price},
            "color": self.color or "#888888",
            "lineWidth": self.line_width,
            "lineStyle": self._line_style_value(),
            "extendRight": self.extend_right,
            "extendLeft": self.extend_left,
        }


@dataclass
class Ray(BaseDrawing):
    """
    Ray extending from a point in one direction.
    """

    start_time: Any = None
    start_price: float = 0.0
    end_time: Any = None
    end_price: float = 0.0

    @property
    def drawing_type(self) -> str:
        return "ray"

    def to_js_config(self) -> Dict[str, Any]:
        return {
            "type": self.drawing_type,
            "start": {"time": self.start_time, "price": self.start_price},
            "end": {"time": self.end_time, "price": self.end_price},
            "color": self.color or "#888888",
            "lineWidth": self.line_width,
            "lineStyle": self._line_style_value(),
        }


@dataclass
class Rectangle(BaseDrawing):
    """
    Rectangle highlighting a price/time zone.
    """

    start_time: Any = None
    start_price: float = 0.0
    end_time: Any = None
    end_price: float = 0.0
    fill_color: Optional[str] = None
    fill_opacity: float = 0.2

    @property
    def drawing_type(self) -> str:
        return "rectangle"

    def to_js_config(self) -> Dict[str, Any]:
        return {
            "type": self.drawing_type,
            "start": {"time": self.start_time, "price": self.start_price},
            "end": {"time": self.end_time, "price": self.end_price},
            "borderColor": self.color or "#888888",
            "borderWidth": self.line_width,
            "fillColor": self.fill_color or self.color or "#888888",
            "fillOpacity": self.fill_opacity,
        }


@dataclass
class Arrow(BaseDrawing):
    """
    Arrow pointing to a specific location.
    """

    time: Any = None
    price: float = 0.0
    direction: str = "up"  # up, down, left, right
    size: int = 1

    @property
    def drawing_type(self) -> str:
        return "arrow"

    def to_js_config(self) -> Dict[str, Any]:
        return {
            "type": self.drawing_type,
            "time": self.time,
            "price": self.price,
            "direction": self.direction,
            "color": self.color or "#888888",
            "size": self.size,
        }


@dataclass
class Text(BaseDrawing):
    """
    Text label at a specific location.
    """

    time: Any = None
    price: float = 0.0
    text: str = ""
    font_size: int = 12
    background: Optional[str] = None
    background_opacity: float = 0.8

    @property
    def drawing_type(self) -> str:
        return "text"

    def to_js_config(self) -> Dict[str, Any]:
        return {
            "type": self.drawing_type,
            "time": self.time,
            "price": self.price,
            "text": self.text,
            "color": self.color or "#000000",
            "fontSize": self.font_size,
            "background": self.background,
            "backgroundOpacity": self.background_opacity,
        }


@dataclass
class PriceRange(BaseDrawing):
    """
    Price range measurement between two points.

    Shows the price difference and percentage change.
    """

    start_time: Any = None
    start_price: float = 0.0
    end_time: Any = None
    end_price: float = 0.0
    show_percentage: bool = True
    show_pips: bool = False

    @property
    def drawing_type(self) -> str:
        return "price_range"

    @property
    def price_diff(self) -> float:
        """Calculate price difference."""
        return self.end_price - self.start_price

    @property
    def percentage_change(self) -> float:
        """Calculate percentage change."""
        if self.start_price == 0:
            return 0
        return (self.price_diff / self.start_price) * 100

    def to_js_config(self) -> Dict[str, Any]:
        return {
            "type": self.drawing_type,
            "start": {"time": self.start_time, "price": self.start_price},
            "end": {"time": self.end_time, "price": self.end_price},
            "color": self.color or "#888888",
            "lineWidth": self.line_width,
            "priceDiff": self.price_diff,
            "percentageChange": self.percentage_change,
            "showPercentage": self.show_percentage,
            "showPips": self.show_pips,
        }


@dataclass
class FibonacciRetracement(BaseDrawing):
    """
    Fibonacci retracement levels between two price points.

    Standard levels: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%
    """

    start_time: Any = None
    start_price: float = 0.0
    end_time: Any = None
    end_price: float = 0.0
    levels: List[float] = field(default_factory=lambda: [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0])
    show_labels: bool = True
    show_prices: bool = True
    extend_lines: bool = False

    @property
    def drawing_type(self) -> str:
        return "fibonacci_retracement"

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
        return {
            "type": self.drawing_type,
            "start": {"time": self.start_time, "price": self.start_price},
            "end": {"time": self.end_time, "price": self.end_price},
            "color": self.color or "#888888",
            "lineWidth": self.line_width,
            "levels": self.get_level_prices(),
            "showLabels": self.show_labels,
            "showPrices": self.show_prices,
            "extendLines": self.extend_lines,
        }


@dataclass
class FibonacciExtension(BaseDrawing):
    """
    Fibonacci extension levels using three points.

    Common extension levels: 100%, 127.2%, 161.8%, 200%, 261.8%
    """

    point1_time: Any = None
    point1_price: float = 0.0
    point2_time: Any = None
    point2_price: float = 0.0
    point3_time: Any = None
    point3_price: float = 0.0
    levels: List[float] = field(default_factory=lambda: [1.0, 1.272, 1.618, 2.0, 2.618])
    show_labels: bool = True
    show_prices: bool = True

    @property
    def drawing_type(self) -> str:
        return "fibonacci_extension"

    def get_level_prices(self) -> List[Dict[str, Any]]:
        """Calculate price at each extension level."""
        # Extension is calculated from point3 using the distance between point1 and point2
        move = self.point2_price - self.point1_price
        return [
            {
                "level": level,
                "price": self.point3_price + (move * level),
                "label": f"{level * 100:.1f}%",
            }
            for level in self.levels
        ]

    def to_js_config(self) -> Dict[str, Any]:
        return {
            "type": self.drawing_type,
            "point1": {"time": self.point1_time, "price": self.point1_price},
            "point2": {"time": self.point2_time, "price": self.point2_price},
            "point3": {"time": self.point3_time, "price": self.point3_price},
            "color": self.color or "#888888",
            "lineWidth": self.line_width,
            "levels": self.get_level_prices(),
            "showLabels": self.show_labels,
            "showPrices": self.show_prices,
        }


# -------------------------------------------------------------------------
# Drawing Serialization Helpers
# -------------------------------------------------------------------------

def export_drawings(drawings: List[BaseDrawing]) -> str:
    """Export a list of drawings to JSON."""
    return json.dumps([d.to_dict() for d in drawings])


def import_drawings(json_str: str) -> List[Dict[str, Any]]:
    """Import drawings from JSON (returns dicts, not objects yet)."""
    return json.loads(json_str)
