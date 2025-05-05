"""Analysis utilities (pure functions).

Currently contains:
• compute_correlation – returns correlation & p-value matrices for a DataFrame slice.
"""

from __future__ import annotations

from typing import Sequence, Tuple

import pandas as pd
import numpy as np
from scipy import stats

__all__ = ["compute_correlation"]


def compute_correlation(
    df: pd.DataFrame,
    columns: Sequence[str],
    method: str = "pearson",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return correlation and p-value matrices for *columns* of *df*.

    Parameters
    ----------
    df : pandas.DataFrame
        Source data.
    columns : Sequence[str]
        Numeric columns to include in the correlation analysis.
    method : str, default "pearson"
        Correlation method – one of *pearson*, *spearman*, *kendall*.

    Returns
    -------
    (corr, pvals) : tuple[pd.DataFrame, pd.DataFrame]
        Square matrices indexed/columned by *columns* order.
    """
    cols = list(columns)
    sub = df[cols].dropna()

    if sub.empty:
        raise ValueError("No valid rows after dropping NaNs for correlation.")

    n = len(cols)
    corr = pd.DataFrame(np.eye(n), index=cols, columns=cols, dtype=float)
    pvals = pd.DataFrame(np.zeros((n, n)), index=cols, columns=cols, dtype=float)

    for i, col_i in enumerate(cols):
        for j in range(i + 1, n):
            col_j = cols[j]
            if method == "pearson":
                r, p = stats.pearsonr(sub[col_i], sub[col_j])
            elif method == "spearman":
                r, p = stats.spearmanr(sub[col_i], sub[col_j])
            elif method == "kendall":
                r, p = stats.kendalltau(sub[col_i], sub[col_j])
            else:
                raise ValueError(f"Unknown correlation method '{method}'.")

            corr.loc[col_i, col_j] = corr.loc[col_j, col_i] = r
            pvals.loc[col_i, col_j] = pvals.loc[col_j, col_i] = p

    return corr, pvals
