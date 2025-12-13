"""
Kagi chart transformation.

Kagi charts focus on significant price movements, changing direction
only when price reverses by a specified amount.
"""

import polars as pl
from typing import Optional, List, Dict, Any


def to_kagi(
    df: pl.DataFrame,
    reversal_amount: float,
    time_col: str = "time",
    close_col: str = "close",
    use_percentage: bool = False,
) -> pl.DataFrame:
    """
    Convert price data to Kagi chart lines.

    Kagi charts consist of vertical lines that change direction when
    price reverses by a specified amount. Line thickness changes when
    price breaks previous highs (yang/thick) or lows (yin/thin).

    Benefits:
    - Filters minor price movements
    - Clear trend visualization
    - Built-in support/resistance levels

    Args:
        df: Polars DataFrame with price data
        reversal_amount: Minimum price change to reverse direction
        time_col: Name of time column
        close_col: Name of close price column
        use_percentage: If True, reversal_amount is a percentage (e.g., 0.04 = 4%)

    Returns:
        DataFrame with Kagi lines (time, open, high, low, close, line_type)
        line_type: 'yang' (thick, bullish) or 'yin' (thin, bearish)

    Example:
        >>> import wrchart as wrc
        >>> # Reverse on $2 movement
        >>> kagi = wrc.to_kagi(price_data, reversal_amount=2.0)
        >>>
        >>> # Reverse on 4% movement
        >>> kagi = wrc.to_kagi(price_data, reversal_amount=0.04, use_percentage=True)
    """
    closes = df[close_col].to_list()
    times = df[time_col].to_list()

    if len(closes) < 2:
        return pl.DataFrame(
            {
                "time": times,
                "open": closes,
                "high": closes,
                "low": closes,
                "close": closes,
                "line_type": ["yang"] * len(closes),
            }
        )

    lines: List[Dict[str, Any]] = []

    # Initialize
    current_price = closes[0]
    trend = 0  # 1 = up, -1 = down
    line_start = current_price
    prev_high = current_price
    prev_low = current_price
    line_type = "yang"  # Start bullish

    for i in range(1, len(closes)):
        price = closes[i]

        # Calculate reversal threshold
        if use_percentage:
            threshold = current_price * reversal_amount
        else:
            threshold = reversal_amount

        if trend == 0:
            # Determine initial trend
            if price - current_price >= threshold:
                trend = 1
                line_start = current_price
                current_price = price
            elif current_price - price >= threshold:
                trend = -1
                line_start = current_price
                current_price = price
        elif trend == 1:  # Uptrend
            if price > current_price:
                # Continue up
                current_price = price
                if price > prev_high:
                    line_type = "yang"  # Break above previous high
            elif current_price - price >= threshold:
                # Reversal down
                lines.append(
                    {
                        "time": times[i - 1],
                        "open": line_start,
                        "high": current_price,
                        "low": line_start,
                        "close": current_price,
                        "line_type": line_type,
                    }
                )
                prev_high = max(prev_high, current_price)
                line_start = current_price
                current_price = price
                trend = -1
                if price < prev_low:
                    line_type = "yin"  # Break below previous low
        else:  # Downtrend
            if price < current_price:
                # Continue down
                current_price = price
                if price < prev_low:
                    line_type = "yin"  # Break below previous low
            elif price - current_price >= threshold:
                # Reversal up
                lines.append(
                    {
                        "time": times[i - 1],
                        "open": line_start,
                        "high": line_start,
                        "low": current_price,
                        "close": current_price,
                        "line_type": line_type,
                    }
                )
                prev_low = min(prev_low, current_price)
                line_start = current_price
                current_price = price
                trend = 1
                if price > prev_high:
                    line_type = "yang"  # Break above previous high

    # Add final line
    if trend == 1:
        lines.append(
            {
                "time": times[-1],
                "open": line_start,
                "high": current_price,
                "low": line_start,
                "close": current_price,
                "line_type": line_type,
            }
        )
    elif trend == -1:
        lines.append(
            {
                "time": times[-1],
                "open": line_start,
                "high": line_start,
                "low": current_price,
                "close": current_price,
                "line_type": line_type,
            }
        )

    if not lines:
        # No significant movement
        return pl.DataFrame(
            {
                "time": [times[-1]],
                "open": [closes[0]],
                "high": [max(closes)],
                "low": [min(closes)],
                "close": [closes[-1]],
                "line_type": ["yang"],
            }
        )

    return pl.DataFrame(lines)
