"""
Chart themes following Wayy Research brand guidelines.

Colors and styling based on:
- Primary: Black #000000, White #FFFFFF
- Accent: Red #E53935
- Grays: #fafafa, #f5f5f5, #e0e0e0, #888888, #555555, #333333
- Fonts: Space Grotesk (sans), JetBrains Mono (mono)
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ThemeColors:
    """Color palette for a theme."""

    # Background
    background: str = "#ffffff"

    # Text
    text_primary: str = "#000000"
    text_secondary: str = "#555555"
    text_muted: str = "#888888"

    # Grid and borders
    grid: str = "#f5f5f5"
    border: str = "#e0e0e0"

    # Candlestick colors
    candle_up: str = "#000000"
    candle_down: str = "#E53935"
    candle_up_border: str = "#000000"
    candle_down_border: str = "#E53935"

    # Wick colors
    wick_up: str = "#000000"
    wick_down: str = "#E53935"

    # Volume colors
    volume_up: str = "#e0e0e0"
    volume_down: str = "#fff5f5"

    # Line colors (for indicators)
    line_primary: str = "#000000"
    line_secondary: str = "#E53935"
    line_tertiary: str = "#888888"

    # Crosshair
    crosshair: str = "#888888"
    crosshair_label_bg: str = "#000000"
    crosshair_label_text: str = "#ffffff"

    # Selection/highlight
    highlight: str = "#E53935"


@dataclass
class ThemeFonts:
    """Font configuration for a theme."""

    family: str = "'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif"
    mono: str = "'JetBrains Mono', 'Fira Code', monospace"
    size_small: str = "11px"
    size_normal: str = "12px"
    size_large: str = "14px"


@dataclass
class ThemeLayout:
    """Layout configuration for a theme."""

    # No rounded corners per Wayy guidelines
    border_radius: int = 0

    # Spacing
    padding: int = 8

    # Grid
    grid_visible: bool = True
    grid_style: str = "solid"  # solid, dashed, dotted

    # Axis
    axis_visible: bool = True
    axis_border_visible: bool = True


@dataclass
class Theme:
    """Complete theme configuration."""

    name: str
    colors: ThemeColors = field(default_factory=ThemeColors)
    fonts: ThemeFonts = field(default_factory=ThemeFonts)
    layout: ThemeLayout = field(default_factory=ThemeLayout)

    def to_lightweight_charts_options(self) -> dict:
        """Convert theme to Lightweight Charts configuration."""
        return {
            "layout": {
                "background": {"type": "solid", "color": self.colors.background},
                "textColor": self.colors.text_primary,
                "fontFamily": self.fonts.family,
                "fontSize": 12,
            },
            "grid": {
                "vertLines": {
                    "color": self.colors.grid,
                    "style": 0 if self.layout.grid_style == "solid" else 1,
                    "visible": self.layout.grid_visible,
                },
                "horzLines": {
                    "color": self.colors.grid,
                    "style": 0 if self.layout.grid_style == "solid" else 1,
                    "visible": self.layout.grid_visible,
                },
            },
            "crosshair": {
                "mode": 1,  # Normal
                "vertLine": {
                    "color": self.colors.crosshair,
                    "width": 1,
                    "style": 1,  # Dashed
                    "labelBackgroundColor": self.colors.crosshair_label_bg,
                },
                "horzLine": {
                    "color": self.colors.crosshair,
                    "width": 1,
                    "style": 1,
                    "labelBackgroundColor": self.colors.crosshair_label_bg,
                },
            },
            "rightPriceScale": {
                "borderColor": self.colors.border,
                "borderVisible": self.layout.axis_border_visible,
            },
            "timeScale": {
                "borderColor": self.colors.border,
                "borderVisible": self.layout.axis_border_visible,
            },
        }

    def to_candlestick_options(self) -> dict:
        """Get candlestick series options for this theme."""
        return {
            "upColor": self.colors.candle_up,
            "downColor": self.colors.candle_down,
            "borderUpColor": self.colors.candle_up_border,
            "borderDownColor": self.colors.candle_down_border,
            "wickUpColor": self.colors.wick_up,
            "wickDownColor": self.colors.wick_down,
        }

    def to_volume_options(self) -> dict:
        """Get volume histogram options for this theme."""
        return {
            "color": self.colors.volume_up,
            "priceFormat": {"type": "volume"},
            "priceScaleId": "",  # Overlay on main pane
        }


# Pre-configured themes

WayyTheme = Theme(
    name="wayy",
    colors=ThemeColors(
        background="#ffffff",
        text_primary="#000000",
        text_secondary="#555555",
        text_muted="#888888",
        grid="#f5f5f5",
        border="#e0e0e0",
        candle_up="#000000",
        candle_down="#E53935",
        candle_up_border="#000000",
        candle_down_border="#E53935",
        wick_up="#000000",
        wick_down="#E53935",
        volume_up="#e0e0e0",
        volume_down="#ffebee",
        line_primary="#000000",
        line_secondary="#E53935",
        line_tertiary="#888888",
        crosshair="#888888",
        crosshair_label_bg="#000000",
        crosshair_label_text="#ffffff",
        highlight="#E53935",
    ),
    fonts=ThemeFonts(
        family="'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif",
        mono="'JetBrains Mono', 'Fira Code', monospace",
    ),
    layout=ThemeLayout(
        border_radius=0,
        grid_visible=True,
        grid_style="solid",
    ),
)


DarkTheme = Theme(
    name="dark",
    colors=ThemeColors(
        background="#1a1a1a",
        text_primary="#ffffff",
        text_secondary="#aaaaaa",
        text_muted="#666666",
        grid="#2a2a2a",
        border="#333333",
        candle_up="#ffffff",
        candle_down="#E53935",
        candle_up_border="#ffffff",
        candle_down_border="#E53935",
        wick_up="#ffffff",
        wick_down="#E53935",
        volume_up="#333333",
        volume_down="#3d1f1f",
        line_primary="#ffffff",
        line_secondary="#E53935",
        line_tertiary="#666666",
        crosshair="#666666",
        crosshair_label_bg="#ffffff",
        crosshair_label_text="#000000",
        highlight="#E53935",
    ),
    fonts=ThemeFonts(
        family="'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif",
        mono="'JetBrains Mono', 'Fira Code', monospace",
    ),
    layout=ThemeLayout(
        border_radius=0,
        grid_visible=True,
        grid_style="solid",
    ),
)


LightTheme = Theme(
    name="light",
    colors=ThemeColors(
        background="#fafafa",
        text_primary="#000000",
        text_secondary="#555555",
        text_muted="#888888",
        grid="#eeeeee",
        border="#e0e0e0",
        candle_up="#26a69a",
        candle_down="#ef5350",
        candle_up_border="#26a69a",
        candle_down_border="#ef5350",
        wick_up="#26a69a",
        wick_down="#ef5350",
        volume_up="#e8f5e9",
        volume_down="#ffebee",
        line_primary="#1976d2",
        line_secondary="#E53935",
        line_tertiary="#888888",
        crosshair="#888888",
        crosshair_label_bg="#333333",
        crosshair_label_text="#ffffff",
        highlight="#1976d2",
    ),
    fonts=ThemeFonts(
        family="'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif",
        mono="'JetBrains Mono', 'Fira Code', monospace",
    ),
    layout=ThemeLayout(
        border_radius=0,
        grid_visible=True,
        grid_style="solid",
    ),
)
