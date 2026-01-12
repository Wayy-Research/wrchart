"""
Forecast visualization module for wrchart.

Provides specialized charts for Monte Carlo simulations, probability forecasts,
and time series predictions with confidence intervals.
"""

from wrchart.forecast.chart import ForecastChart
from wrchart.forecast.colorscales import (
    Colorscale,
    VIRIDIS,
    PLASMA,
    INFERNO,
    HOT,
    density_to_color,
)
from wrchart.forecast.utils import (
    compute_path_density,
    compute_path_colors_by_density,
)

__all__ = [
    "ForecastChart",
    "Colorscale",
    "VIRIDIS",
    "PLASMA",
    "INFERNO",
    "HOT",
    "density_to_color",
    "compute_path_density",
    "compute_path_colors_by_density",
]
