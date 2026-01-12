"""
Multi-panel chart module for wrchart.

Provides subplot layouts for complex visualizations with multiple
chart types in a single figure.
"""

from wrchart.multipanel.chart import MultiPanelChart
from wrchart.multipanel.panels import (
    Panel,
    LinePanel,
    BarPanel,
    HeatmapPanel,
    GaugePanel,
    AreaPanel,
)

__all__ = [
    "MultiPanelChart",
    "Panel",
    "LinePanel",
    "BarPanel",
    "HeatmapPanel",
    "GaugePanel",
    "AreaPanel",
]
