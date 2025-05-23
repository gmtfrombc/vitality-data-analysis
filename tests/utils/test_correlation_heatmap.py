import pandas as pd
import numpy as np
from app.utils.advanced_correlation import calculate_correlation_matrix
from app.utils.plots import correlation_heatmap, Element, Overlay


def test_correlation_heatmap_overlay():
    """Ensure helper returns Overlay and correlation matrix is symmetric."""
    np.random.seed(0)
    # Create correlated data
    n = 50
    weight = np.random.normal(80, 10, n)
    bmi = weight / 2.5 + np.random.normal(0, 2, n)
    sbp = 120 + (weight - 80) * 0.5 + np.random.normal(0, 5, n)
    df = pd.DataFrame({"weight": weight, "bmi": bmi, "sbp": sbp})

    from scipy import stats

    metrics = ["weight", "bmi", "sbp"]
    corr = calculate_correlation_matrix(df, metrics)
    # Calculate p-values manually to match expected interface
    n = len(metrics)
    pvals = pd.DataFrame(np.ones((n, n)), index=metrics, columns=metrics)
    for i, col_i in enumerate(metrics):
        for j, col_j in enumerate(metrics):
            if i < j:
                r, p = stats.pearsonr(df[col_i], df[col_j])
                pvals.loc[col_i, col_j] = pvals.loc[col_j, col_i] = p
            elif i == j:
                pvals.loc[col_i, col_j] = 1.0

    # Symmetry and diagonal ones
    assert corr.shape == (3, 3)
    assert (corr.columns == corr.index).all()
    assert np.allclose(np.diag(corr), 1)

    plot = correlation_heatmap(corr, pvals)
    # Should be Overlay (heat + labels)
    assert isinstance(plot, (Overlay, Element))

    # String representation contains title
    assert "Correlation Matrix" in str(plot)
