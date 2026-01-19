"""Tests for drawing tools."""

import json
import pytest

from wrchart.drawing.tools import (
    BaseDrawing,
    HorizontalLine,
    VerticalLine,
    TrendLine,
    Ray,
    Rectangle,
    Arrow,
    Text,
    PriceRange,
    FibonacciRetracement,
    FibonacciExtension,
    export_drawings,
    import_drawings,
)


class TestHorizontalLine:
    """Test HorizontalLine drawing."""

    def test_creates_with_price(self):
        """Create horizontal line with price."""
        line = HorizontalLine(price=100.0)
        assert line.price == 100.0
        assert line.drawing_type == "horizontal_line"

    def test_to_js_config(self):
        """Convert to JS config."""
        line = HorizontalLine(price=100.0, color="#ff0000", label="Support")
        config = line.to_js_config()
        assert config["price"] == 100.0
        assert config["color"] == "#ff0000"
        assert config["title"] == "Support"

    def test_serialization(self):
        """Serialize to JSON."""
        line = HorizontalLine(price=100.0)
        json_str = line.to_json()
        data = json.loads(json_str)
        assert data["price"] == 100.0
        assert "id" in data


class TestVerticalLine:
    """Test VerticalLine drawing."""

    def test_creates_with_time(self):
        """Create vertical line with time."""
        line = VerticalLine(time=1234567890)
        assert line.time == 1234567890
        assert line.drawing_type == "vertical_line"

    def test_to_js_config(self):
        """Convert to JS config."""
        line = VerticalLine(time=1234567890, color="#00ff00", label="Event")
        config = line.to_js_config()
        assert config["time"] == 1234567890
        assert config["color"] == "#00ff00"
        assert config["label"] == "Event"


class TestTrendLine:
    """Test TrendLine drawing."""

    def test_creates_with_points(self):
        """Create trend line with start/end points."""
        line = TrendLine(
            start_time=100, start_price=50.0,
            end_time=200, end_price=60.0,
        )
        assert line.start_price == 50.0
        assert line.end_price == 60.0
        assert line.drawing_type == "trend_line"

    def test_extend_options(self):
        """Test extend left/right options."""
        line = TrendLine(
            start_time=100, start_price=50.0,
            end_time=200, end_price=60.0,
            extend_right=True, extend_left=True,
        )
        config = line.to_js_config()
        assert config["extendRight"] is True
        assert config["extendLeft"] is True


class TestRay:
    """Test Ray drawing."""

    def test_creates_with_points(self):
        """Create ray with start/end points."""
        ray = Ray(
            start_time=100, start_price=50.0,
            end_time=200, end_price=60.0,
        )
        assert ray.drawing_type == "ray"


class TestRectangle:
    """Test Rectangle drawing."""

    def test_creates_with_bounds(self):
        """Create rectangle with bounds."""
        rect = Rectangle(
            start_time=100, start_price=50.0,
            end_time=200, end_price=60.0,
        )
        assert rect.drawing_type == "rectangle"

    def test_fill_opacity(self):
        """Test fill opacity option."""
        rect = Rectangle(
            start_time=100, start_price=50.0,
            end_time=200, end_price=60.0,
            fill_opacity=0.5,
        )
        config = rect.to_js_config()
        assert config["fillOpacity"] == 0.5


class TestArrow:
    """Test Arrow drawing."""

    def test_creates_with_position(self):
        """Create arrow with position."""
        arrow = Arrow(time=100, price=50.0, direction="up")
        assert arrow.drawing_type == "arrow"
        assert arrow.direction == "up"

    def test_directions(self):
        """Test all arrow directions."""
        for direction in ["up", "down", "left", "right"]:
            arrow = Arrow(time=100, price=50.0, direction=direction)
            config = arrow.to_js_config()
            assert config["direction"] == direction


class TestText:
    """Test Text drawing."""

    def test_creates_with_text(self):
        """Create text label."""
        text = Text(time=100, price=50.0, text="Hello")
        assert text.drawing_type == "text"
        assert text.text == "Hello"

    def test_font_size(self):
        """Test font size option."""
        text = Text(time=100, price=50.0, text="Hello", font_size=16)
        config = text.to_js_config()
        assert config["fontSize"] == 16


