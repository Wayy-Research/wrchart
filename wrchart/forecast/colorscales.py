"""
Colorscale definitions for density-based visualizations.

Provides perceptually uniform color scales for path density visualization.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ColorStop:
    """A single stop in a colorscale."""

    position: float  # 0.0 to 1.0
    rgb: Tuple[int, int, int]


@dataclass
class Colorscale:
    """A colorscale for mapping values to colors."""

    name: str
    stops: List[ColorStop]

    def to_color(self, value: float) -> str:
        """
        Convert a value (0-1) to an RGB color string.

        Args:
            value: Value between 0 and 1

        Returns:
            RGB color string like 'rgb(255, 128, 0)'
        """
        value = max(0.0, min(1.0, value))

        # Find the two stops to interpolate between
        for i in range(len(self.stops) - 1):
            s0 = self.stops[i]
            s1 = self.stops[i + 1]

            if s0.position <= value <= s1.position:
                # Linear interpolation
                t = (value - s0.position) / (s1.position - s0.position)
                r = int(s0.rgb[0] + t * (s1.rgb[0] - s0.rgb[0]))
                g = int(s0.rgb[1] + t * (s1.rgb[1] - s0.rgb[1]))
                b = int(s0.rgb[2] + t * (s1.rgb[2] - s0.rgb[2]))
                return f"rgb({r},{g},{b})"

        # Fallback to last color
        last = self.stops[-1].rgb
        return f"rgb({last[0]},{last[1]},{last[2]})"

    def to_rgba(self, value: float, alpha: float = 1.0) -> str:
        """
        Convert a value (0-1) to an RGBA color string.

        Args:
            value: Value between 0 and 1
            alpha: Alpha transparency (0-1)

        Returns:
            RGBA color string like 'rgba(255, 128, 0, 0.5)'
        """
        value = max(0.0, min(1.0, value))
        alpha = max(0.0, min(1.0, alpha))

        for i in range(len(self.stops) - 1):
            s0 = self.stops[i]
            s1 = self.stops[i + 1]

            if s0.position <= value <= s1.position:
                t = (value - s0.position) / (s1.position - s0.position)
                r = int(s0.rgb[0] + t * (s1.rgb[0] - s0.rgb[0]))
                g = int(s0.rgb[1] + t * (s1.rgb[1] - s0.rgb[1]))
                b = int(s0.rgb[2] + t * (s1.rgb[2] - s0.rgb[2]))
                return f"rgba({r},{g},{b},{alpha:.2f})"

        last = self.stops[-1].rgb
        return f"rgba({last[0]},{last[1]},{last[2]},{alpha:.2f})"

    def to_js_array(self) -> List[List]:
        """
        Convert to JavaScript-compatible array format.

        Returns:
            List of [position, [r, g, b]] pairs
        """
        return [[stop.position, list(stop.rgb)] for stop in self.stops]


# Pre-defined colorscales
VIRIDIS = Colorscale(
    name="viridis",
    stops=[
        ColorStop(0.0, (68, 1, 84)),  # Dark purple
        ColorStop(0.25, (59, 82, 139)),  # Blue-purple
        ColorStop(0.5, (33, 145, 140)),  # Teal
        ColorStop(0.75, (94, 201, 98)),  # Green
        ColorStop(1.0, (253, 231, 37)),  # Yellow
    ],
)

PLASMA = Colorscale(
    name="plasma",
    stops=[
        ColorStop(0.0, (13, 8, 135)),  # Dark blue
        ColorStop(0.25, (126, 3, 168)),  # Purple
        ColorStop(0.5, (204, 71, 120)),  # Pink
        ColorStop(0.75, (248, 149, 64)),  # Orange
        ColorStop(1.0, (240, 249, 33)),  # Yellow
    ],
)

INFERNO = Colorscale(
    name="inferno",
    stops=[
        ColorStop(0.0, (0, 0, 4)),  # Black
        ColorStop(0.25, (87, 16, 110)),  # Purple
        ColorStop(0.5, (188, 55, 84)),  # Red
        ColorStop(0.75, (249, 142, 9)),  # Orange
        ColorStop(1.0, (252, 255, 164)),  # Yellow-white
    ],
)

HOT = Colorscale(
    name="hot",
    stops=[
        ColorStop(0.0, (10, 10, 40)),  # Dark blue
        ColorStop(0.25, (80, 30, 100)),  # Purple
        ColorStop(0.5, (200, 50, 50)),  # Red
        ColorStop(0.75, (255, 150, 50)),  # Orange
        ColorStop(1.0, (255, 255, 200)),  # Light yellow
    ],
)

# Colorscale lookup by name
COLORSCALES = {
    "viridis": VIRIDIS,
    "plasma": PLASMA,
    "inferno": INFERNO,
    "hot": HOT,
}


def get_colorscale(name: str) -> Colorscale:
    """
    Get a colorscale by name.

    Args:
        name: Colorscale name (viridis, plasma, inferno, hot)

    Returns:
        Colorscale instance
    """
    return COLORSCALES.get(name.lower(), VIRIDIS)


def density_to_color(score: float, colorscale: str = "viridis") -> str:
    """
    Convert a density score (0-1) to a color string.

    Args:
        score: Density score between 0 and 1
        colorscale: Name of the colorscale to use

    Returns:
        RGB color string
    """
    scale = get_colorscale(colorscale)
    return scale.to_color(score)
