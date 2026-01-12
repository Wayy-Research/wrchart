"""
Utility functions for forecast visualization.

Provides density computation and path analysis for Monte Carlo simulations.
"""

from typing import Optional, Tuple
import numpy as np


def compute_path_density(
    paths: np.ndarray,
    n_time_bins: int = 50,
    n_price_bins: int = 100,
    probabilities: Optional[np.ndarray] = None,
    sigma: float = 1.5,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute 2D density of paths over time and price.

    Creates a density heatmap showing where Monte Carlo paths
    are most concentrated in time-price space.

    Args:
        paths: Array of shape (n_paths, n_steps)
        n_time_bins: Number of bins along time axis
        n_price_bins: Number of bins along price axis
        probabilities: Optional path probabilities for weighting
        sigma: Gaussian smoothing sigma

    Returns:
        Tuple of (density, time_edges, price_edges)
    """
    n_paths, n_steps = paths.shape

    # Flatten paths to get all (time, price) points
    time_indices = np.tile(np.arange(n_steps), n_paths)
    price_values = paths.flatten()

    # Create weights based on path probabilities
    if probabilities is not None:
        weights = np.repeat(probabilities, n_steps)
    else:
        weights = None

    # Compute 2D histogram
    price_range = (np.min(price_values), np.max(price_values))

    density, time_edges, price_edges = np.histogram2d(
        time_indices,
        price_values,
        bins=[n_time_bins, n_price_bins],
        range=[[0, n_steps], price_range],
        weights=weights,
        density=True,
    )

    # Apply Gaussian smoothing for nicer visualization
    try:
        from scipy.ndimage import gaussian_filter

        density = gaussian_filter(density.T, sigma=sigma)
    except ImportError:
        # Fallback without scipy
        density = density.T

    return density, time_edges, price_edges


def compute_path_colors_by_density(
    paths: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
    method: str = "endpoint",
) -> np.ndarray:
    """
    Compute density scores for each path for color mapping.

    Args:
        paths: Array of shape (n_paths, n_steps)
        probabilities: Optional path probabilities
        method: 'endpoint' uses final values, 'full' uses full path clustering

    Returns:
        Array of density scores for each path (0-1 range)
    """
    n_paths = paths.shape[0]

    if probabilities is not None:
        # Normalize probabilities to 0-1
        prob_min = probabilities.min()
        prob_max = probabilities.max()
        if prob_max - prob_min > 1e-10:
            scores = (probabilities - prob_min) / (prob_max - prob_min)
        else:
            scores = np.ones(n_paths) * 0.5
        return scores

    if method == "endpoint":
        # Use kernel density estimation on endpoint values
        endpoints = paths[:, -1]
        try:
            from scipy import stats

            kde = stats.gaussian_kde(endpoints)
            density_scores = kde(endpoints)
        except ImportError:
            # Fallback: use histogram-based density
            hist, bins = np.histogram(endpoints, bins=50)
            bin_indices = np.digitize(endpoints, bins[:-1]) - 1
            bin_indices = np.clip(bin_indices, 0, len(hist) - 1)
            density_scores = hist[bin_indices].astype(float)

        # Normalize to 0-1
        score_min = density_scores.min()
        score_max = density_scores.max()
        if score_max - score_min > 1e-10:
            scores = (density_scores - score_min) / (score_max - score_min)
        else:
            scores = np.ones(n_paths) * 0.5
    else:
        # Full path similarity - compute pairwise distances
        try:
            from sklearn.neighbors import NearestNeighbors

            nn = NearestNeighbors(n_neighbors=min(10, n_paths))
            nn.fit(paths)
            distances, _ = nn.kneighbors(paths)
            # Average distance to neighbors - lower = denser region
            avg_dist = distances.mean(axis=1)
            # Convert to density score (inverse distance)
            scores = 1 / (1 + avg_dist)
            score_min = scores.min()
            score_max = scores.max()
            if score_max - score_min > 1e-10:
                scores = (scores - score_min) / (score_max - score_min)
            else:
                scores = np.ones(n_paths) * 0.5
        except ImportError:
            # Fallback to endpoint method
            return compute_path_colors_by_density(paths, method="endpoint")

    return scores


def compute_percentiles(
    paths: np.ndarray, percentiles: list = [5, 25, 50, 75, 95]
) -> dict:
    """
    Compute percentile values across paths.

    Args:
        paths: Array of shape (n_paths, n_steps)
        percentiles: List of percentiles to compute

    Returns:
        Dict mapping percentile to array of values
    """
    result = {}
    for p in percentiles:
        result[p] = np.percentile(paths, p, axis=0)
    return result


def compute_weighted_forecast(
    paths: np.ndarray, probabilities: np.ndarray
) -> np.ndarray:
    """
    Compute probability-weighted forecast.

    Args:
        paths: Array of shape (n_paths, n_steps)
        probabilities: Path probabilities

    Returns:
        Weighted forecast array of shape (n_steps,)
    """
    # Normalize probabilities
    probs = probabilities / probabilities.sum()
    return np.average(paths, axis=0, weights=probs)


def compute_weighted_ci(
    paths: np.ndarray,
    probabilities: np.ndarray,
    lower_pct: float = 0.025,
    upper_pct: float = 0.975,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute probability-weighted confidence intervals.

    Args:
        paths: Array of shape (n_paths, n_steps)
        probabilities: Path probabilities
        lower_pct: Lower percentile (default 2.5% for 95% CI)
        upper_pct: Upper percentile (default 97.5% for 95% CI)

    Returns:
        Tuple of (lower_ci, upper_ci) arrays
    """
    n_steps = paths.shape[1]
    lower_ci = np.zeros(n_steps)
    upper_ci = np.zeros(n_steps)

    # Normalize probabilities
    probs = probabilities / probabilities.sum()

    for t in range(n_steps):
        values = paths[:, t]
        # Sort values and get cumulative probabilities
        sorted_idx = np.argsort(values)
        sorted_values = values[sorted_idx]
        sorted_probs = probs[sorted_idx]
        cumsum_probs = np.cumsum(sorted_probs)

        # Find percentile values
        lower_idx = np.searchsorted(cumsum_probs, lower_pct)
        upper_idx = np.searchsorted(cumsum_probs, upper_pct)

        lower_ci[t] = sorted_values[min(lower_idx, len(sorted_values) - 1)]
        upper_ci[t] = sorted_values[min(upper_idx, len(sorted_values) - 1)]

    return lower_ci, upper_ci
