import pandas as pd
import numpy as np
from app.utils.analysis_helpers import compute_correlation
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

    corr, pvals = compute_correlation(df, ["weight", "bmi", "sbp"])

    # Symmetry and diagonal ones
    assert corr.shape == (3, 3)
    assert (corr.columns == corr.index).all()
    assert np.allclose(np.diag(corr), 1)

    plot = correlation_heatmap(corr, pvals)
    # Should be Overlay (heat + labels)
    assert isinstance(plot, (Overlay, Element))

    # String representation contains title
    assert "Correlation Matrix" in str(plot)