class TestPriceRange:
    """Test PriceRange drawing."""

    def test_creates_with_range(self):
        """Create price range."""
        pr = PriceRange(
            start_time=100, start_price=50.0,
            end_time=200, end_price=60.0,
        )
        assert pr.drawing_type == "price_range"

    def test_price_diff(self):
        """Calculate price difference."""
        pr = PriceRange(
            start_time=100, start_price=50.0,
            end_time=200, end_price=60.0,
        )
        assert pr.price_diff == 10.0

    def test_percentage_change(self):
        """Calculate percentage change."""
        pr = PriceRange(
            start_time=100, start_price=100.0,
            end_time=200, end_price=110.0,
        )
        assert pr.percentage_change == 10.0

    def test_zero_start_price(self):
        """Handle zero start price."""
        pr = PriceRange(
            start_time=100, start_price=0.0,
            end_time=200, end_price=10.0,
        )
        assert pr.percentage_change == 0


class TestFibonacciRetracement:
    """Test FibonacciRetracement drawing."""

    def test_creates_with_points(self):
        """Create Fibonacci retracement."""
        fib = FibonacciRetracement(
            start_time=100, start_price=100.0,
            end_time=200, end_price=200.0,
        )
        assert fib.drawing_type == "fibonacci_retracement"

    def test_default_levels(self):
        """Check default Fibonacci levels."""
        fib = FibonacciRetracement(
            start_time=100, start_price=100.0,
            end_time=200, end_price=200.0,
        )
        assert 0.618 in fib.levels
        assert 0.382 in fib.levels

    def test_level_prices(self):
        """Calculate prices at Fibonacci levels."""
        fib = FibonacciRetracement(
            start_time=100, start_price=100.0,
            end_time=200, end_price=200.0,
        )
        level_prices = fib.get_level_prices()
        # 0% level should be at start price
        assert level_prices[0]["price"] == 100.0
        # 100% level should be at end price
        assert level_prices[-1]["price"] == 200.0
        # 50% level should be at midpoint
        mid_level = next(l for l in level_prices if l["level"] == 0.5)
        assert mid_level["price"] == 150.0


class TestFibonacciExtension:
    """Test FibonacciExtension drawing."""

    def test_creates_with_three_points(self):
        """Create Fibonacci extension with three points."""
        fib = FibonacciExtension(
            point1_time=100, point1_price=100.0,
            point2_time=150, point2_price=150.0,
            point3_time=200, point3_price=125.0,
        )
        assert fib.drawing_type == "fibonacci_extension"

    def test_extension_level_prices(self):
        """Calculate extension prices."""
        fib = FibonacciExtension(
            point1_time=100, point1_price=100.0,
            point2_time=150, point2_price=150.0,  # 50 point move up
            point3_time=200, point3_price=125.0,  # Retracement point
        )
        level_prices = fib.get_level_prices()
        # 100% extension: 125 + 50*1.0 = 175
        level_100 = next(l for l in level_prices if l["level"] == 1.0)
        assert level_100["price"] == 175.0


class TestSerialization:
    """Test serialization and export."""

    def test_export_drawings(self):
        """Export multiple drawings to JSON."""
        drawings = [
            HorizontalLine(price=100.0),
            TrendLine(start_time=100, start_price=50.0, end_time=200, end_price=60.0),
        ]
        json_str = export_drawings(drawings)
        data = json.loads(json_str)
        assert len(data) == 2
        assert data[0]["type"] == "horizontal_line"
        assert data[1]["type"] == "trend_line"

    def test_import_drawings(self):
        """Import drawings from JSON."""
        json_str = '[{"type": "horizontal_line", "price": 100.0}]'
        data = import_drawings(json_str)
        assert len(data) == 1
        assert data[0]["price"] == 100.0

    def test_unique_ids(self):
        """Each drawing gets a unique ID."""
        line1 = HorizontalLine(price=100.0)
        line2 = HorizontalLine(price=200.0)
        assert line1.id != line2.id

    def test_to_dict_includes_metadata(self):
        """to_dict includes visibility and lock state."""
        line = HorizontalLine(price=100.0, visible=False, locked=True)
        data = line.to_dict()
        assert data["visible"] is False
        assert data["locked"] is True


class TestLineStyles:
    """Test line style conversion."""

    def test_solid_style(self):
        """Solid line style."""
        line = HorizontalLine(price=100.0, line_style="solid")
        config = line.to_js_config()
        assert config["lineStyle"] == 0

    def test_dashed_style(self):
        """Dashed line style."""
        line = HorizontalLine(price=100.0, line_style="dashed")
        config = line.to_js_config()
        assert config["lineStyle"] == 1

    def test_dotted_style(self):
        """Dotted line style."""
        line = HorizontalLine(price=100.0, line_style="dotted")
        config = line.to_js_config()
        assert config["lineStyle"] == 2
