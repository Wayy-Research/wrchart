"""
Backend renderers for wrchart.

Each backend handles a specific rendering technology:
- LightweightChartsBackend: Interactive charts using TradingView's Lightweight Charts
- WebGLBackend: GPU-accelerated rendering for millions of points
- CanvasBackend: Canvas-based rendering for forecast paths
- MultiPanelBackend: Grid layouts with multiple charts
"""

from wrchart.core.backends.base import Backend, BackendType
from wrchart.core.backends.lightweight import LightweightChartsBackend
from wrchart.core.backends.webgl import WebGLBackend
from wrchart.core.backends.canvas import CanvasBackend
from wrchart.core.backends.multipanel import MultiPanelBackend

__all__ = [
    "Backend",
    "BackendType",
    "LightweightChartsBackend",
    "WebGLBackend",
    "CanvasBackend",
    "MultiPanelBackend",
]
