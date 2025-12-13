"""
Point and Figure (P&F) chart transformation.

P&F charts use X's and O's to show price movements,
ignoring time completely.
"""

import polars as pl
from typing import List, Dict, Any


def to_point_and_figure(
    df: pl.DataFrame,
    box_size: float,
    reversal_boxes: int = 3,
    time_col: str = "time",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pl.DataFrame:
    """
    Convert price data to Point and Figure chart data.

    Point and Figure charts plot price movements using:
    - X columns for rising prices
    - O columns for falling prices

    Each X or O represents a fixed price movement (box_size).
    Direction only changes after a reversal of reversal_boxes * box_size.

    Benefits:
    - Pure price action analysis
    - Clear support/resistance levels
    - Eliminates time-based noise

    Args:
        df: Polars DataFrame with price data
        box_size: Size of each box in price units
        reversal_boxes: Number of boxes required for reversal (typically 3)
        time_col: Name of time column
        high_col: Name of high price column
        low_col: Name of low price column
        close_col: Name of close price column

    Returns:
        DataFrame with P&F data:
        - time: Time of the column
        - column_index: Index of the column (for x-axis positioning)
        - column_type: 'X' or 'O'
        - low: Bottom of the column (lowest box)
        - high: Top of the column (highest box)
        - boxes: Number of boxes in the column

    Example:
        >>> import wrchart as wrc
        >>> # $1 box size, 3-box reversal
        >>> pnf = wrc.to_point_and_figure(ohlc_data, box_size=1.0, reversal_boxes=3)
    """
    highs = df[high_col].to_list()
    lows = df[low_col].to_list()
    times = df[time_col].to_list()

    if len(highs) == 0:
        return pl.DataFrame(
            {
                "time": [],
                "column_index": [],
                "column_type": [],
                "low": [],
                "high": [],
                "boxes": [],
            }
        )

    reversal_amount = box_size * reversal_boxes

    columns: List[Dict[str, Any]] = []
    column_index = 0

    # Initialize with first data point
    current_high = _round_to_box(highs[0], box_size)
    current_low = _round_to_box(lows[0], box_size)
    column_type = None  # Will be determined by first movement
    column_start_time = times[0]

    for i in range(1, len(highs)):
        high = highs[i]
        low = lows[i]
        time = times[i]

        if column_type is None:
            # Determine initial direction
            if high - current_low >= box_size:
                column_type = "X"
                current_high = _round_to_box(high, box_size)
            elif current_high - low >= box_size:
                column_type = "O"
                current_low = _round_to_box(low, box_size, round_down=True)
            continue

        if column_type == "X":
            # In an X column (rising)
            if high > current_high:
                # Continue rising
                current_high = _round_to_box(high, box_size)
            elif current_high - low >= reversal_amount:
                # Reversal to O column
                columns.append(
                    {
                        "time": column_start_time,
                        "column_index": column_index,
                        "column_type": "X",
                        "low": current_low,
                        "high": current_high,
                        "boxes": int((current_high - current_low) / box_size),
                    }
                )
                column_index += 1
                column_start_time = time
                current_low = _round_to_box(low, box_size, round_down=True)
                # New column starts one box below the previous high
                current_high = current_high - box_size
                column_type = "O"

        else:  # column_type == 'O'
            # In an O column (falling)
            if low < current_low:
                # Continue falling
                current_low = _round_to_box(low, box_size, round_down=True)
            elif high - current_low >= reversal_amount:
                # Reversal to X column
                columns.append(
                    {
                        "time": column_start_time,
                        "column_index": column_index,
                        "column_type": "O",
                        "low": current_low,
                        "high": current_high,
                        "boxes": int((current_high - current_low) / box_size),
                    }
                )
                column_index += 1
                column_start_time = time
                current_high = _round_to_box(high, box_size)
                # New column starts one box above the previous low
                current_low = current_low + box_size
                column_type = "X"

    # Add final column
    if column_type is not None:
        columns.append(
            {
                "time": column_start_time,
                "column_index": column_index,
                "column_type": column_type,
                "low": current_low,
                "high": current_high,
                "boxes": max(1, int((current_high - current_low) / box_size)),
            }
        )

    if not columns:
        # Not enough movement for any columns
        return pl.DataFrame(
            {
                "time": [times[0]],
                "column_index": [0],
                "column_type": ["X"],
                "low": [_round_to_box(min(lows), box_size, round_down=True)],
                "high": [_round_to_box(max(highs), box_size)],
                "boxes": [1],
            }
        )

    return pl.DataFrame(columns)


def _round_to_box(price: float, box_size: float, round_down: bool = False) -> float:
    """Round price to nearest box boundary."""
    if round_down:
        return (price // box_size) * box_size
    else:
        return ((price + box_size - 0.0001) // box_size) * box_size
